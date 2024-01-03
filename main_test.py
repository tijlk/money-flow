from decimal import Decimal
from unittest.mock import Mock, MagicMock, call

from main import AutomateAllocations
from src.allocation import Settings, Allocation

default_payment_kwargs = {
    "description": "test description",
    "iban": "NL76BUNQ2063655073",
    "iban_name": "Folkert Plank",
}


class TestMinimumAllocation:
    def setup_method(self):
        self.bunq_ = MagicMock()
        self.store_ = MagicMock()
        self.store_.get_main_account_settings = Mock(
            return_value=Settings(minimum=Decimal("500.00"), id=0)
        )
        self.bunq_.get_balance_by_id = Mock(return_value=Decimal("1000.00"))
        self.automate_allocations = AutomateAllocations(
            bunq=self.bunq_, store=self.store_
        )

    def test_when_minimum_is_greater_than_remainder_expect_payment_with_remainder_as_amount(
        self,
    ):
        self.bunq_.make_payment = Mock()
        self.store_.get_allocations = Mock(
            return_value=[
                Allocation(
                    value=Decimal("99999999.00"),
                    type="top_up",
                    **default_payment_kwargs,
                )
            ]
        )
        self.bunq_.get_balance_by_iban = Mock(return_value=Decimal("0.00"))

        self.automate_allocations.run()

        self.bunq_.make_payment.assert_called_once_with(
            amount=Decimal("500.00"), account_id=0, **default_payment_kwargs
        )

    def test_when_minimum_is_smaller_than_remainder_expect_payment_with_difference(
        self,
    ):
        self.bunq_.make_payment = Mock()
        self.store_.get_allocations = Mock(
            return_value=[
                Allocation(
                    value=Decimal("2000.00"),
                    type="top_up",
                    **default_payment_kwargs,
                )
            ]
        )
        self.bunq_.get_balance_by_iban = Mock(return_value=Decimal("1970.00"))

        self.automate_allocations.run()

        self.bunq_.make_payment.assert_any_call(
            amount=Decimal("30.00"),
            **default_payment_kwargs,
            account_id=0,
        )

    def test_when_minimum_amount_is_higher_than_amount_expect_no_payment(
        self,
    ):
        self.bunq_.make_payment = Mock()
        self.store_.get_allocations = Mock(
            return_value=[
                Allocation(
                    value=Decimal("2000.00"),
                    type="top_up",
                    minimum_amount=Decimal("200.00"),
                    **default_payment_kwargs,
                )
            ]
        )
        self.bunq_.get_balance_by_iban = Mock(return_value=Decimal("1900.00"))

        self.automate_allocations.run()

        self.bunq_.make_payment.assert_not_called()


class TestPercentageAllocation:
    def setup_method(self):
        self.bunq_ = MagicMock()
        self.store_ = MagicMock()
        self.store_.get_main_account_settings = Mock(
            return_value=Settings(minimum=Decimal("500.00"), id=0)
        )
        self.bunq_.get_balance_by_id = Mock(return_value=Decimal("1000.00"))
        self.automate_allocations = AutomateAllocations(
            bunq=self.bunq_, store=self.store_
        )

    def test_when_percentage_is_100_expect_total_remainder_in_payment(
        self,
    ):
        self.bunq_.make_payment = Mock()
        self.store_.get_allocations = Mock(
            return_value=[
                Allocation(
                    value=Decimal("100.00"),
                    type="percentage",
                    **default_payment_kwargs,
                )
            ]
        )

        self.automate_allocations.run()

        self.bunq_.make_payment.assert_called_once_with(
            amount=Decimal("500.00"), account_id=0, **default_payment_kwargs
        )

    def test_when_two_percentage_allocations_expect_correct_amounts(
        self,
    ):
        self.bunq_.make_payment = Mock()
        self.store_.get_allocations = Mock(
            return_value=[
                Allocation(
                    value=Decimal("10.00"),
                    type="percentage",
                    **default_payment_kwargs,
                ),
                Allocation(
                    value=Decimal("50.00"),
                    type="percentage",
                    **default_payment_kwargs,
                ),
            ]
        )

        self.automate_allocations.run()

        self.bunq_.make_payment.assert_any_call(
            amount=Decimal("50.00"), account_id=0, **default_payment_kwargs
        )

        self.bunq_.make_payment.assert_any_call(
            amount=Decimal("250.00"), account_id=0, **default_payment_kwargs
        )

    def test_when_percentage_is_zero_expect_no_payment(
        self,
    ):
        self.bunq_.make_payment = Mock()
        self.store_.get_allocations = Mock(
            return_value=[
                Allocation(
                    value=Decimal("00.00"),
                    type="percentage",
                    **default_payment_kwargs,
                )
            ]
        )
        self.bunq_.get_balance_by_iban = Mock(return_value=Decimal("2500.00"))

        self.automate_allocations.run()

        self.bunq_.make_payment.assert_not_called()

    def test_when_minimum_amount_is_higher_than_amount_expect_no_payment(
        self,
    ):
        self.bunq_.make_payment = Mock()
        self.store_.get_allocations = Mock(
            return_value=[
                Allocation(
                    value=Decimal("100.00"),
                    type="percentage",
                    minimum_amount=Decimal("500.01"),
                    **default_payment_kwargs,
                )
            ]
        )
        self.bunq_.get_balance_by_iban = Mock(return_value=Decimal("2500.00"))

        self.automate_allocations.run()

        self.bunq_.make_payment.assert_not_called()


