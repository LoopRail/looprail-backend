# Transactions & History Guide

This guide describes how to track and detail financial movements within the LoopRail platform.

---

## 📜 Listing Transactions

To retrieve a paginated history of transactions for the authenticated user's wallet.

**Endpoint:** `GET /transactions/`

**Query Parameters:**

- `page`: Page number (default: 1).
- `page_size`: Items per page (default: 10).

**Response:**

```json
{
  "transactions": [
    {
      "id": "txn_...",
      "amount": 100.0,
      "status": "completed",
      "transaction-type": "withdrawal",
      "payment-type": "bank_transfer",
      "created-at": "2023-10-27T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page-size": 10
}
```

---

## 🔍 Transaction Details

Retrieve granular data for a specific transaction, including external references and block hashes (for crypto).

**Endpoint:** `GET /transactions/{transaction_id}`

**Query Parameters:**

- `include_details`: (Boolean) If true, returns type-specific details (e.g., full bank account info).

**Example Response (Crypto):**

```json
{
  "id": "txn_...",
  "status": "completed",
  "amount": "1.5",
  "currency": "ETH",
  "transaction-hash": "0x...",
  "network": "bsc",
  "confirmations": 12,
  "destination": {
    "wallet-address": "0x...",
    "network": "bsc"
  }
}
```

---

## 🚦 Transaction Statuses

| Status       | Description                                                                    |
| :----------- | :----------------------------------------------------------------------------- |
| `pending`    | The transaction has been initiated and is awaiting processing.                 |
| `processing` | The transaction is currently being handled by a background worker or provider. |
| `completed`  | The funds have been successfully moved.                                        |
| `failed`     | The transaction could not be completed. Check `error-message` for details.     |
| `reversed`   | The funds have been returned to the original wallet.                           |

---

## 📎 Metadata & Narration

Transactions can include a custom `narration` (visible to the user) and a `metadata` blob (internal details, e.g., IP address, device info).

```json
{
  "narration": "Payment for services",
  "metadata": {
    "ip_address": "192.168.1.1",
    "location": "Lagos, Nigeria"
  }
}
```
