from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


@dataclass
class Allocation:
    description: str
    value: Decimal
    type: str
    iban: str
    iban_name: str
    minimum_amount: Optional[Decimal] = None
    order: Optional[int] = None


@dataclass
class Settings:
    minimum: Decimal
    id: int


class FireStore:
    def __init__(self, config: str):
        cred = credentials.Certificate(config)
        firebase_admin.initialize_app(cred)
        self.db = firestore.client()

    def get_main_account_settings(self):
        data = self.db.collection("settings").document("main_account").get().to_dict()

        return Settings(minimum=Decimal(data.get("minimum")), id=data.get("id"))

    def get_allocations(self):
        data = self.db.collection("allocation").stream()

        def transform_data(doc):
            kwargs: dict = doc.to_dict()
            amount = kwargs.pop("value")
            minimum_amount = kwargs.pop("minimum")
            return Allocation(
                **kwargs, value=Decimal(amount), minimum_amount=Decimal(minimum_amount)
            )

        return list(map(transform_data, data))
