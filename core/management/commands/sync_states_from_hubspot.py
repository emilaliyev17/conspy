from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import ActiveState, HubSpotData

DEFAULT_STATE_FIELD = 'state_placeholder'


class Command(BaseCommand):
    help = "Aggregate HubSpot deal data into ActiveState counters."

    def add_arguments(self, parser):
        parser.add_argument(
            '--state-field',
            default=DEFAULT_STATE_FIELD,
            help=(
                "HubSpot deal property that contains the state identifier. "
                "Placeholder defaults to 'state_placeholder' until confirmed."
            ),
        )
        parser.add_argument(
            '--amount-field',
            default='amount',
            help="HubSpot deal property used for monetary amount (fallbacks are applied automatically).",
        )

    def handle(self, *args, **options):
        state_field = options['state_field']
        primary_amount_field = options['amount_field']

        deals_qs = HubSpotData.objects.filter(record_type=HubSpotData.RecordType.DEAL)
        total_deals = deals_qs.count()

        if total_deals == 0:
            self.stdout.write(self.style.WARNING('No HubSpot deals found to process.'))
            return

        aggregates: dict[str, dict[str, Decimal | int]] = defaultdict(lambda: {'count': 0, 'amount': Decimal('0')})
        skipped_state = 0
        skipped_amount = 0

        for deal in deals_qs.iterator():
            payload = deal.data or {}
            state_raw = payload.get(state_field)
            if not state_raw:
                skipped_state += 1
                continue

            state_code = str(state_raw).strip().upper()
            if len(state_code) != 2:
                skipped_state += 1
                continue

            raw_amount = payload.get(primary_amount_field) or payload.get('dealamount')
            amount = Decimal('0')
            if raw_amount not in (None, ''):
                try:
                    amount = Decimal(str(raw_amount))
                except (InvalidOperation, ValueError, TypeError):
                    skipped_amount += 1
                    amount = Decimal('0')

            aggregates[state_code]['count'] += 1
            aggregates[state_code]['amount'] += amount

        if not aggregates:
            self.stdout.write(self.style.WARNING('No deals contained a usable state code; nothing to update.'))
            return

        with transaction.atomic():
            ActiveState.objects.update(deal_count=0, deal_volume=Decimal('0'), is_active=False)

            for state_code, data in sorted(aggregates.items()):
                state_obj, _ = ActiveState.objects.get_or_create(
                    state_code=state_code,
                    defaults={
                        'state_name': state_code,
                        'deal_count': 0,
                        'deal_volume': Decimal('0'),
                        'is_active': False,
                    },
                )
                state_obj.deal_count = data['count']
                state_obj.deal_volume = data['amount'].quantize(Decimal('0.01'))
                state_obj.is_active = data['count'] > 0
                state_obj.save(update_fields=['deal_count', 'deal_volume', 'is_active'])

        processed_states = len(aggregates)
        self.stdout.write(self.style.SUCCESS(
            f'State aggregates updated for {processed_states} state(s) from {total_deals} deal(s).'
        ))

        if skipped_state:
            self.stdout.write(self.style.WARNING(f'Skipped {skipped_state} deal(s) due to missing/invalid state values.'))
        if skipped_amount:
            self.stdout.write(self.style.WARNING(f'Skipped amount parsing for {skipped_amount} deal(s).'))

        self.stdout.write('Per-state summary:')
        for state_code, data in sorted(aggregates.items(), key=lambda item: item[0]):
            amount = data['amount'].quantize(Decimal('0.01'))
            self.stdout.write(f"  {state_code}: count={data['count']} amount={amount}")
