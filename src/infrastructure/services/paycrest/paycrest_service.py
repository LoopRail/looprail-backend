from decimal import Decimal
from typing import Optional, Tuple

import requests

from src.dtos import OrderResponse
from src.infrastructure.settings import PayCrestConfig
from src.types import Error, error

PAYCREST_API_VERSION = "v1"

BASE_URL = f"https://api.paycrest.io/{PAYCREST_API_VERSION}"


class PaycrestService:
    def __init__(self, config: PayCrestConfig):
        self.api_key = config.paycrest_api_key
        self.headers = {
            "API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def fetch_rate(
        self, token: str, amount: Decimal, currency: str, network: str
    ) -> Tuple[Optional[str], Error]:  # We do not want to break execution
        """Fetch conversion rate for token -> fiat"""
        url = f"{BASE_URL}/rates/{token}/{float(amount)}/{currency}"
        params = {"network": network}

        resp = requests.get(
            url, headers={"Content-Type": "application/json"}, params=params, timeout=30
        )
        if resp.status_code != 200:
            return None, error(f"Rate fetch failed {resp.status_code}: {resp.text}")

        return resp.json()["data"], None

    async def create_payment_order(
        self,
        user_id: int,
        token: str,
        amount: Decimal,
        network: str,
        recipient: dict,
        reference: str,
        return_address: str,
    ) -> Tuple[Optional[OrderResponse], Error]:
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
            f"{BASE_URL}/sender/orders",
            headers=self.headers,
            json=order_data,
            timeout=30,
        )

        if resp.status_code != 200:
            return None, error(f"Order creation failed {resp.status_code}: {resp.text}")

        data = resp.json()
        order_id = data.get("id")
        receive_address = data.get("receiveAddress")
        sender_fee = data.get("senderFee")
        transaction_fee = data.get("transactionFee")
        valid_until = data.get("validUntil")

        # Return response object
        return OrderResponse(
            user_id=user_id,
            order_id=order_id,
            amount=amount,
            receive_address=receive_address,
            sender_fee=sender_fee,
            transaction_fee=transaction_fee,
            valid_until=valid_until,
        ), None
