# Push Notifications — Mobile Integration Guide

This document describes the push notification events sent by the LoopRail backend
via Firebase Cloud Messaging (FCM). It covers when each event fires, the full FCM
message payload, and how to handle it on Android and iOS.

---

## How to Register an FCM Token

Send the device FCM token during **login** so the backend can associate it with the session:

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secret",
  "allow_notifications": true,
  "fcm_token": "<your-fcm-token>"
}
```

| Field                 | Type             | Notes                                                     |
| --------------------- | ---------------- | --------------------------------------------------------- |
| `allow_notifications` | `bool`           | **Required.** Set `true` to enable push for this session. |
| `fcm_token`           | `string \| null` | Required when `allow_notifications` is `true`.            |

The token is stored on the session. All active sessions with `allow_notifications=true` will receive push notifications for that user.

---

## FCM Message Structure

Every push notification has the following top-level structure:

```json
{
  "notification": {
    "title": "...",
    "body": "...",
    "image": "https://..."
  },
  "data": {
    "action": "ACTION_NAME",
    "campaign_id": "",
    "campaign_name": "",
    "<custom_key>": "<custom_value>"
  },
  "android": {
    "priority": "high",
    "notification": {
      "channel_id": "default",
      "sound": "default",
      "color": "#4CAF50",
      "icon": "ic_notification"
    }
  },
  "apns": {
    "payload": {
      "aps": {
        "sound": "default",
        "badge": 1,
        "mutable-content": 1
      }
    }
  }
}
```

The `data.action` field is the **primary routing key** you should use to decide how to handle the notification.

---

## Notification Actions

### `NONE`

**When:** Generic/fallback notifications with no specific action. No deep-link or special handling required.

**Data payload:**

```json
{ "action": "NONE", "campaign_id": "", "campaign_name": "" }
```

---

### `DEPOSIT_RECEIVED`

**When:** A crypto deposit has been detected on-chain and is pending confirmation/sweep.

**Use for:** Showing a "Pending" status update in the transaction history screen.

**Data payload:**

```json
{
  "action": "DEPOSIT_RECEIVED",
  "campaign_id": "",
  "campaign_name": "",
  "transaction_id": "txn_<id>",
  "amount": "100.00",
  "asset": "USDC",
  "network": "base"
}
```

**Recommended UX:** Navigate to the transaction detail screen and show a pending/processing badge.

---

### `DEPOSIT_CONFIRMED`

**When:** The deposit has been swept and the user's balance has been updated.

**Use for:** Showing a "Completed" update and triggering a balance refresh.

**Data payload:**

```json
{
  "action": "DEPOSIT_CONFIRMED",
  "campaign_id": "",
  "campaign_name": "",
  "transaction_id": "txn_<id>",
  "amount": "100.00",
  "asset": "USDC",
  "network": "base"
}
```

**Recommended UX:** Navigate to the transaction detail screen, update balance in the UI.

---

### `WITHDRAWAL_INITIATED`

**When:** The user has submitted a withdrawal request and it has been enqueued for processing.

**Use for:** Confirming the request was received; show a "Pending" status.

**Data payload:**

```json
{
  "action": "WITHDRAWAL_INITIATED",
  "campaign_id": "",
  "campaign_name": "",
  "transaction_id": "txn_<id>",
  "amount": "50.00",
  "asset": "USDC",
  "destination": "0x..."
}
```

---

### `WITHDRAWAL_PROCESSED`

**When:** The withdrawal has been executed by the background worker.

**Use for:** Confirming the funds have left the account; show a "Completed" or "Failed" status.

**Data payload:**

```json
{
  "action": "WITHDRAWAL_PROCESSED",
  "campaign_id": "",
  "campaign_name": "",
  "transaction_id": "txn_<id>",
  "amount": "50.00",
  "asset": "USDC",
  "status": "completed"
}
```

---

## Welcome Notification (Onboarding)

Sent once after the user completes onboarding, if they provided an `fcm_token` in the `CompleteOnboarding` request.

```json
{
  "notification": {
    "title": "Welcome to LoopRail! 🚀",
    "body": "Your onboarding is complete. Start exploring now."
  },
  "data": {
    "action": "NONE",
    "campaign_id": "",
    "campaign_name": ""
  }
}
```

---

## Android — Handling Notifications

```kotlin
class MyFirebaseMessagingService : FirebaseMessagingService() {

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        val action = remoteMessage.data["action"]
        val transactionId = remoteMessage.data["transaction_id"]

        when (action) {
            "DEPOSIT_RECEIVED"      -> navigateToTransaction(transactionId, status = "pending")
            "DEPOSIT_CONFIRMED"     -> navigateToTransaction(transactionId, status = "confirmed")
            "WITHDRAWAL_INITIATED"  -> navigateToTransaction(transactionId, status = "pending")
            "WITHDRAWAL_PROCESSED"  -> navigateToTransaction(transactionId, status = "completed")
            else                    -> showGenericNotification(remoteMessage)
        }
    }

    override fun onNewToken(token: String) {
        // Re-authenticate or PATCH the session to update the stored FCM token
    }
}
```

**Register in `AndroidManifest.xml`:**

```xml
<service android:name=".MyFirebaseMessagingService" android:exported="false">
    <intent-filter>
        <action android:name="com.google.firebase.MESSAGING_EVENT" />
    </intent-filter>
</service>
```

---

## iOS (Swift) — Handling Notifications

```swift
extension AppDelegate: UNUserNotificationCenterDelegate, MessagingDelegate {

    // Called when a notification is tapped or received in foreground
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        let userInfo = response.notification.request.content.userInfo
        guard let action = userInfo["action"] as? String else { return }
        let transactionId = userInfo["transaction_id"] as? String

        switch action {
        case "DEPOSIT_RECEIVED", "DEPOSIT_CONFIRMED",
             "WITHDRAWAL_INITIATED", "WITHDRAWAL_PROCESSED":
            navigateToTransaction(id: transactionId, userInfo: userInfo)
        default:
            break
        }
        completionHandler()
    }

    func messaging(_ messaging: Messaging, didReceiveRegistrationToken fcmToken: String?) {
        guard let token = fcmToken else { return }
        // Send to backend on next login or via a dedicated PATCH endpoint
    }
}
```

---

## Channel IDs (Android)

Creating notification channels on first launch is recommended:

| `channel_id` | Name    | Description                            |
| ------------ | ------- | -------------------------------------- |
| `default`    | General | Fallback channel for all notifications |

You can extend this list by adding new channels in the backend's `PushNotificationDTO`.

---

## Priority

All notifications are sent with `priority: "high"` (Android) and `mutable-content: 1` (iOS) to ensure delivery even in low-power states.
