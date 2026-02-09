# User Logout API Guide

This document provides a guide to the different methods for logging out users in the Looprail backend.

## Logout from Current Session

This endpoint invalidates the user's current session, effectively logging them out from the device they are currently using.

- **Endpoint:** `POST /api/v1/auth/logout`
- **Method:** `POST`
- **Headers:**
    - `Authorization: Bearer <user's_access_token>`

**Request Body:**

No request body is required.

**Response:**

A successful logout request returns a confirmation message.

```json
{
  "message": "Logged out successfully"
}
```

---

## Logout from All Sessions

This endpoint invalidates all of the user's active sessions across all devices. This is useful for security purposes, for example, if a user believes their account may be compromised.

- **Endpoint:** `POST /api/v1/auth/logout-all`
- **Method:** `POST`
- **Headers:**
    - `Authorization: Bearer <user's_access_token>`

**Request Body:**

No request body is required.

**Response:**

A successful request returns a confirmation message.

```json
{
  "message": "Logged out from all sessions successfully"
}
```
