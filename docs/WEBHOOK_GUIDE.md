# Webhooks & Asynchronous Events

LoopRail uses webhooks to handle real-time updates for on-chain events (deposits, sweepings, and withdrawals) via **BlockRadar**.

---

## 🔌 Endpoint Configuration

All webhooks must be sent to the following URI:

`POST /api/v1/webhooks/blockrader`

### Security

Webhooks are verified using a signature from BlockRadar. In development/staging, ensure your `BLOCKRADER_API_KEY` is correctly configured in the `.env` file to allow incoming testnet events.

---

## 📥 Supported Events

### 1. Deposit Success (`deposit.success`)

Triggered when a user sends funds to their LoopRail-provided wallet address.

**System Action:**

- Increments the user's balance in the Blnk Ledger.
- Creates a `deposit` transaction in the database.
- Sends a push notification to the user.

### 2. Deposit Swept (`deposit.swept.success`)

Triggered when LoopRail moves funds from a user's temporary deposit address to the primary treasury wallet.

### 3. Withdrawal Success (`withdraw.success`)

Triggered when a requested withdrawal has been successfully broadcast and confirmed on the blockchain.

**System Action:**

- Marks the transaction as `completed` in the database.
- Finalizes the ledger entry.

### 4. Withdrawal Failed (`withdraw.failed`)

Triggered if a withdrawal fail on-chain (e.g., out of gas or rejected).

**System Action:**

- Marks the transaction as `failed`.
- **Reverses** the funds in the user's ledger so they can try again.

---

## 📄 Payload Structure

Every webhook follows a consistent wrapper:

```json
{
  "event": "deposit.success",
  "data": {
    "id": "br_...",
    "reference": "txn_...",
    "amount": "100.0",
    "currency": "USDC",
    "network": "bsc",
    "hash": "0x...",
    "status": "success",
    "wallet": {
      "wallet_id": "wal_..."
    }
  }
}
```

---

## 🛠 Handling Webhooks Locally

To test webhooks during development:

1.  Use a tool like **ngrok** to expose your local port 8000.
2.  Configure the ngrok URL in your BlockRadar dashboard.
3.  Simulate events or send testnet tokens to a generated address.
