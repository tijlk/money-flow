from decimal import Decimal

from src.allocation import Allocation
from src.bunq import BunqLib


def _check_minimum_amount(amount: Decimal, *, minimum_amount: Decimal) -> Decimal:
    if amount > (minimum_amount if minimum_amount else 0):
        return amount
    else:
        return Decimal(0)


def _check_remainder(amount: Decimal, *, remainder: Decimal) -> Decimal:
    return min(amount, remainder)


def top_up_strategy(
    allocation: Allocation, remainder: Decimal, *, bunq: BunqLib
) -> Decimal:
    balance = bunq.get_balance_by_iban(iban=allocation.iban)
    amount = allocation.target_balance - balance
    amount = _check_remainder(amount, remainder=remainder)
    if allocation.max_amount:
        amount = min(amount, allocation.max_amount)

    return _check_minimum_amount(amount, minimum_amount=allocation.min_amount)


def fixed_strategy(allocation: Allocation, remainder: Decimal, *_, **__) -> Decimal:
    amount = allocation.fixed_amount
    amount = _check_remainder(amount, remainder=remainder)
    return _check_minimum_amount(amount, minimum_amount=allocation.min_amount)


def percentage_strategy(
    allocation: Allocation, remainder: Decimal, *_, **__
) -> Decimal:
    amount = Decimal(round(float(remainder) * (allocation.percentage / 100.), 2))
    return _check_minimum_amount(amount, minimum_amount=allocation.min_amount)


all_strategies = dict(
    top_up=top_up_strategy,
    fixed=fixed_strategy,
    percentage=percentage_strategy,
)
