# Launch checklist

Gates marked **BLOCKER** must be done before public launch. ✅ = done and verified in this build; ⬜ = not done.

## Security (see SECURITY_REPORT.md)
- ✅ Passwords hashed (Argon2id), sessions server-side + revocable, CSRF, rate limits, per-user isolation, upload hardening, headers, error hygiene, dependency scan (one run)
- ⬜ **BLOCKER** Independent security assessment / penetration test
- ⬜ **BLOCKER** Real HTTPS deployment on your domain, checked with SSL Labs; HSTS confirmed
- ⬜ **BLOCKER** Email verification for new accounts; real password-reset email via a mail provider (SPF/DKIM set up)
- ⬜ MFA or passkeys (strongly recommended)
- ⬜ Shared rate-limit store (Redis) or gateway limits if running more than one server process
- ⬜ Automated dependency/vulnerability scanning in CI; patch process
## Privacy & legal
- ⬜ **BLOCKER** Lawyer-reviewed Privacy Policy and Terms naming the legal entity, contact address, data retention (audit-log IPs, backups) and deletion timelines
- ✅ In-app account deletion and data export exist
- ⬜ Cookie/consent review for your jurisdictions; data-processing terms with hosting and mail providers; children's-data decision (age gate)
- ⬜ If any AI/intelligence provider is enabled: document exact data sent, add explicit opt-in (currently none enabled)
## Deployment, monitoring, backups
- ⬜ Production host, domain, `.env` secrets management, non-root container, firewall
- ⬜ Monitoring and alerts (uptime, error rate, disk), log retention without personal data
- ⬜ Automated encrypted backups of `data/` and a tested restore; backup deletion policy matching account deletion
- ⬜ Capacity plan: per-account SQLite suits tens–hundreds of users; plan migration to a managed database before growth
## Product quality
- ✅ Core flows, accessibility audits, layout widths, offline/error states (desktop Chrome)
- ⬜ **BLOCKER** Real-device testing on several iPhones (you, via IPHONE_TESTING.md) and Android if supported
- ⬜ Screen-reader pass (VoiceOver); user testing with people who use the accessibility presets
- ⬜ Professional brand identity review (current O-ring mark is a placeholder-grade design)
## Apple / App Store (only if shipping a native app)
- ⬜ Apple Developer Program membership, bundle ID, signing, TestFlight
- ⬜ Native build (none exists; Capacitor wrap recommended first), privacy nutrition label, permission strings (camera, photos), in-app account deletion (present in the web app), support and privacy URLs, review demo account
