# Mobile Integration & Push Notifications

This guide describes how to integrate mobile clients (iOS & Android) with LoopRail's real-time notification system via Firebase Cloud Messaging (FCM).

---

## 📲 FCM Token Registration

Mobile clients must register their FCM token during the **Login** or **Onboarding** flow.

**Endpoint:** `POST /api/v1/auth/login` (or `/auth/complete-onboarding`)

**Payload:**

```json
{
  "allow_notifications": true,
  "fcm_token": "FCM_TOKEN_FROM_SDK"
}
```

---

## 🔔 Notification Actions

The `data.action` field in the FCM payload is the **primary routing key** for mobile apps.

| Action                 | When it fires                      | Suggested Client UX                   |
| :--------------------- | :--------------------------------- | :------------------------------------ |
| `DEPOSIT_RECEIVED`     | Crypto deposit detected (pending). | Update transaction to "Pending".      |
| `DEPOSIT_CONFIRMED`    | Asset swept and balance updated.   | Refresh balance and mark "Completed". |
| `WITHDRAWAL_INITIATED` | Request enqueued.                  | Show "Pending Withdrawal".            |
| `WITHDRAWAL_PROCESSED` | Broadcaster confirmed or failed.   | Finalize status/show error.           |

---

## 📦 FCM Payload Example

```json
{
  "notification": {
    "title": "Deposit Received! 💰",
    "body": "Welcome aboard! Your Looprail account is ready. Send, receive, and manage cross-border payments with ease."
  },
  "data": {
    "action": "DEPOSIT_RECEIVED",
    "transaction_id": "txn_...",
    "amount": "100.00",
    "asset": "USDC"
  }
}
```

---

## 💻 Implementation Snippet (Android)

```kotlin
override fun onMessageReceived(remoteMessage: RemoteMessage) {
    val action = remoteMessage.data["action"]

    when (action) {
        "DEPOSIT_CONFIRMED" -> refreshWalletBalance()
        "WITHDRAWAL_PROCESSED" -> updateTransactionHistory()
    }
}
```

---

## 🍎 Implementation Snippet (iOS)

```swift
func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse, withCompletionHandler completionHandler: @escaping () -> Void) {
    let userInfo = response.notification.request.content.userInfo
    if let action = userInfo["action"] as? String {
        // Handle action routing
    }
    completionHandler()
}
```
