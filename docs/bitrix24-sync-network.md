# Bitrix24 Box Network Contract — prox01 (Gap 4.3)

**Status:** Contract defined; must be verified before production cutover.
**Scope:** One-way sync worker → Bitrix24 Box REST API (`SyncTransport` boundary in
`backend/jol_commerce/bitrix24/sync_client.py`).
**Related:** Blueprint v2.0 §2 (One-Way Bitrix24 Sync), §4.3, `docs/tenancy-threat-model.md` (T7).

## 1. Topology

The Bitrix24 Box instance (dispatch center) runs on **prox01** (Dell PowerEdge R640,
Proxmox VE node, internal `10.60.60.10`, see `jol-infrastructure:docs/servers/prox01.md`).
The sync worker runs on the Django/FastAPI app servers in the application segment.

```
 app servers (Django/FastAPI)          prox01 (Dell R640)
 ┌────────────────────────┐            ┌──────────────────────────────┐
 │ Bitrix24SyncClient     │   mTLS     │ Bitrix24 Box VM              │
 │  └─ SyncTransport ─────┼──────────► │  REST API :443               │
 │     (client cert)      │  VLAN 80   │  source-IP allowlist         │
 └────────────────────────┘  only      └──────────────────────────────┘
```

**Hard rules:**

1. prox01's Bitrix24 VM is reachable **only from the internal network** — no
   public DNS record, no port-forward, no exposure on the WAN edge.
2. The sync path crosses a **dedicated VLAN** (dispatch segment), not the
   Proxmox management VLAN 60 or iDRAC VLAN 10.
3. Sync is one-way at the application layer as well: `apply_inbound_write`
   raises `SyncWriteRejectedError` for any Bitrix24 → core write.

## 2. The Three Required Controls

### 2.1 Internal VPN tunnel / dedicated VLAN

- Sync traffic originates from app servers in the application segment and is
  routed to the dispatch segment over internal routing only (MikroTik
  inter-VLAN, firewalled). No internet path exists to the Bitrix24 REST API.
- The Bitrix24 VM's network interface is attached to the dispatch VLAN
  bridge only; it shares no interface with the management or OOB VLANs.
- Equivalent alternative accepted by this contract: a WireGuard site tunnel
  terminating on prox01 with the same source restrictions.

### 2.2 mTLS client certificate authentication

- The Bitrix24 Box REST endpoint requires a **client certificate**; TLS
  handshake without a valid cert fails before any HTTP exchange.
- Client certificates are issued by the internal CA (cert-manager / Vault
  PKI), one per app server, stored outside the repo, mounted at deploy time.
- Server side presents the internal CA-signed cert; the transport pins the
  CA bundle (`verify=<internal-ca-bundle>`) — public CA trust is not relied on.
- Certificate lifecycle follows `docs/runbooks/certificate-renewal.md`
  (jol-infrastructure); rotation of the sync client cert is recorded in the
  audit hash chain as an admin event.

### 2.3 IP whitelist

- The Bitrix24 VM firewall accepts REST connections **only from the app
  server addresses** (Django/FastAPI hosts). All other sources are dropped
  and logged.
- Enforcement point: PVE guest firewall on the Bitrix24 VM plus the segment
  firewall rule — defense in depth, either alone is sufficient to block.
- The allowlist is part of the change record: adding a source IP requires a
  ticketed change (SOC2 CC7.1 / CC8.1).

## 3. Implementation Mapping

| Contract control | Where it is enforced | Evidence artifact |
|---|---|---|
| Dedicated VLAN / no internet path | prox01 VM network config + MikroTik firewall | `jol-infrastructure:docs/network/` audit output |
| mTLS client certs | `SyncTransport` implementation (httpx with `cert=`/`verify=`) + Bitrix24 Apache/nginx SSLVerifyClient | deploy manifest + TLS handshake test below |
| IP allowlist | PVE guest firewall + segment firewall | firewall rule export |
| One-way direction | `Bitrix24SyncClient.apply_inbound_write` (raises) | `tests/bitrix24/` |
| PII boundary | `PIIScrubber` before transport | `tests/bitrix24/` |

The `SyncTransport` protocol deliberately abstracts the wire: the mTLS and
allowlist guarantees live below it, so a transport implementation that cannot
present a client certificate fails at handshake, not silently.

## 4. Pre-Cutover Verification Checklist

Run from an **app server** (positive) and from any **non-allowlisted host**
(negative). Record outputs in the change ticket.

- [ ] `openssl s_client -connect <bitrix24>:443 -cert client.crt -key client.key -CAfile internal-ca.pem`
      → handshake succeeds, `SSL_verify_client` required.
- [ ] Same command **without** `-cert` → handshake rejected
      (`alert certificate required` / `403`).
- [ ] `curl --resolve` from an allowlisted app server → HTTP 200/401 from the
      REST API (reachable + authenticated path).
- [ ] Same request from a non-allowlisted internal host → connection
      dropped/timeout (IP allowlist holds).
- [ ] External scan (WAN side) confirms no route to the Bitrix24 port —
      prox01 publishes nothing publicly.
- [ ] One sync cycle executed end-to-end; `bitrix24.synced` entry present in
      the audit chain (`jol-cli audit verify` passes).

## 5. Residual Risk

| Risk | Mitigation |
|---|---|
| Compromised app server holds a valid client cert | per-server certs (blast-radius limit), short validity + revocation via CRL/OCSP at the internal CA |
| Bitrix24 Box itself compromised | sync payloads are already PII-scrubbed; no inbound write path exists to the core; tenant DB is unreachable from the dispatch VLAN |
| VLAN misconfiguration during VM moves | change checklist requires re-running section 4 after any prox01 network change |
