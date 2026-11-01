# Friends-and-family beta plan

**Distribution method:** private HTTPS web app + invite codes (no TestFlight needed). Reason: it works on every iPhone immediately, costs nothing, and updates instantly when you restart the server.

## Costs and limits
- **Web beta:** free (Cloudflare quick tunnel or any small host). Your Mac must stay on for Option A; temporary URL changes per run.
- **TestFlight (only if you build a native app later):** requires the Apple Developer Program (about US$99/year, verify current price), a native build (none exists), up to 10,000 external testers, builds expire after 90 days, first external build goes through Apple beta review. Not required now.

## Inviting testers
1. Run `./scripts/beta.sh` (or set `OFTLY_INVITE_CODES` on your server). Share the **link** and **invite code** privately (message, not social media). Rotate the code after the beta (`python -m app.admin new-invite`).
2. Each tester registers their own account → their wardrobe, photos and preferences are **separate and unreachable by other testers** (separate database and photo folder per account; verified by automated tests, including a deliberate-breakage check).
3. See who joined: `cd backend && ../.venv/bin/python -m app.admin list-users`. Help someone locked out: `reset-link EMAIL`. Remove someone: `delete-user EMAIL`.
4. **Test vs production separation:** beta data lives in `data-beta/` (or your server volume). Automated tests use throwaway temp folders and a fixture account (`seeded@example.com`, test-only). Never point tests at beta data.

## Updating the app for testers
Stop the server (Ctrl+C), replace the project folder with the new ZIP's contents (keep `data-beta/`), run `./scripts/beta.sh` again. With the quick tunnel the link changes: send the new link; testers re-add to Home Screen.

## Reproducing bugs
Ask for: iPhone model + iOS version, what they tapped, what they expected/saw, screenshot or screen recording, time, and whether the issue repeats after signing out/in. For you: `OFTLY_DEBUG=1` shows API docs; server errors are logged in the Terminal (no passwords are logged).

## Feedback template (copy into a form or message)
```
Tester: ____  iPhone model / iOS: ____  Date: ____
1. Sign-up & login (easy? any errors? password reset needed?): 1–5 ___ notes ___
2. Walkthrough & accessibility setup (clear? skippable? found it again in Settings?): 1–5
3. Adding clothes (camera / photo library / manual): 1–5   Problems: 
4. Outfit suggestions (useful? explanations clear? swap/save/wear): 1–5
5. Weather & destination (worked? any wrong or missing data?): 
6. Visual design (looks premium? anything ugly/cut off/unreadable?): 1–5
7. Accessibility (text size, contrast, night mode, reduced motion, tap size): what you used and what didn't work:
8. Speed (anything slow? how long to open? photos upload time?):
9. Privacy (did anything feel like too much data? did you understand what's stored/deleted?):
10. Bugs (steps → expected → actual → screenshot):
11. Would you use it weekly? What's missing?
```

## Device and screen checklist
| Device class | Example | Check |
|---|---|---|
| Small (320–375 pt) | iPhone SE (2nd/3rd gen), 12/13 mini | no horizontal scroll, buttons reachable, walkthrough fits |
| Standard (390–393 pt) | iPhone 12–16 | all pages, bottom nav above home bar |
| Large (428–440 pt) | Plus / Pro Max | layout not stretched, text readable |
| Older iOS | oldest iPhone/iOS you can borrow | page loads, forms work, fonts load |
| Accessibility | Larger Text on in iOS, Dark Mode, Reduce Motion, VoiceOver | app respects dark/reduced motion; try VoiceOver on sign-in + one outfit |
| Network | Wi-Fi, mobile data, airplane mode | graceful errors, recovery |
Automated browser checks covered widths 320/390/768/1024/1440 in desktop Chrome only.

## Rules for testers (put these in your invite message)
This is an early test: don't upload photos of other people or sensitive images; don't reuse an important password; report problems to the person who invited you; you can delete your account in Settings → Account at any time.