class TestFixedAllocation:
    def setup_method(self):
        self.bunq_ = MagicMock()
        self.bunq_.get_balance_by_id = Mock(return_value=Decimal("1000.00"))
        self.bunq_.make_payment = Mock()

        self.store_ = MagicMock()
        self.store_.get_main_account_settings = Mock(
            return_value=Settings(minimum=Decimal("500.00"), id=0)
        )
        self.automate_allocations = AutomateAllocations(
            bunq=self.bunq_, store=self.store_
        )

    def test_when_amount_available_expect_amount_in_payment(
        self,
    ):
        self.store_.get_allocations = Mock(
            return_value=[
                Allocation(
                    value=Decimal("200.00"),
                    type="fixed",
                    **default_payment_kwargs,
                )
            ]
        )

        self.automate_allocations.run()

        self.bunq_.make_payment.assert_called_once_with(
            amount=Decimal("200.00"), account_id=0, **default_payment_kwargs
        )

    def test_when_amount_unavailable_expect_available_amount_in_payment(
        self,
    ):
        self.store_.get_allocations = Mock(
            return_value=[
                Allocation(
                    value=Decimal("700.00"),
                    type="fixed",
                    **default_payment_kwargs,
                )
            ]
        )

        self.automate_allocations.run()

        self.bunq_.make_payment.assert_called_once_with(
            amount=Decimal("500.00"), account_id=0, **default_payment_kwargs
        )

    def test_when_amount_smaller_than_minimum_expect_no_payment(
        self,
    ):
        self.store_.get_allocations = Mock(
            return_value=[
                Allocation(
                    value=Decimal("1000.00"),
                    type="fixed",
                    minimum_amount=Decimal("500.01"),
                    **default_payment_kwargs,
                )
            ]
        )

        self.automate_allocations.run()

        self.bunq_.make_payment.assert_not_called()


