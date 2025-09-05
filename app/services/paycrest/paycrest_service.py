import requests
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import Depends

from ...models import PaymentOrder
from ....schemas.service_schema import OrderResponse
from ...settings import settings
from ...database import get_db


class PaycrestService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.base_url = settings.paycrest_base_url.rstrip("/")
        self.api_key = settings.paycrest_api_key
        self.headers = {
            "API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def fetch_rate(self, token: str, amount: Decimal, currency: str, network: str) -> str:
        """Fetch conversion rate for token -> fiat"""
        url = f"{self.base_url}/rates/{token}/{float(amount)}/{currency}"
        params = {"network": network}

        resp = requests.get(
            url, headers={"Content-Type": "application/json"}, params=params, timeout=30
        )

        if resp.status_code != 200:
            raise Exception(f"Rate fetch failed {resp.status_code}: {resp.text}")

        return resp.json()["data"]

    async def create_payment_order(
        self,
        user_id: int,
        token: str,
        amount: Decimal,
        network: str,
        recipient: dict,
        reference: str,
        return_address: str,
    ) -> OrderResponse:
        """Create a payment order to off-ramp tokens via Paycrest"""

        currency = recipient.get("currency")
        if not currency:
            raise ValueError("Recipient dict must contain a 'currency' key")

        # Fetch latest rate
        rate = self.fetch_rate(token, amount, currency, network)

        # Build payload
        order_data = {
            "amount": float(amount),
            "token": token,
            "network": network,
            "rate": rate,
            "recipient": recipient,
            "reference": reference,
            "returnAddress": return_address,
        }

        # Call Paycrest API
        resp = requests.post(
            f"{self.base_url}/sender/orders",
            headers=self.headers,
            json=order_data,
            timeout=30,
        )

        if resp.status_code != 200:
            raise Exception(f"Order creation failed {resp.status_code}: {resp.text}")

        data = resp.json()
        order_id = data.get("id")
        receive_address = data.get("receiveAddress")
        sender_fee = data.get("senderFee")
        transaction_fee = data.get("transactionFee")
        valid_until = data.get("validUntil")


        # Log order in DB
        order = PaymentOrder(
            user_id=user_id,
            amount=amount,
            order_id=order_id,
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        # Return response object
        return OrderResponse(
            user_id=user_id,
            order_id=order_id,
            amount=amount,
            receive_address=receive_address,
            sender_fee=sender_fee,
            transaction_fee=transaction_fee,
            valid_until=valid_until,
        )
