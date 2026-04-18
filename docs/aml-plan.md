# AML Plan

## Current State
- `KYCStatus` on `User` — field exists but not enforced
- No risk scoring, velocity checks, or flagging
- `Transaction` model has no AML-related fields

## Proposed Approach

### Layer 1 — Transaction flags (DB)
Add to `Transaction`:
```python
aml_flagged: bool = Field(default=False)
aml_flag_reason: Optional[str] = Field(default=None)
```

### Layer 2 — Rule engine
Simple `AMLService` running checks before a transaction is committed.

Rules to start with:
- **Velocity**: > N transactions in last 24h for this wallet
- **Amount threshold**: single tx > configured limit (e.g. $10k equivalent)
- **KYC gate**: certain transaction types require `KYCStatus.COMPLETED`
- **Sanctioned address**: check sender/receiver against a blocklist

### Layer 3 — Integration points
1. **Deposits** — in `_initialize_deposit_transaction`, after wallet/asset resolved, before creating the transaction
2. **Withdrawals** — in `initiate_withdrawal`, before `_execute_bank_transfer_withdrawal`

### Layer 4 — Flagged transaction handling
| Result | Action |
|--------|--------|
| `PASS` | proceed normally |
| `FLAG` | create tx with `aml_flagged=True`, hold (status=PENDING), don't execute |
| `BLOCK` | reject immediately, return error to user |

## Open Questions
1. Should AML checks be **blocking** (reject) or **flagging** (hold for manual review)?
2. What are the **amount thresholds** — per transaction and per day?
3. Do we have a sanctions list source, or start with velocity + amount rules only?
4. Should flagged transactions be reviewable via an admin endpoint, or just logged for now?
