# Notification Encryption Key Management (Gap 4.6)

**Scope:** Payload encryption for `confidential` and `restricted` notification
classes (`backend/jol_commerce/notifications/` — `Notification.encrypted_payload`,
Blueprint v2.0 §3.3).
**Related:** ADR-003 secrets management (jol-infrastructure),
`docs/runbooks/secret-rotation.md` (jol-infrastructure).

## 1. Answers to the Audit Questions

| Question | Answer |
|---|---|
| Are keys in HashiCorp Vault? | **Yes.** Notification payload keys live in Vault KV v2 under `secret/data/jol-commerce/notifications/`; envelope master key operations use the Vault Transit engine (`jol-notifications` key). Application pods never hold plaintext key material in config or images — keys are fetched at runtime via External Secrets / Vault agent. |
| Rotation schedule? | **90 days** for data keys, aligned with the platform secret-rotation runbook. Transit master key rotation is annual and non-destructive (Vault keeps all key versions). |
| Old keys during rotation? | **Dual-key window.** Every ciphertext is versioned (`enc:v{kid}:…`), so queued notifications are always decrypted with the key that encrypted them. The previous key version stays readable for the full drain window (see §4). |

## 2. Envelope Scheme

Payloads are encrypted with an AES-256-GCM **data key**; the data key itself
is wrapped by the Vault Transit master key (envelope encryption). The stored
`encrypted_payload` is a self-describing envelope:

```
enc:v3:<base64(wrapped_data_key)>:<base64(nonce)>:<base64(ciphertext+tag)>
```

- `v3` — the **key version ID (kid)** at encryption time; it selects which
  data key decrypts this payload. Never inferred from "current".
- GCM provides integrity: any tampering with the ciphertext fails
  authentication at decrypt time (audit events: `notification.decrypt_failed`).
- Plaintext payloads for confidential+ classes are never persisted — only the
  envelope is stored/queued (classification enforcement in
  `NotificationService.send` rejects confidential+ without `encrypted_payload`).

## 3. Key Hierarchy

| Layer | Location | Rotation | Access |
|---|---|---|---|
| Master key (KEK) | Vault Transit `jol-notifications` | annual (new version, rewrap lazy) | decrypt-capable policy: notification workers only |
| Data keys (DEK) | wrapped by KEK; per-key metadata in Vault KV v2 | 90 days | `notifications:encrypt` policy: app servers |
| Wrapped DEK store | Vault KV v2 `secret/data/jol-commerce/notifications/keys/v{kid}` | versions retained ≥ 180 days after retire | read: notification workers |

## 4. Rotation Procedure (zero dead notifications)

The invariant: **a ciphertext is only retired after no queued notification
references its kid.**

1. **T+0 — issue new key.** Create data key `v{kid+1}`, wrap via Transit,
   publish to KV. New encryptions immediately use `v{kid+1}`. Decryption
   accepts both `v{kid}` and `v{kid+1}` (dual-key window opens).
2. **T+0..T+7d — drain.** Queued/pending notifications still carrying
   `enc:v{kid}:…` are delivered and decrypted with the old key. Retry
   backoff guarantees the queue drains within the retention window; a
   monitoring alert fires if any `v{kid}` envelope remains queued past T+7d.
3. **T+7d — retire.** Old key moves to *decrypt-only*: encryption refuses
   `v{kid}`; workers keep it loaded. Audit entry `notification.key_retired`.
4. **T+90d+180d — destroy.** After the longest possible retry horizon
   (notification retention policy), the wrapped DEK metadata is deleted from
   KV and the transit version revoked. Audit entry `notification.key_destroyed`.

Because the kid travels inside the envelope, steps 2–4 can slip without any
risk of undecryptable notifications — decryption never depends on which key
is "current".

## 5. Failure Modes & Handling

| Failure | Detection | Response |
|---|---|---|
| Ciphertext tampering / corrupted envelope | GCM auth failure at decrypt | notification quarantined, `notification.decrypt_failed` audited, delivery skipped (never fallback to plaintext) |
| Unknown kid (key destroyed too early) | kid lookup miss | quarantine + incident (this is the "dead notification" failure the dual-key window prevents; procedure §4 makes it operationally impossible) |
| Vault unavailable | worker cannot fetch DEK | queue holds envelopes (no plaintext ever cached); delivery resumes after Vault recovers — nothing is lost because plaintext was never stored |

## 6. Verification

- Rotation drill: quarterly, run a rotation end-to-end in staging; assert a
  queued `v{kid}` notification delivers successfully **after** `v{kid+1}`
  becomes current (drains with old key). Record evidence for SOC2 CC6.1.
- Policy checks: Vault policy exports reviewed in the semi-annual access
  review — only notification workers hold decrypt capability.
