# Looprail Withdrawal Workflow and Device ID Guide

This document provides a comprehensive overview of the withdrawal process in the Looprail backend and explains the role and usage of the `device_id`.

## Withdrawal Workflow

The withdrawal process is a two-phase operation designed for security and reliability. It involves initiating a withdrawal request and then processing it after user verification.

### Phase 1: Initiate Withdrawal

This phase creates a withdrawal request and a corresponding transaction record in a `PENDING` state.

**Endpoint:** `POST /api/v1/wallets/inititate-withdraw`

**Authentication:** Requires a valid `access-token`.

**Request Body:**

The request body should be a JSON object with the following structure:

```json
{
  "asset_id": "ast_xxxxxxxxxxxxxxxx",
  "amount": "100.00",
  "currency": "USD",
  "narration": "Withdrawal to my bank account",
  "destination": {
    "event": "withdraw:bank-transfer", // or "withdraw:external-wallet"
    "data": {
      // For "withdraw:bank-transfer"
      "bank_code": "044",
      "account_number": "1234567890",
      "account_name": "John Doe",

      // For "withdraw:external-wallet"
      "address": "0x...",
      "chain": "ethereum"
    }
  }
}
```

**Response:**

A successful initiation request returns a JSON object containing the `transaction_id`, `paycrest_rate`, and `blockrader_fee`.

```json
{
  "data": {
    "transaction_id": "txn_xxxxxxxxxxxxxxxx",
    "paycrest_rate": { ... },
    "blockrader_fee": { ... }
  }
}
```

### Phase 2: Process Withdrawal

After initiating the withdrawal, the user must authorize the transaction by providing their transaction PIN and a PKCE code verifier. This phase executes the actual transfer of funds.

**Endpoint:** `POST /api/v1/wallets/process-withdraw`

**Authentication:** Requires a valid `access-token`.

**Request Body:**

```json
{
  "transaction_id": "txn_xxxxxxxxxxxxxxxx",
  "transation_pin": "123456",
  "challenge_id": "...",
  "code_verifier": "..."
}
```

**Response:**

A successful processing request will enqueue a background task to handle the withdrawal and return a confirmation message.

```json
{
  "message": "Withdrawal processing initiated successfully."
}
```

The background task will then:
1.  Verify the user's transaction PIN.
2.  Debit the user's ledger balance.
3.  Update the transaction status to `COMPLETED` or `FAILED`.

## Device ID (`device_id`)

The `device_id` is a crucial component for ensuring the security of user sessions. It is a unique identifier for the user's device that helps prevent session hijacking.

### Purpose

The `device_id` links a user's session to a specific device. When a user logs in or performs other authenticated actions, the `device_id` sent in the request header is validated against the one stored in the session. This ensures that the request is coming from the same device that initiated the session.

### Generation

The `device_id` must be generated on the client-side. It is the client's responsibility to create and store a unique identifier for the device.

**We recommend using a Universally Unique Identifier (UUID) for the `device_id`.** When generating the `device_id`, ensure it is prefixed with `device_` as defined in the system's `DeviceID` type. Most platforms and languages provide libraries for generating UUIDs.

### Usage

The `device_id` must be included as an `X-Device-ID` header in all authentication-related API requests, including:

*   `/auth/login`
*   `/auth/create-user`
*   `/auth/token` (refreshing an access token)
*   `/auth/complete_onboarding`
*   `/auth/passcode-login`

**Example Header:**

```
X-Device-ID: device_123e4567-e89b-12d3-a456-426614174000
```

By consistently sending the `device_id`, you enhance the security of your application and protect your users' accounts.
