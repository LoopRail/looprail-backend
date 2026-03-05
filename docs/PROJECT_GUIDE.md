# LoopRail API — Project Guide

Welcome to the LoopRail Backend API documentation. This guide provides the foundational information needed to integrate with our services.

---

## 🌍 Environments & Base URLs

| Environment     | Base URL                              | Description                         |
| :-------------- | :------------------------------------ | :---------------------------------- |
| **Development** | `http://localhost:8000/api/v1`        | Local development environment.      |
| **Staging**     | `https://staging.looprail.xyz/api/v1` | Pre-production testing environment. |
| **Production**  | `https://api.looprail.xyz/api/v1`     | Live production environment.        |

---

## 🛠 Global Headers

Every request to the LoopRail API **must** include the following headers for security, session tracking, and analytics.

| Header          | Required | Description                                                     | Example                 |
| :-------------- | :------- | :-------------------------------------------------------------- | :---------------------- |
| `X-Device-ID`   | **Yes**  | Unique identifier for the user's device. Prefix with `device_`. | `device_uuid-string`    |
| `X-Platform`    | **Yes**  | The client platform making the request.                         | `ios`, `android`, `web` |
| `X-Session-Id`  | Optional | Required for session-bound actions (e.g., Passcode Login).      | `ses_uuid-string`       |
| `Authorization` | Optional | Required for authenticated routes. Uses Bearer scheme.          | `Bearer <token>`        |

---

## 🔐 Authentication Overview

LoopRail uses a multi-token authentication system to ensure security and smooth onboarding.

1.  **Onboarding Token**: Issued after successful email verification. Used exclusively for setup actions (Transaction PIN, Onboarding questions).
2.  **Access Token**: Short-lived JWT used for all standard API operations.
3.  **Refresh Token**: Long-lived token used to rotate the Access Token without requiring user re-authentication.

See the [Auth Guide](./AUTH_GUIDE.md) for detailed flows.

---

## 📦 Response Format

All responses follow a standard JSON structure.

### Success

```json
{
  "status": "success",
  "data": { ... }
}
```

### Error

```json
{
  "message": "Human-readable error description",
  "error_code": "SPECIFIC_ERROR_CODE"
}
```

---

## 📚 Guides

- [**Authentication & Onboarding**](./AUTH_GUIDE.md) — Sign-up, Login, and Passcode setup.
- [**Wallets & Balances**](./WALLET_GUIDE.md) — Managing assets and initiating withdrawals.
- [**Transactions**](./TRANSACTION_GUIDE.md) — History, status tracking, and metadata.
- [**Webhooks**](./WEBHOOK_GUIDE.md) — Real-time event integration via BlockRadar.
- [**Mobile Integration**](./MOBILE_GUIDE.md) — FCM setup and push notification actions.
- [**Caching**](./CACHING.md) — Internal infrastructure and cache-aside implementation.
