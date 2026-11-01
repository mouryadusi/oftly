# OFTLY security report (v0.4.0)

**Verdict:** suitable for a **small, invite-only friends-and-family beta over HTTPS**. **Not ready for public launch.** No independent security assessment has been done; get one before public release. Nothing here means "completely secure".

## 1. Architecture (what protects what)
```
Browser/iPhone ──HTTPS (proxy/tunnel)──► LocalGuard ► BodyLimit ► AuthGuard ► routes
   LocalGuard : Host allow-list (anti DNS-rebinding), cross-site write refusal (Origin), CSP + security headers, HSTS over HTTPS
   BodyLimit  : 10 MB uploads / 1 MB everything else, refuses length-less bodies
   AuthGuard  : session lookup, CSRF double-submit, then binds THIS user's data folder to the request
Data:  data/accounts.db (users, session hashes, reset-token hashes, audit)   data/users/<uuid>/oftly.db + media/   (one folder per account)
```
**Why per-account folders:** the signed-in user id selects their own database file and photo folder. Routes cannot query another account because that account's data is not reachable from the request context at all (no `WHERE user_id=` to forget). TLS is terminated by your tunnel/proxy, not by the app.

## 2. Implemented controls
| Control | How it protects users | Verified by (automated) | State |
|---|---|---|---|
| Argon2id password hashing | A database leak doesn't reveal passwords | `test_passwords_are_argon2id_and_sessions_are_stored_hashed` | ✅ tested |
| Password policy (12–128 chars, common-password and email-name checks) | Blocks trivially guessable passwords | `test_weak_passwords_rejected` | ✅ tested |
| Generic login errors, equal-cost hash for unknown emails | Prevents account enumeration by message/timing | `test_login_logout_and_generic_errors` (timing not measured) | ⚠️ messages tested, timing unproven |
| Brute-force protection: per-IP + per-account limits and 15-min lockout (lockout persists in DB) | Slows password guessing | `test_brute_force_is_throttled…`, `test_account_lockout_persists…`, `test_registration_rate_limit_per_ip`, `test_forgot_is_rate_limited…` | ✅ tested (in-memory limiter: see §3) |
| Sessions: 256-bit random token, only SHA-256 stored, HttpOnly + SameSite=Lax cookie, 7-day idle / 30-day absolute expiry, revocation on logout, logout-all, password change, reset, deletion | Stolen DB ≠ usable sessions; sessions can be killed | `test_register_sets_httponly…`, `test_idle_and_absolute_expiry_and_tampering`, `test_logout_all_revokes_every_device`, `test_password_change_signs_out_other_devices…` | ✅ tested; Secure flag tested via forced/forwarded HTTPS, not on a real TLS site |
| CSRF: SameSite + Origin check + double-submit token | A malicious site can't act as you | `test_state_changing_requests_need_the_csrf_token`, `test_cross_site_writes_are_refused` | ✅ tested |
| Authorization on every route | Anonymous requests get 401 | `test_every_api_route_rejects_anonymous_requests` (all 39 method/route pairs + media) | ✅ tested |
| User isolation (items, outfits, preferences, photos, exports, wipe) | One tester can't see/change another's data | `test_users_cannot_see_or_touch_each_others_data` (+ **mutation check**: deliberately breaking isolation made it fail), `test_media_path_traversal_is_blocked` | ✅ tested |
| Password recovery: hashed single-use 30-min tokens, newest only, generic responses, sessions revoked | Safe account recovery without revealing accounts | `test_recovery_flow_…`, `test_reset_tokens_expire…`, `test_admin_cli_can_issue_a_reset_link_without_email` | ✅ logic tested; **real email delivery untested** (no mail provider) |
| Account deletion (password-confirmed; removes DB, photos, sessions) | Right to erasure | `test_account_deletion_removes_everything…` + browser test | ✅ tested (backups, if any, are outside this) |
| Upload safety: decode-verified images only, size caps, decompression-bomb limit, re-encode, **EXIF/GPS stripped**, random file names, per-user quota and rate limit | Blocks disguised files, leaks of location data, abuse | `test_upload_validation…`, `test_oversized_upload…`, `test_photo_quota_per_user`, `test_uploaded_photos_lose_exif_and_gps` | ✅ tested |
| Security headers (strict CSP with `script-src 'self'`, nosniff, frame deny, no-referrer, CORP, HSTS on HTTPS) | Limits XSS, clickjacking, leakage | `test_security_headers`, `test_https_requests_get_secure_cookies_and_hsts` + browser CSP check | ✅ tested |
| Host allow-list | Stops DNS-rebinding | `test_dns_rebinding_host_is_rejected` (+ mutation check) | ✅ tested |
| Error/log hygiene: generic 500s, passwords never logged, docs hidden unless `OFTLY_DEBUG` | No secret/stack leakage | `test_unhandled_errors_do_not_leak_details`, `test_passwords_never_appear_in_logs`, `test_docs_are_disabled_in_production` | ✅ tested |
| Dependency check | Known-vulnerable libraries | `pip-audit -r requirements.txt` → **no known vulnerabilities** (run once at build; re-run before launch) | ✅ run once |
| Private beta invite codes | Strangers can't register on a public URL | `test_private_beta_invite_code` | ✅ tested |
| Data minimisation / external services | Names, photos, notes never leave | Weather sends only a place name and is **off** by default; intelligence provider **disabled** by default and loopback-only, ranking requests carry no names/notes/photos (`test_provider_nudges_…`) | ✅ tested |
| XSS handling in the UI | User text can't run scripts | browser test `user-entered HTML is shown as text` | ✅ tested |

