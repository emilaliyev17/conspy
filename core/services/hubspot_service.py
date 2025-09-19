"""HubSpot integration service for synchronizing CRM data into Django."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Callable, Dict, Optional

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from hubspot import HubSpot

from core.models import HubSpotData, HubSpotSyncLog

logger = logging.getLogger(__name__)


def convert_datetime_to_str(obj):
    """Recursively convert datetime objects to ISO format strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {key: convert_datetime_to_str(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [convert_datetime_to_str(item) for item in obj]
    return obj


class HubSpotService:
    """Wrapper around the HubSpot API client implementing read-only sync flows."""

    PAGE_SIZE = 100

    def __init__(self, access_token: Optional[str] = None) -> None:
        self.access_token = access_token or settings.HUBSPOT_ACCESS_TOKEN
        self._client: Optional[HubSpot] = None

    @property
    def client(self) -> HubSpot:
        if self._client is None:
            if not self.access_token:
                raise ImproperlyConfigured("HUBSPOT_ACCESS_TOKEN is not configured.")
            self._client = HubSpot(access_token=self.access_token)
        return self._client

    # Public API -----------------------------------------------------------------

    def sync_deals(self) -> Dict[str, object]:
        return self._sync_objects(
            record_type=HubSpotData.RecordType.DEAL,
            fetch_page=lambda after=None, limit=None: self.client.crm.deals.basic_api.get_page(
                limit=limit or self.PAGE_SIZE,
                after=after,
                archived=False,
            ),
        )

    def sync_companies(self) -> Dict[str, object]:
        return self._sync_objects(
            record_type=HubSpotData.RecordType.COMPANY,
            fetch_page=lambda after=None, limit=None: self.client.crm.companies.basic_api.get_page(
                limit=limit or self.PAGE_SIZE,
                after=after,
                archived=False,
            ),
        )

    def sync_contacts(self) -> Dict[str, object]:
        return self._sync_objects(
            record_type=HubSpotData.RecordType.CONTACT,
            fetch_page=lambda after=None, limit=None: self.client.crm.contacts.basic_api.get_page(
                limit=limit or self.PAGE_SIZE,
                after=after,
                archived=False,
            ),
        )

    def get_financial_metrics(self) -> Dict[str, object]:
        """Return high-level FP&A metrics derived from synced HubSpot data."""

        deals_qs = HubSpotData.objects.filter(record_type=HubSpotData.RecordType.DEAL)
        companies_qs = HubSpotData.objects.filter(record_type=HubSpotData.RecordType.COMPANY)
        contacts_qs = HubSpotData.objects.filter(record_type=HubSpotData.RecordType.CONTACT)

        total_deal_amount = Decimal("0")
        deals_with_amount = 0
        for deal_payload in deals_qs.values_list("data", flat=True):
            properties = (deal_payload or {}).get("properties", {})
            raw_amount = properties.get("amount") or properties.get("dealamount")
            if raw_amount in (None, ""):
                continue
            try:
                total_deal_amount += Decimal(str(raw_amount))
                deals_with_amount += 1
            except (InvalidOperation, TypeError):
                logger.debug("Skipping deal amount that could not be parsed: %s", raw_amount)

        average_deal_amount = (
            (total_deal_amount / deals_with_amount).quantize(Decimal("0.01"))
            if deals_with_amount
            else Decimal("0")
        )

        last_logs = (
            HubSpotSyncLog.objects.filter(status=HubSpotSyncLog.Status.SUCCESS)
            .order_by("-finished_at")
            .values("sync_type", "finished_at")
        )

        last_successful_sync = None
        last_success_per_type: Dict[str, Optional[str]] = {
            HubSpotData.RecordType.DEAL: None,
            HubSpotData.RecordType.COMPANY: None,
            HubSpotData.RecordType.CONTACT: None,
        }

        for log in last_logs:
            finished_at = log.get("finished_at")
            if finished_at and last_successful_sync is None:
                last_successful_sync = finished_at.isoformat()
            sync_type = log.get("sync_type")
            if sync_type in last_success_per_type and not last_success_per_type[sync_type]:
                last_success_per_type[sync_type] = finished_at.isoformat() if finished_at else None

            if all(last_success_per_type.values()):
                break

        return {
            "totals": {
                "deals": deals_qs.count(),
                "companies": companies_qs.count(),
                "contacts": contacts_qs.count(),
                "deal_amount_total": str(total_deal_amount.quantize(Decimal("0.01")) if deals_with_amount else Decimal("0")),
                "deal_amount_avg": str(average_deal_amount),
            },
            "last_successful_sync": last_successful_sync,
            "last_success_per_type": last_success_per_type,
        }

    # Internal helpers -----------------------------------------------------------

    def _sync_objects(
        self,
        *,
        record_type: HubSpotData.RecordType,
        fetch_page: Callable[[Optional[str], Optional[int]], object],
    ) -> Dict[str, object]:
        created_count = 0
        updated_count = 0
        total_processed = 0
        after: Optional[str] = None
        more = True

        log_entry = HubSpotSyncLog.objects.create(
            sync_type=record_type,
            status=HubSpotSyncLog.Status.SUCCESS,
            details={},
        )

        try:
            while more:
                response = fetch_page(after=after, limit=self.PAGE_SIZE)
                results = getattr(response, "results", [])

                for item in results:
                    hubspot_id = getattr(item, "id", None)
                    if not hubspot_id:
                        continue

                    properties = getattr(item, "properties", None)
                    source = properties if properties is not None else item.to_dict()
                    payload = convert_datetime_to_str(source)
                    _, created = HubSpotData.objects.update_or_create(
                        record_type=record_type,
                        hubspot_id=hubspot_id,
                        defaults={"data": payload},
                    )
                    total_processed += 1
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                paging = getattr(response, "paging", None)
                next_link = getattr(paging, "next", None) if paging else None
                after = getattr(next_link, "after", None) if next_link else None
                more = bool(after)

            details = {
                "status": HubSpotSyncLog.Status.SUCCESS.value,
                "synced": total_processed,
                "created": created_count,
                "updated": updated_count,
            }
            log_entry.details = details
            log_entry.finished_at = timezone.now()
            log_entry.save(update_fields=["details", "finished_at"])
            logger.info(
                "HubSpot %s sync completed", record_type
            )
            return {**details, "log_id": log_entry.id}

        except Exception as exc:  # noqa: BLE001 - allow richer context in log
            status = (
                HubSpotSyncLog.Status.PARTIAL
                if (created_count or updated_count)
                else HubSpotSyncLog.Status.FAILURE
            )
            log_entry.status = status
            log_entry.error_message = str(exc)
            log_entry.details = {
                "status": status.value,
                "synced": total_processed,
                "created": created_count,
                "updated": updated_count,
            }
            log_entry.finished_at = timezone.now()
            log_entry.save(update_fields=["status", "error_message", "details", "finished_at"])

            logger.exception("HubSpot %s sync failed", record_type)
            return {
                "status": status.value,
                "synced": total_processed,
                "created": created_count,
                "updated": updated_count,
                "error": str(exc),
                "log_id": log_entry.id,
            }
