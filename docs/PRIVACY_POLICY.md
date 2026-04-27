# Privacy Policy

**Effective Date:** April 27, 2026
**Last Updated:** April 27, 2026

## 1. Introduction

Looprail ("we", "our", or "us") operates a financial services platform that enables users to manage wallets, make deposits, and process withdrawals. This Privacy Policy explains how we collect, use, store, and protect your personal information when you use our services.

## 2. Information We Collect

### 2.1 Account & Identity Information
- Full name (first name, last name)
- Email address
- Username
- Gender
- Date of birth
- KYC (Know Your Customer) status

### 2.2 Contact & Address Information
- Phone number
- Street address, city, state, postal code, and country

### 2.3 Financial Information
- Wallet balances and transaction history (deposits, withdrawals)
- Bank account details used for transfers
- Exchange rates applied to transactions
- Ledger identity and transaction IDs

### 2.4 Authentication & Security Data
- Hashed passwords and PINs (never stored in plain text)
- Biometric public keys (for device-based biometric authentication)
- OTP (one-time password) records
- Refresh tokens (stored as hashes)
- Failed login attempt counts and account lock timestamps

### 2.5 Device & Session Information
When you log in, we collect:
- IP address
- Device ID, model, brand, manufacturer, name, and product
- Operating system version
- Platform (iOS, Android, etc.)
- User agent string
- FCM (Firebase Cloud Messaging) token for push notifications

### 2.6 Geolocation Data
Derived from your IP address at login:
- Country and country code
- Region and city
- Approximate latitude and longitude

### 2.7 Usage Data
- Session activity and last-seen timestamps
- Onboarding responses
- Email notification preferences

## 3. How We Use Your Information

| Purpose | Data Used |
|---|---|
| Account creation and authentication | Email, password hash, PIN hash, biometrics |
| Identity verification (KYC) | Name, date of birth, address, phone number |
| Processing transactions | Wallet data, bank details, transaction records |
| Security and fraud prevention | IP address, device info, geolocation, failed attempts |
| Push and email notifications | FCM token, email address, notification preferences |
| Customer support | Account details, session history |
| Legal and regulatory compliance | KYC data, transaction records |

## 4. Third-Party Services

We share data with the following third-party providers to operate our services:

- **Paystack** — payment processing and bank transfers
- **Paycrest** — additional payment processing
- **Blnk (Ledger Service)** — financial ledger and transaction management
- **Blockrader** — crypto wallet infrastructure
- **Firebase (FCM)** — push notifications
- **Resend** — transactional email delivery

Each provider has their own privacy policy and data processing terms. We only share the minimum data necessary for each service to function.

## 5. Data Retention

- **Account data** is retained for as long as your account is active.
- **Session data** is retained for security auditing purposes and purged periodically.
- **Transaction records** are retained as required by applicable financial regulations.
- **OTP records** are short-lived and expire automatically.
- If you delete your account, your data is deactivated. Some records may be retained to meet legal obligations.

## 6. Data Security

We implement the following security measures:

- Passwords and PINs are hashed using Argon2 — they are never stored in plain text.
- Biometric authentication uses public-key cryptography; private keys never leave your device.
- All API communication is encrypted in transit (HTTPS/TLS).
- Sessions are invalidated on logout and can be remotely revoked.
- Account lockout is enforced after repeated failed authentication attempts.
- Disposable email addresses are blocked at registration.

## 7. Your Rights

Depending on your jurisdiction, you may have the right to:

- **Access** the personal data we hold about you
- **Correct** inaccurate or incomplete data
- **Delete** your account and associated data
- **Restrict** or **object** to certain processing
- **Data portability** — receive your data in a machine-readable format
- **Withdraw consent** at any time where processing is based on consent

To exercise any of these rights, contact us at the address below.

## 8. Cookies and Tracking

Our backend API does not use browser cookies. Session management is handled via JWT access tokens and refresh tokens transmitted in request headers.

## 9. Children's Privacy

Our services are not directed at individuals under the age of 18. We do not knowingly collect personal data from minors. If you believe a minor has provided us with personal data, please contact us immediately.

## 10. Changes to This Policy

We may update this Privacy Policy from time to time. We will notify you of material changes via email or an in-app notification. Continued use of the service after changes take effect constitutes acceptance of the updated policy.

## 11. Contact Us

If you have questions or concerns about this Privacy Policy or how we handle your data, please contact us at:

**Looprail**
Email: looprail@looprail.xyz
Website: https://looprail.xyz
