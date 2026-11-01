# Status and readiness (defined checklists, not opinion)

Scoring: ✅ done and verified = 1 · ◐ done but only partly verified = 0.5 · ⬜ not done = 0. Percent = points ÷ items.

## Development: 28 / 33 = **85 %**
✅ Rename everywhere · palette kept · UI/layout sweep (fixes listed in TEST_RESULTS §3) · accessibility step in onboarding · accessibility off the home screen · reopenable in Settings · preferences persisted · 3-step walkthrough · Back/Skip/Next/Finish · shown once + replay · registration · login · logout · sessions · isolation · rate limits · CSRF · upload hardening · security headers · account deletion · demo removed from product · clean new-user state · beta distribution plan · feedback template · device checklist · launch checklist
◐ Brand mark (reworked, placeholder-grade) · password recovery (logic verified; real email not) · privacy policy (draft, no legal review) · iPhone route (PWA + tunnel script written, never run)
⬜ Email verification · MFA/passkeys · native iOS app (not chosen for this stage)

## Testing: 9.5 / 19 = **50 %**
✅ backend suite · auth + isolation suite · branding guard · browser functional suite · automated accessibility audits · layout widths · offline/error states · mutation checks · dependency scan
◐ browser suite ran in chunks, not one continuous pass
⬜ real iPhone · Safari/WebKit · VoiceOver · load/soak · independent pen test · real email · real HTTPS · tunnel script · user testing · long-run reliability

## Security readiness for **public launch**: 8.5 / 20 = **43 %**
✅ hashing · sessions · CSRF · isolation · upload safety · headers · error/log hygiene
◐ rate limiting (in-memory) · dependency scanning (once) · secrets handling (env only)
⬜ real HTTPS in production · email verification · real reset email · MFA · independent assessment · backups · retention policy · legal privacy · monitoring · shared rate-limit store · audit-log retention
*For a small invite-only friends beta over HTTPS the verified controls are appropriate; for public launch they are not sufficient.*

## Launch readiness: 6 / 20 = **30 %**
✅ auth · isolation · deletion · accessibility · clean data · headers · ⬜ the 14 launch gates in `LAUNCH_CHECKLIST.md`

## Overall (mean of the four): **52 %**

| Question | Answer |
|---|---|
| Ready for your personal iPhone test? | **Yes**, with one step I could not verify: run `scripts/beta.sh` (needs `brew install cloudflared`) |
| Ready for friends-and-family beta? | **Conditionally yes**: small, invite-only, after *you* complete the iPhone checklist; accept documented gaps (no email verification, manual password resets, in-memory limiter) |
| Ready for public launch? | **No** |
