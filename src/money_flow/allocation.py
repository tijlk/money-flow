from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore


@dataclass
class Allocation:
    description: str
    strategy: str
    iban: str
    account_type: str
    percentage: Optional[float] = None
    target_balance: Optional[Decimal] = None
    fixed_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    min_amount: Optional[Decimal] = None
    priority: Optional[int] = None
    current_balance: Optional[Decimal] = None


@dataclass
class Settings:
    minimum: Decimal
    id: int


class FireStore:
    def __init__(self, config: str):
        try:
            firebase_admin.get_app()
        except ValueError:
            cred = credentials.Certificate(config)
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()

    def get_main_account_settings(self):
        data = self.db.collection("settings").document("salary_account").get().to_dict()
        return Settings(minimum=Decimal(data.get("minimum")), id=data.get("id"))

    def get_allocations(self, accounts):
        data = self.db.collection("allocation").stream()

        def pop_value_to_decimal(kwargs, key):
            value = kwargs.pop(key, None)
            return Decimal(value) if value else None

        def transform_data(doc):
            kwargs: dict = doc.to_dict()
            max_amount = pop_value_to_decimal(kwargs, "max_amount")
            min_amount = pop_value_to_decimal(kwargs, "min_amount")
            fixed_amount = pop_value_to_decimal(kwargs, "fixed_amount")
            target_balance = pop_value_to_decimal(kwargs, "target_balance")
            bunq_id = kwargs.pop("id", None)
            current_balance = None
            if bunq_id:
                kwargs["description"] = accounts[bunq_id]["description"]
                kwargs["iban"] = accounts[bunq_id]["iban"]
                current_balance = Decimal(accounts[bunq_id]["balance"])
            return Allocation(
                **kwargs,
                max_amount=max_amount,
                min_amount=min_amount,
                target_balance=target_balance,
                current_balance=current_balance,
                fixed_amount=fixed_amount,
            )

        return list(map(transform_data, data))
