# Onboarding and accessibility

## First-run flow (shown once per account, server-side flag `walkthrough_done`)
1. **Optional first step: "Make OFTLY comfortable for you".** Placed first on purpose, so someone who needs larger text or higher contrast can set it before reading the rest. Buttons: *Set up accessibility* (opens the panel) or *Skip this step*.
2. **Step 1 of 3 – Build your wardrobe.** 3. **Step 2 of 3 – Discover your style.** 4. **Step 3 of 3 – Plan what to wear** (mentions destination weather, optional and off by default).
Controls: **Next**, **Back**, **Skip walkthrough** (steps before the last), **Finish** or **Add my first item** (last step). Arrow keys also move between steps; the heading takes focus on every step; progress is announced via the step label.
Finishing or skipping saves the flag, so it never appears automatically again. **Settings → Account → Replay walkthrough** shows it any time (it does not change the flag).

## Accessibility panel
Not permanently on screen. Open it from: onboarding step 0, **Settings → Accessibility → Open accessibility settings**, the **sign-in / register / reset** pages ("Accessibility options" link), or keyboard **Alt + A**. Choices apply instantly and are stored **on the device** (so they work before sign-in) and survive reloads.
- **Presets** (combinable, grouped, collapsed by default except the first): low vision, cataracts, presbyopia, AMD, visual fatigue, protan / deutan / tritan / achromatopsia, dyslexia, simple & calm, photosensitivity, tremor, Parkinson's, osteoarthritis, night comfort, bright light. Optional temporary mode (1 hour / 1 day / 1 week) that reverts automatically.
- **Fine-tune:** theme (system / light / dark / warm night), contrast (3 levels), text size 100–175 %, dim screen, colour support, typeface (highly legible), line / letter / word spacing, line length, bold, underlined links, animation (reduced / off), tap size, focus outline, steady taps, no dragging, simple view.
- Presets are convenience starting points, **not medical advice** and not clinically validated; the colour-vision presets change interface colours and add colour names but were not validated with a CVD simulator.

## What was tested (automated, desktop Chrome)
Dark, warm night, high and maximum contrast, legible font at 150 % text: axe-core WCAG A/AA audits on Today, Wardrobe, Settings, Help and the walkthrough; keyboard (skip link first Tab stop, Alt+A, Esc); presets' computed styles; reduced-motion; 44 px / 66 px targets; no horizontal overflow at 320–1440 px; persistence and temporary-preset expiry. **Not tested:** VoiceOver/TalkBack, real iPhone Larger-Text/Dynamic Type, people with the target conditions.
