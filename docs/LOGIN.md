# User Login API Guide

This document provides a guide to the different methods for authenticating users in the Looprail backend.

## Standard Email & Password Login

This is the primary method for users to log in using their email and password.

- **Endpoint:** `POST /api/v1/auth/login`
- **Method:** `POST`
- **Headers:**
    - `Content-Type: application/json`
    - `X-Device-ID: <user's_device_id>`
    - `X-Platform: <ios|android|web>`

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "a_strong_password"
}
```

**Responses:**

There are two possible successful responses depending on the user's onboarding status.

**1. Onboarding Incomplete:**

If the user has not completed the onboarding process, the API returns an `onboarding_token`. The user must complete the onboarding flow before they can fully log in.

```json
{
  "message": "Login successful. Please complete onboarding.",
  "user": { ... },
  "access-token": "a.jwt.onboarding_token"
}
```

**2. Onboarding Complete:**

If the user has completed onboarding, the API returns a full set of authentication tokens (`access-token` and `refresh-token`) for the user's session.

```json
{
  "message": "Login successful.",
  "session_id": "ses_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "access-token": "a.jwt.access_token",
  "refresh-token": "a.jwt.refresh_token",
  "user": { ... }
}
```

---

## Passcode Login

This method allows users to log in quickly using a 6-digit passcode associated with a specific session. This is typically used for re-authenticating on a trusted device.

- **Endpoint:** `POST /api/v1/auth/passcode-login`
- **Method:** `POST`
- **Headers:**
    - `Content-Type: application/json`
    - `X-Device-ID: <user's_device_id>`
    - `X-Platform: <ios|android|web>`
    - `X-Session-Id: <user's_session_id>`

**Request Body:**

The request requires the passcode and a PKCE challenge/verifier pair.

```json
{
  "passcode": "123456",
  "challenge_id": "chl_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "code_verifier": "a_pkce_code_verifier"
}
```

**Response:**

A successful passcode login returns a new `access-token` for the existing session.

```json
{
  "message": "Passcode login successful",
  "session_id": "ses_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "access-token": "a.jwt.access_token",
  "user": { ... }
}
```

---

## Refreshing an Access Token

When an `access-token` expires, a `refresh-token` can be used to obtain a new one without requiring the user to log in again.

- **Endpoint:** `POST /api/v1/auth/token`
- **Method:** `POST`
- **Headers:**
    - `Content-Type: application/json`
    - `X-Device-ID: <user's_device_id>`
    - `X-Platform: <ios|android|web>`

**Request Body:**

```json
{
  "refresh_token": "a.jwt.refresh_token"
}
```

**Response:**

The API returns a new `access-token` and a new `refresh-token`. The old refresh token is invalidated (token rotation).

```json
{
  "access-token": "a.new.jwt.access_token",
  "refresh-token": "a.new.jwt.refresh_token"
}
```