## 3. What is NOT done / residual risks (be honest with testers)
1. **No independent security assessment or penetration test.** Required before public launch.
2. **HTTPS is not provided by the app.** It depends on your tunnel/reverse proxy. Misconfiguration (e.g. exposing plain HTTP) removes cookie/transport protection. Verified only with simulated forwarded-HTTPS headers, not against a real certificate.
3. **No email verification of addresses**, no MFA, no passkeys. Anyone with an invite can register any email (they can't read its mail, but could squat it). Needed before public launch.
4. **Password-reset email delivery is untested** against a real provider. Without `OFTLY_MAIL=smtp`, recovery is manual via `python -m app.admin reset-link EMAIL`.
5. **Rate limiter is in memory** (single process). A restart clears IP/email windows (account lockout persists). Multiple server instances would each count separately: needs Redis or a gateway limiter before scaling.
6. **Registration reveals whether an email exists** (HTTP 409). Accepted trade-off for beta; mitigated by rate limits and invites.
7. **CSP allows inline styles** (`style-src 'unsafe-inline'`) because the UI uses style attributes. Scripts are strict.
8. **Per-account SQLite files** suit tens of users, not thousands; no automatic backups, no encryption at rest beyond disk encryption (FileVault/volume encryption). Deleted accounts may persist in any backups you make.
9. **Audit log stores IP addresses** with no retention job yet. Decide and document retention.
10. **Bearer-token path (for a future native app) is tested at API level only.** No native app exists.
11. **Privacy policy and Terms are drafts** with no legal entity or contact. Not legal advice; needs legal review.
12. Not tested: load/performance, long-running soak, malicious multi-part fuzzing beyond the tests above, screen readers, real iPhone hardware.

## 4. How to verify before launch (you can do all of this)
```bash
python -m pytest -q                                   # backend + security tests
pip install pip-audit && pip-audit -r requirements.txt   # dependency vulnerabilities (re-run on launch day)
curl -sI https://YOUR-URL/ | egrep -i "content-security|strict-transport|x-frame|nosniff"   # headers over real HTTPS
curl -s -o /dev/null -w "%{http_code}\n" https://YOUR-URL/api/items                          # expect 401 when signed out
curl -s -H "Host: evil.example" -o /dev/null -w "%{http_code}\n" https://YOUR-URL/api/health  # expect 400
```
Then: run **OWASP ZAP baseline scan** against your test URL (free); check TLS with SSL Labs on a real domain; try two accounts on two phones and confirm neither sees the other's items or photos; change a password and confirm the other device is signed out; hire an independent reviewer for a focused test of auth, isolation and uploads.

## 5. External services, credentials, hosting still required
- **HTTPS endpoint:** Cloudflare quick tunnel (free, temporary URL; `scripts/beta.sh`) for personal/friends testing, or a small server + domain + Caddy (`docker-compose.yml`, untested here).
- **Mail provider (SMTP)** for password-reset emails: your choice; store credentials in `.env` only.
- **Backups:** your policy (nothing automatic).
- **Legal:** privacy policy/terms review, legal entity, contact address, data-retention decisions.
- **Apple Developer Program** only if you later ship a native app/TestFlight (not needed for the web-app beta).
