from itertools import groupby

from src.bunq import BunqLib
from src.strategies import all_strategies
from src.allocation import FireStore


class AutomateAllocations:
    def __init__(self, bunq: BunqLib, store: FireStore, simulate: bool = True):
        self.bunq = bunq
        self.store = store
        self.main_account_balance = None
        self.simulate = simulate

    def run(self):
        allocations = self.store.get_allocations(self.bunq.accounts)
        sorted_allocations = sorted(allocations, key=lambda x: x.priority)
        grouped_allocations = groupby(sorted_allocations, key=lambda x: x.priority)
        main_account_settings = self.store.get_main_account_settings()
        self.main_account_balance = self.bunq.get_balance_by_id(id_=main_account_settings.id)
        remainder = self.main_account_balance
        print(f"{remainder} EUR to sort...")

        for _, group in grouped_allocations:
            allocations = list(group)
            for allocation in filter(lambda a: a.strategy != "percentage", allocations):
                remainder = self._process_allocation(
                    allocation, main_account_settings, remainder
                )

            original_remainder = remainder
            for allocation in filter(lambda a: a.strategy == "percentage", allocations):
                remainder = self._process_allocation(
                    allocation,
                    main_account_settings,
                    remainder,
                    original_remainder=original_remainder,
                )
        return "Success"

    def _process_allocation(
        self, allocation, main_account_settings, remainder, *, original_remainder=None
    ):
        strategy = all_strategies.get(allocation.strategy)
        amount = strategy(
            allocation,
            original_remainder if original_remainder else remainder,
            bunq=self.bunq,
        )
        if amount > 0:
            self.bunq.make_payment(
                from_account_id=main_account_settings.id,
                to_account_alias=allocation.description,
                to_account_type=allocation.account_type,
                amount=amount,
                description=f"Deel salaris voor {allocation.description}",
                to_iban=allocation.iban,
                simulate=self.simulate,
                original_amount_to_sort=self.main_account_balance
            )
            remainder -= amount
        return remainder
