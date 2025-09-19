from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ImproperlyConfigured

from core.models import HubSpotSyncLog
from core.services.hubspot_service import HubSpotService


class Command(BaseCommand):
    help = "Synchronize HubSpot CRM data into the local store (read-only)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--objects',
            nargs='+',
            choices=['deals', 'companies', 'contacts', 'all'],
            default=['all'],
            help='Object types to sync. Default: all.',
        )

    def handle(self, *args, **options):
        requested = options['objects'] or ['all']
        if 'all' in requested:
            targets = ['deals', 'companies', 'contacts']
        else:
            targets = []
            for item in requested:
                if item not in targets:
                    targets.append(item)

        try:
            service = HubSpotService()
        except ImproperlyConfigured as exc:
            raise CommandError(str(exc)) from exc

        action_map = {
            'deals': service.sync_deals,
            'companies': service.sync_companies,
            'contacts': service.sync_contacts,
        }

        failure_detected = False
        partial_detected = False

        for target in targets:
            self.stdout.write(self.style.MIGRATE_HEADING(f"Syncing {target} from HubSpot"))
            result = action_map[target]()

            status = result.get('status')
            message = (
                f"{target.capitalize()} sync status: {status}. "
                f"created={result.get('created', 0)}, updated={result.get('updated', 0)}, "
                f"synced={result.get('synced', 0)}, log_id={result.get('log_id')}"
            )

            if status == HubSpotSyncLog.Status.FAILURE.value:
                failure_detected = True
                self.stderr.write(self.style.ERROR(message))
                if result.get('error'):
                    self.stderr.write(self.style.ERROR(f"Error: {result['error']}"))
            elif status == HubSpotSyncLog.Status.PARTIAL.value:
                partial_detected = True
                self.stdout.write(self.style.WARNING(message))
                if result.get('error'):
                    self.stdout.write(self.style.WARNING(f"Warning: {result['error']}"))
            else:
                self.stdout.write(self.style.SUCCESS(message))

        metrics = service.get_financial_metrics()
        totals = metrics.get('totals', {})
        self.stdout.write(
            f"Current HubSpot metrics: deals={totals.get('deals')}, "
            f"companies={totals.get('companies')}, contacts={totals.get('contacts')}, "
            f"total_deal_amount={totals.get('deal_amount_total')}"
        )

        if failure_detected:
            raise CommandError('One or more sync operations failed. See logs for details.')

        if partial_detected:
            self.stdout.write(self.style.WARNING('One or more sync operations completed partially. Review sync logs.'))
