import requests
from ...settings import settings

PAYCREST_BASE_URL = "settings.paycrest_base_url".rstrip("/")

def check_order_status(order_id: str) -> dict:
    """Poll Paycrest API for the current status of an order."""
    try:
        response = requests.get(
            f"{PAYCREST_BASE_URL}/sender/orders/{order_id}",
            headers={"API-Key": settings.paycrest_api_key}
        )
        response.raise_for_status()
        order = response.json()

        status = order.get("status")
        if status == "pending":
            # waiting for provider assignment
            pass
        elif status == "validated":
            # funds have been sent to recipient’s bank
            handle_order_validated(order)
        elif status == "settled":
            # provider received stablecoin on-chain
            handle_order_settled(order)
        elif status == "refunded":
            handle_order_refunded(order)
        elif status == "expired":
            handle_order_expired(order)

        return order
    except Exception as e:
        raise RuntimeError(f"Error checking order status: {str(e)}")

# Handlers – here you can update DB, notify user, etc.
def handle_order_validated(order: dict):
    print(f"[VALIDATED] Order {order['id']} confirmed")

def handle_order_settled(order: dict):
    print(f"[SETTLED] Order {order['id']} settled on-chain")

def handle_order_refunded(order: dict):
    print(f"[REFUNDED] Order {order['id']} refunded")

def handle_order_expired(order: dict):
    print(f"[EXPIRED] Order {order['id']} expired")
