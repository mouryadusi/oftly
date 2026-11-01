/* OFTLY sign-in, registration, password recovery, first-run walkthrough and account actions.
   Loaded before app.js; uses app.js globals (main, $, esc, api, guard, toast, route, PREFS, CATS, GEN) at call time. */
let SESSION = null, CFG = { demo_enabled: false, invite_required: false, recovery_available: false };
const PUBLIC_PAGES = ["login", "register", "forgot", "reset", "help", "privacy", "terms", "community", "app"];
const csrfToken = () => (document.cookie.match(/(?:^|; )oftly_csrf=([^;]+)/) || [])[1] || "";

const authShell = (title, lead, inner) => `<section class="auth"><span class="eyebrow">OFTLY · Your Wardrobe. Reimagined.</span><h1 class="display">${title}</h1>${lead ? `<p class="hero-sub">${lead}</p>` : ""}${inner}
  <p class="auth-a11y"><button class="link" type="button" data-a11y-open>Accessibility options</button></p></section>`;
const pwField = (id, label, ac, hint = "") => `<label>${label}<span class="pw"><input id="${id}" name="${id}" type="password" autocomplete="${ac}" required maxlength="256" ${hint ? `aria-describedby="${id}-h"` : ""}>
  <button type="button" class="btn sm ghost" data-show="${id}" aria-pressed="false">Show</button></span>${hint ? `<small id="${id}-h">${hint}</small>` : ""}</label>`;
const NOTICE = { signedout: "You’re signed out.", reset: "Password updated. Please sign in.", deleted: "Your account and all its data were deleted.", expired: "Your session ended. Please sign in again." };
const notice = qs => (qs && NOTICE[qs.msg]) ? `<p class="notice" role="status">${NOTICE[qs.msg]}</p>` : "";

function wireAuth(form, fn) {
  main.querySelectorAll("[data-show]").forEach(b => b.onclick = () => { const i = $("#" + b.dataset.show), show = i.type === "password"; i.type = show ? "text" : "password"; b.textContent = show ? "Hide" : "Show"; b.setAttribute("aria-pressed", show); });
  main.querySelector("[data-a11y-open]").onclick = () => OFTLYA11y.open();
  form.onsubmit = async e => {
    e.preventDefault(); const err = $("#auth-err"), btn = form.querySelector("[type=submit]"); err.textContent = ""; btn.disabled = true;
    try { await fn(Object.fromEntries(new FormData(form))); } catch (x) { err.textContent = x.message; err.focus(); } finally { btn.disabled = false; }
  };
}
async function enterApp() {
  CATS = await api("/categories"); PREFS = await api("/preferences"); GEN = { list: [], seen: [], occ: "", dest: "", day: 0, msg: "", weather: null };
  document.body.dataset.auth = "in"; const t = PREFS.walkthrough_done ? "#/" : "#/start";
  if (location.hash === t || (t === "#/" && !location.hash)) route(); else location.hash = t;
}

async function pageLogin(_, qs) {
  main.innerHTML = authShell("Welcome <em>back.</em>", "Sign in to your wardrobe.", `${notice(qs)}<form class="auth-form" id="lf" novalidate>
    <label>Email<input name="email" type="email" autocomplete="username" inputmode="email" required maxlength="254"></label>${pwField("password", "Password", "current-password")}
    <p id="auth-err" class="err" role="alert" tabindex="-1"></p><button class="btn primary" type="submit">Sign in</button></form>
    <p class="auth-links"><a href="#/forgot">Forgot your password?</a><span>New here? <a href="#/register">Create an account</a></span></p>`);
  wireAuth($("#lf"), async v => { SESSION = await api("/auth/login", { method: "POST", body: { email: v.email, password: v.password } }); await enterApp(); });
}
async function pageRegister() {
  main.innerHTML = authShell("Create your <em>wardrobe.</em>", "Your clothes and photos stay private to your account.", `<form class="auth-form" id="rf" novalidate>
    <label>Your name <small>(optional, used to greet you)</small><input name="display_name" autocomplete="given-name" maxlength="60"></label>
    <label>Email<input name="email" type="email" autocomplete="username" inputmode="email" required maxlength="254"></label>
    ${pwField("password", "Password", "new-password", "At least 12 characters. A few random words make a strong, memorable password.")}
    ${CFG.invite_required ? `<label>Invite code <small>(private beta)</small><input name="invite" autocomplete="off" required maxlength="100"></label>` : ""}
    <label class="chip consent"><input type="checkbox" name="agree" required> <span>I’ve read the <a href="#/privacy" target="_blank" rel="noopener">Privacy policy</a> and <a href="#/terms" target="_blank" rel="noopener">Terms</a>.</span></label>
    <p id="auth-err" class="err" role="alert" tabindex="-1"></p><button class="btn primary" type="submit">Create account</button></form>
    <p class="auth-links"><span>Already have an account? <a href="#/login">Sign in</a></span></p>`);
  wireAuth($("#rf"), async v => {
    if (!v.agree) throw new Error("Please confirm you’ve read the Privacy policy and Terms.");
    SESSION = await api("/auth/register", { method: "POST", body: { email: v.email, password: v.password, display_name: v.display_name || "", invite: v.invite || "" } }); await enterApp();
  });
}
async function pageForgot() {
  main.innerHTML = authShell("Reset your <em>password.</em>", "Enter your email and we’ll send a link that works for 30 minutes.", `${CFG.recovery_available ? "" : `<p class="notice" role="note">Email delivery isn’t set up on this test server yet, so reset links can’t be emailed. Ask the person running your test to generate a link for you.</p>`}
    <form class="auth-form" id="ff" novalidate><label>Email<input name="email" type="email" autocomplete="username" inputmode="email" required maxlength="254"></label>
    <p id="auth-err" class="err" role="alert" tabindex="-1"></p><p id="ok" class="notice" role="status" hidden></p><button class="btn primary" type="submit">Send reset link</button></form>
    <p class="auth-links"><a href="#/login">Back to sign in</a></p>`);
  wireAuth($("#ff"), async v => { const r = await api("/auth/forgot", { method: "POST", body: { email: v.email } }); $("#ok").hidden = false; $("#ok").textContent = r.detail; });
}
async function pageReset(_, qs) {
  const token = (qs && qs.token) || "";
  main.innerHTML = authShell("Choose a new <em>password.</em>", token ? "" : "This link is missing its token. Request a new reset link.", token ? `<form class="auth-form" id="sf" novalidate>
    ${pwField("password", "New password", "new-password", "At least 12 characters.")}<p id="auth-err" class="err" role="alert" tabindex="-1"></p><button class="btn primary" type="submit">Save new password</button></form>` : `<a class="btn" href="#/forgot">Request a new link</a>`);
  if (token) wireAuth($("#sf"), async v => { await api("/auth/reset", { method: "POST", body: { token, password: v.password } }); location.hash = "#/login?msg=reset"; });
}