class TestMixedAllocation:
    def setup_method(self):
        self.bunq_ = MagicMock()
        self.bunq_.make_payment = Mock()
        self.bunq_.get_balance_by_id = Mock(return_value=Decimal("3700.00"))

        self.store_ = MagicMock()
        self.store_.get_main_account_settings = Mock(
            return_value=Settings(minimum=Decimal("1500.00"), id=0)
        )

        self.automate_allocations = AutomateAllocations(
            bunq=self.bunq_, store=self.store_
        )

        self.expected_allocations = [
            dict(
                iban_name="Folkert Plank",
                iban="NL76BUNQ2063655001",
                description="safety net top up",
            ),
            dict(
                iban_name="Folkert Plank",
                iban="NL76BUNQ2063655002",
                description="groceries top up",
            ),
            dict(
                iban_name="Folkert Plank",
                iban="NL76BUNQ2063655003",
                description="pleasure transfer",
            ),
            dict(
                iban_name="Folkert Plank",
                iban="NL76BUNQ2063655004",
                description="stocks transfer",
            ),
        ]
        self.store_.get_allocations = Mock(
            return_value=[
                Allocation(
                    value=Decimal("4000.00"),
                    type="top_up",
                    order=1,
                    **self.expected_allocations[0],
                ),
                Allocation(
                    value=Decimal("250.00"),
                    type="top_up",
                    order=1,
                    **self.expected_allocations[1],
                ),
                Allocation(
                    value=Decimal("250.00"),
                    type="fixed",
                    order=1,
                    **self.expected_allocations[2],
                ),
                Allocation(
                    value=Decimal("33.33"),
                    type="percentage",
                    order=2,
                    **self.expected_allocations[3],
                ),
                Allocation(
                    value=Decimal("66.67"),
                    type="percentage",
                    order=2,
                    **self.expected_allocations[3],
                ),
            ]
        )

    def test_when_mixed_flow_expect_correct_payments(self):
        self.bunq_.get_balance_by_iban = Mock()
        self.bunq_.get_balance_by_iban.side_effect = [
            Decimal("3800.00"),
            Decimal("189.56"),
        ]

        self.automate_allocations.run()

        self.bunq_.make_payment.assert_has_calls(
            [
                call(
                    amount=Decimal("200.00"),
                    account_id=0,
                    **self.expected_allocations[0],
                ),
                call(
                    amount=Decimal("60.44"),
                    account_id=0,
                    **self.expected_allocations[1],
                ),
                call(
                    amount=Decimal("250.00"),
                    account_id=0,
                    **self.expected_allocations[2],
                ),
                call(
                    amount=Decimal("563.13"),
                    account_id=0,
                    **self.expected_allocations[3],
                ),
                call(
                    amount=Decimal("1126.43"),
                    account_id=0,
                    **self.expected_allocations[3],
                ),
            ]
        )

    def test_when_not_enough_money_for_entire_flow_expect_correct_payments(self):
        self.bunq_.get_balance_by_iban = Mock()
        self.bunq_.get_balance_by_id = Mock(return_value=Decimal("1860.00"))
        self.bunq_.get_balance_by_iban.side_effect = [
            Decimal("3800.00"),
            Decimal("189.56"),
        ]

        self.automate_allocations.run()

        self.bunq_.make_payment.assert_has_calls(
            [
                call(
                    amount=Decimal("200.00"),
                    account_id=0,
                    **self.expected_allocations[0],
                ),
                call(
                    amount=Decimal("60.44"),
                    account_id=0,
                    **self.expected_allocations[1],
                ),
                call(
                    amount=Decimal("99.56"),
                    account_id=0,
                    **self.expected_allocations[2],
                ),
            ]
        )

    def test_when_minimum_added_at_the_end_expect_last_payment_not_executed(self):
        self.bunq_.get_balance_by_iban = Mock()
        self.bunq_.get_balance_by_id = Mock(return_value=Decimal("2060.00"))
        self.bunq_.get_balance_by_iban.side_effect = [
            Decimal("3800.00"),
            Decimal("189.56"),
        ]
        self.store_.get_allocations = Mock(
            return_value=[
                Allocation(
                    value=Decimal("4000.00"),
                    type="top_up",
                    order=1,
                    **self.expected_allocations[0],
                ),
                Allocation(
                    value=Decimal("250.00"),
                    type="top_up",
                    order=1,
                    **self.expected_allocations[1],
                ),
                Allocation(
                    value=Decimal("250.00"),
                    type="fixed",
                    order=1,
                    **self.expected_allocations[2],
                ),
                Allocation(
                    value=Decimal("50.00"),
                    type="percentage",
                    order=2,
                    **self.expected_allocations[3],
                ),
                Allocation(
                    value=Decimal("50.00"),
                    type="percentage",
                    order=2,
                    minimum_amount=Decimal("100.00"),
                    **self.expected_allocations[3],
                ),
            ]
        )

        self.automate_allocations.run()

        self.bunq_.make_payment.assert_has_calls(
            [
                call(
                    amount=Decimal("200.00"),
                    account_id=0,
                    **self.expected_allocations[0],
                ),
                call(
                    amount=Decimal("60.44"),
                    account_id=0,
                    **self.expected_allocations[1],
                ),
                call(
                    amount=Decimal("250.00"),
                    account_id=0,
                    **self.expected_allocations[2],
                ),
                call(
                    amount=Decimal("24.78"),
                    account_id=0,
                    **self.expected_allocations[3],
                ),
            ]
        )
