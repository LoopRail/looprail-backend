# Authentication & Onboarding Guide

This guide details the complete user lifecycle from registration to active session management.

---

## 🚀 The Onboarding Flow

New users must complete a four-step sequence before they can access standard API features.

### 1. Register Account

**Endpoint:** `POST /auth/create-user`

Registers the user and triggers an email OTP.

**Request:**

```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "strong-password",
  "first_name": "John",
  "last_name": "Doe",
  "gender": "male",
  "phone_number": "+2348000000000",
  "country_code": "NG"
}
```

**Response:** Returns `otp_token` required for verification.

### 2. Verify Email OTP

**Endpoint:** `POST /verify/onboarding-otp`

Validates the OTP sent to the user's email.

**Headers:**

- `X-OTP-Token: <otp_token>`

**Request:**

```json
{
  "otp": "123456"
}
```

**Response:** Returns `access-token` (Onboarding type).

### 3. Setup Wallet & Security

**Endpoint:** `POST /auth/setup-wallet`

Sets the transaction PIN and initializes the on-chain wallet.

**Headers:**

- `Authorization: Bearer <onboarding-token>`

**Request:**

```json
{
  "transaction_pin": "123456"
}
```

### 4. Complete Onboarding

**Endpoint:** `POST /auth/complete-onboarding`

Submits onboarding questionnaire and issues final session tokens.

**Headers:**

- `Authorization: Bearer <onboarding-token>`
- `X-Device-ID: <device_id>`
- `X-Platform: <platform>`

**Request:**

```json
{
  "questioner": ["Answer 1", "Answer 2"],
  "allow_notifications": true,
  "fcm_token": "<fcm-token>"
}
```

**Response:** Returns full `access-token`, `refresh-token`, and `session_id`.

---

## 🔑 Login Methods

### Standard Login

**Endpoint:** `POST /auth/login`

**Request:**

```json
{
  "email": "user@example.com",
  "password": "password",
  "allow_notifications": true,
  "fcm_token": "<fcm-token>"
}
```

- If onboarding is incomplete, it returns an `access-token` (Onboarding type) and a 403-like message.
- If complete, returns full session tokens.

### Passcode Login (Biometric/Fast Login)

**Endpoint:** `POST /auth/passcode-login`

Used for re-authenticating an existing session without a password. REQUIRES a PKCE challenge.

**Headers:**

- `X-Device-ID`: Must match original session.
- `X-Session-Id`: The active session identifier.

**Request:**

```json
{
  "passcode": "123456",
  "challenge_id": "chl_...",
  "code_verifier": "..."
}
```

---

## 🔄 Token Management

### Refresh Token

**Endpoint:** `POST /auth/token`

Rotates the expired Access Token.

**Request:**

```json
{
  "refresh_token": "<current-refresh-token>"
}
```

### Logout

**Endpoint:** `POST /auth/logout`

Revokes the current session.

---

## 🛡 Security & Locks

- **Account Locking**: Accounts are locked for 15 minutes after 3 failed login/passcode attempts.
- **PIN Authorization**: Sensitive actions (withdrawals) require the 6-digit transaction PIN set during Step 3.
