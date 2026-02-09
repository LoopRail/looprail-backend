# User Signup and Onboarding API Guide

This document provides a step-by-step guide to the user signup and onboarding process in the Looprail backend.

## Overview

The user signup process is a multi-step flow that involves creating a user, verifying their email via OTP, setting up a wallet, and completing the onboarding process.

## Step 1: Create User

This is the first step where a new user is created in the system.

- **Endpoint:** `POST /api/v1/auth/create-user`
- **Method:** `POST`
- **Headers:**
    - `Content-Type: application/json`

**Request Body:**

The request body must contain the user's details.

```json
{
  "email": "user@example.com",
  "password": "a_strong_password",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890"
}
```

**Response:**

On successful user creation, the API sends an OTP to the user's email and returns a response containing the user object and an `otp_token`. This token is required for the next step.

```json
{
  "user": {
    "id": "usr_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "is_email_verified": false,
    "has_completed_onboarding": false
  },
  "otp_token": "a.jwt.token_for_otp_verification"
}
```

## Step 2: Verify Onboarding OTP

The user must provide the OTP they received via email to verify their account.

- **Endpoint:** `POST /api/v1/verify/onboarding-otp`
- **Method:** `POST`
- **Headers:**
    - `Content-Type: application/json`
    - `Authorization: Bearer <otp_token_from_step_1>`

**Request Body:**

```json
{
  "otp": "123456"
}
```

**Response:**

A successful OTP verification returns an `OnBoardingToken` which is required for the subsequent onboarding steps.

```json
{
  "message": "OTP verified successfully",
  "access_token": "a.jwt.onboarding_token"
}
```

## Step 3: Setup Wallet

After verifying their email, the user needs to set up their wallet by creating a transaction PIN.

- **Endpoint:** `POST /api/v1/auth/setup-wallet`
- **Method:** `POST`
- **Headers:**
    - `Content-Type: application/json`
    - `Authorization: Bearer <onboarding_token_from_step_2>`

**Request Body:**

```json
{
  "transaction_pin": "1234"
}
```

**Response:**

A successful request returns a confirmation message.

```json
{
  "message": "Wallet setup initiated successfully"
}
```

## Step 4: Complete Onboarding

This is the final step of the onboarding process where the user provides additional information.

- **Endpoint:** `POST /api/v1/auth/complete_onboarding`
- **Method:** `POST`
- **Headers:**
    - `Content-Type: application/json`
    - `Authorization: Bearer <onboarding_token_from_step_2>`
    - `X-Device-ID: <user's_device_id>`
    - `X-Platform: <ios|android|web>`

**Request Body:**

```json
{
  "allow_notifications": true,
  "questioner": [
    {
      "question": "What is your primary goal?",
      "answer": "To save and invest."
    }
  ]
}
```

**Response:**

Upon successful completion, the API returns a full set of authentication tokens (`access-token` and `refresh-token`) for the user's session, along with the user's public data.

```json
{
  "message": "User onboarded successfully",
  "session_id": "ses_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "refresh-token": "a.jwt.refresh_token",
  "access-token": "a.jwt.access_token",
  "user": {
    "id": "usr_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "is_email_verified": true,
    "has_completed_onboarding": true
  }
}
```

After completing these steps, the user is fully signed up and authenticated. They can now use their `access-token` for all subsequent authenticated API requests.
