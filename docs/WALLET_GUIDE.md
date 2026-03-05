# Wallets, Assets & Withdrawals Guide

This guide covers how to retrieve account balances and move funds out of the LoopRail ecosystem.

---

## 🏦 Account Overview

### Get All Account Data

**Endpoint:** `GET /account/me`

Returns the current user's profile details along with their wallet and active asset balances.

**Response:**

```json
{
  "user": {
    "username": "johndoe",
    "email": "user@example.com",
    "is_email_verified": true
  },
  "wallet": {
    "wallet_id": "wal_...",
    "assets": [
      {
        "asset_id": "ass_...",
        "symbol": "USDC",
        "balance": "150.50"
      }
    ]
  }
}
```

---

## 💰 Assets & Balances

### Get Specific Asset Balance

**Endpoint:** `GET /wallets/assets/{asset_id}/balance`

Fetches the real-time balance for a specific asset. This call bypasses the cache to ensure absolute accuracy.

**Response:**

```json
{
  "asset_id": "ass_...",
  "balance": "150.50",
  "symbol": "USDC"
}
```

---

## 💸 Withdrawals

Withdrawals are multi-step processes that require PIN authorization and background processing.

### Initiate Withdrawal

**Endpoint:** `POST /wallets/withdraw`

**Request:**

```json
{
  "asset_id": "ass_...",
  "amount": 50.0,
  "destination": {
    "type": "on_chain",
    "address": "0x..."
  },
  "authorization": {
    "pin": "123456"
  }
}
```

### Withdrawal Workflow

1.  **Authorization**: The system verifies the 6-digit `transaction_pin`.
2.  **Lock Check**: If the PIN is incorrect 3 times, withdrawals for the account are locked for 15 minutes.
3.  **Initiation**: The system records the intent and issues a transaction ID.
4.  **Processing**: The withdrawal is enqueued for background processing (interfacing with BlockRadar and Blnk Ledger).

---

## 🔍 Account Verification

### Verify External Account (NUBAN/Bank)

**Endpoint:** `POST /account/verify`

Used to verify bank account details before initiating a withdrawal to a traditional bank.

**Request:**

```json
{
  "account_identifier": "0123456789",
  "institution_code": "058",
  "institution_country": "NG"
}
```

**Response:** Returns the verified account name if successful.