/* ---------- first-run walkthrough: optional accessibility step, then three steps ---------- */
const ILLU = {
  build: `<svg viewBox="0 0 120 120" aria-hidden="true"><path d="M60 22a9 9 0 1 1 9 9c-5 1-9 4-9 9v6M12 92l48-40 48 40z" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/><rect x="30" y="94" width="60" height="8" rx="4" fill="currentColor" opacity=".25"/></svg>`,
  style: `<svg viewBox="0 0 120 120" aria-hidden="true"><path d="M40 28l-24 20 14 12 10-8v48h40V52l10 8 14-12-24-20c-4 8-12 12-20 12s-16-4-20-12z" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/><path d="M96 16l3 7 7 3-7 3-3 7-3-7-7-3 7-3z" fill="currentColor"/></svg>`,
  plan: `<svg viewBox="0 0 120 120" aria-hidden="true"><rect x="16" y="26" width="88" height="78" rx="12" fill="none" stroke="currentColor" stroke-width="4"/><path d="M16 50h88M40 16v18M80 16v18" stroke="currentColor" stroke-width="4" stroke-linecap="round"/><circle cx="46" cy="78" r="9" fill="currentColor"/><path d="M64 84a10 10 0 0 1 4-19 14 14 0 0 1 26 4 8 8 0 0 1 0 15z" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linejoin="round"/></svg>`,
  a11y: `<svg viewBox="0 0 120 120" aria-hidden="true"><circle cx="60" cy="24" r="9" fill="currentColor"/><path d="M24 44l36 8 36-8M60 52v26m0 0l-16 30m16-30l16 30" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
};
const WALK = [
  { id: "a11y", k: "Optional first step", t: "Make OFTLY <em>comfortable</em> for you", p: "Choose text size, contrast, night mode, colour-vision support, reduced motion and easier tapping. Everything is optional, applies straight away, and you can change it any time in Settings." },
  { id: "build", k: "Step 1 of 3", t: "Build your <em>wardrobe</em>", p: "Add and organise the clothes you own in a personal digital wardrobe. Take a photo or upload one, then note its colour, style and the occasions it suits." },
  { id: "style", k: "Step 2 of 3", t: "Discover your <em>style</em>", p: "Explore outfit combinations made only from your own clothes. Each suggestion is explained piece by piece, and you can swap any item, save looks and tell OFTLY what you like." },
  { id: "plan", k: "Step 3 of 3", t: "Plan what to <em>wear</em>", p: "Pick an occasion and, if you switch on weather, a destination and day. OFTLY styles for the forecast and helps you plan your week. Weather is optional and off until you turn it on." },
];
async function pageStart(_, qs) {
  const replay = !!(qs && qs.replay); let n = 0;
  const finish = async dest => { if (!replay) { PREFS = await api("/preferences", { method: "PUT", body: { walkthrough_done: true, onboarded: true } }); } location.hash = dest || (replay ? "#/settings" : "#/"); };
  const draw = () => {
    const s = WALK[n], last = n === WALK.length - 1;
    main.innerHTML = `<section class="start" aria-labelledby="st-h"><div class="start-art">${ILLU[s.id]}</div><span class="eyebrow">${s.k}</span><h1 class="display" id="st-h" tabindex="-1">${s.t}</h1><p class="hero-sub">${s.p}</p>
      <ol class="dots" aria-label="Progress">${WALK.map((w, i) => `<li ${i === n ? 'aria-current="step"' : ""} class="${i <= n ? "on" : ""}"><span class="sr">${w.k}</span></li>`).join("")}</ol>
      <div class="row start-actions">${n ? `<button class="btn" id="back">Back</button>` : ""}
        ${s.id === "a11y" ? `<button class="btn primary" id="seta11y">Set up accessibility</button><button class="btn" id="next">Skip this step</button>` : last ? `<button class="btn primary" id="done-add">Add my first item</button><button class="btn" id="done">Finish</button>` : `<button class="btn primary" id="next">Next</button>`}
        ${last ? "" : `<button class="link" id="skipall">Skip walkthrough</button>`}</div></section>`;
    $("#st-h").focus({ preventScroll: true });
    $("#back")?.addEventListener("click", () => { n--; draw(); });
    $("#next")?.addEventListener("click", () => { n++; draw(); });
    $("#seta11y")?.addEventListener("click", () => OFTLYA11y.open());
    $("#skipall")?.addEventListener("click", guard(() => finish()));
    $("#done")?.addEventListener("click", guard(() => finish()));
    $("#done-add")?.addEventListener("click", guard(() => finish("#/add")));
  };
  draw();
  main.onkeydown = e => { if (e.target.closest("input,select,textarea,dialog")) return; if (e.key === "ArrowRight" && n < WALK.length - 1) { n++; draw(); } else if (e.key === "ArrowLeft" && n) { n--; draw(); } };
}

/* ---------- account actions (Settings) ---------- */
function askDialog(title, fields, cta, danger, action, intro = "") {
  const d = $("#dlg");
  d.innerHTML = `<form class="f" id="askf"><h2 class="wide">${title}</h2>${intro ? `<p class="wide muted">${intro}</p>` : ""}${fields.map(f => `<label class="wide">${f.label}<input name="${f.name}" type="password" autocomplete="${f.ac}" required maxlength="256"></label>`).join("")}
    <p id="ask-err" class="err wide" role="alert"></p><div class="row wide"><button class="btn ${danger ? "danger" : "primary"}" type="submit">${cta}</button><button class="btn" type="button" id="ask-x">Cancel</button></div></form>`;
  d.showModal(); d.querySelector("input").focus();
  $("#ask-x").onclick = () => d.close();
  $("#askf").onsubmit = async e => { e.preventDefault(); const b = e.submitter; b.disabled = true; $("#ask-err").textContent = "";
    try { await action(Object.fromEntries(new FormData(e.target))); d.close(); } catch (x) { $("#ask-err").textContent = x.message; } finally { b.disabled = false; } };
}
const accountSection = () => `<h2>Account</h2><p class="muted">Signed in as <b>${esc(SESSION.email)}</b></p>
  <div class="row"><button class="btn" id="signout">Sign out</button><button class="btn" id="signoutall">Sign out of all devices</button><button class="btn" id="chpw">Change password</button><button class="btn" id="walk">Replay walkthrough</button><button class="btn danger" id="delacct">Delete account…</button></div>
  <p class="muted"><small>Deleting your account permanently removes your wardrobe, outfits, photos and preferences from the OFTLY server. Export first if you want a copy.</small></p>`;
function wireAccount() {
  const out = async (path, msg) => { await api(path, { method: "POST" }); SESSION = null; PREFS = {}; document.body.dataset.auth = "out"; location.hash = "#/login?msg=" + msg; };
  $("#signout").onclick = guard(() => out("/auth/logout", "signedout"));
  $("#signoutall").onclick = guard(() => out("/auth/logout-all", "signedout"));
  $("#walk").onclick = () => { location.hash = "#/start?replay=1"; };
  $("#chpw").onclick = () => askDialog("Change password", [{ name: "current", label: "Current password", ac: "current-password" }, { name: "new", label: "New password (12+ characters)", ac: "new-password" }], "Change password", false,
    async v => { await api("/auth/password", { method: "POST", body: v }); toast("Password changed. Other devices were signed out."); });
  $("#delacct").onclick = () => askDialog("Delete your account?", [{ name: "password", label: "Enter your password to confirm", ac: "current-password" }], "Delete everything", true,
    async v => { await api("/auth/account", { method: "DELETE", body: v }); SESSION = null; PREFS = {}; document.body.dataset.auth = "out"; location.hash = "#/login?msg=deleted"; },
    "This permanently deletes your wardrobe, outfits, photos and preferences. It can’t be undone.");
}
const AUTH_PAGES = { login: pageLogin, register: pageRegister, forgot: pageForgot, reset: pageReset, start: pageStart, welcome: pageStart };
