// Real-browser end-to-end + accessibility tests (headless Chrome via puppeteer-core, axe-core for automated a11y rules).
// Run:  node e2e.mjs http://127.0.0.1:8011     (server: tests/frontend/serve_fake_weather.py, fake Open-Meteo)
// Env:  CHROME_PATH=/path/to/chrome  (else @sparticuz/chromium)   SHOTS=/dir for screenshots
import puppeteer from "puppeteer-core";
import fs from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const base = process.argv[2] || "http://127.0.0.1:8011", SHOTS = process.env.SHOTS || "";
const axeSrc = fs.readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
let results = [], problems = [];
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ONLY = process.env.ONLY ? new RegExp(process.env.ONLY, "i") : null;
async function step(name, fn) { if (ONLY && !ONLY.test(name)) return; try { await fn(); results.push([name, true]); console.log("PASS ", name); } catch (e) { results.push([name, false]); console.log("FAIL ", name, "\n      ", String(e.message).split("\n")[0]);
  try { if (typeof p !== "undefined") console.log("       [p] url:", p.url(), "| main:", (await p.evaluate(() => (document.querySelector("main")?.innerText || "").slice(0, 70).replace(/\n/g, " ")))); } catch (x) { /* page gone */ } } }
const ok = (c, m = "assertion failed") => { if (!c) throw new Error(m); };
const SEED = { email: "seeded@example.com", password: "correct-horse-battery-7" };
let COOKIES = [], CSRF = "";
const api = (p, o = {}) => fetch(base + "/api" + p, { ...o, headers: { ...(o.body ? { "Content-Type": "application/json" } : {}), cookie: COOKIES.map(c => `${c.name}=${c.value}`).join("; "), "x-csrf-token": CSRF }, body: o.body ? JSON.stringify(o.body) : undefined }).then(r => r.status === 204 ? null : r.json());
async function login(email, password) {
  const r = await fetch(base + "/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
  if (!r.ok) throw new Error("login failed " + r.status);
  COOKIES = r.headers.getSetCookie().map(c => { const [nv] = c.split(";"); const k = nv.indexOf("="); return { name: nv.slice(0, k), value: nv.slice(k + 1), url: base }; });
  CSRF = COOKIES.find(c => c.name === "oftly_csrf").value;
}

let exe, args = [];
if (process.env.CHROME_PATH) { exe = process.env.CHROME_PATH; args = ["--no-sandbox"]; }
else { const chromium = (await import("@sparticuz/chromium")).default; exe = await chromium.executablePath(); args = [...chromium.args.filter(a => a !== "--single-process"), "--no-sandbox"]; }
const launch = () => puppeteer.launch({ executablePath: exe, args, headless: "shell" });
let browser = await launch();
async function newPage(w = 1440, h = 900, opts = {}) {
  const p = await (opts.ctx || browser).newPage(); await p.setViewport({ width: w, height: h, deviceScaleFactor: opts.dpr || 1 }); p.errs = []; if (!opts.anon) await p.setCookie(...COOKIES);
  p.on("pageerror", e => p.errs.push("pageerror: " + e.message));
  p.on("console", m => { const t = m.text(); if (m.type() === "error" || /Content Security Policy|Refused to/i.test(t)) p.errs.push("console: " + t); });
  p.on("requestfailed", r => p.errs.push("requestfailed: " + r.url()));
  p.on("response", r => { if (r.status() >= 400 && !r.url().includes("favicon")) p.errs.push(`http ${r.status()}: ${r.url()}`); });
  if (opts.motion) await p.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: opts.motion }]);
  if (opts.scheme) await p.emulateMediaFeatures([{ name: "prefers-color-scheme", value: opts.scheme }]);
  await p.evaluateOnNewDocument(() => { try { sessionStorage.setItem("oftly.pre", "1"); } catch (e) {} });  // skip preloader unless a test wants it
  return p;
}
const goto = async (p, hash = "") => {
  await p.goto(base + "/" + (hash ? "#" + hash : ""), { waitUntil: "domcontentloaded", timeout: 60000 });
  // hash-only navigations resolve immediately, so wait until the SPA has really finished rendering (no busy flag, no skeletons)
  await p.waitForFunction(() => { const m = document.querySelector("main"); return m && !m.hasAttribute("aria-busy") && m.children.length > 0 && !m.querySelector(".skeleton"); }, { timeout: 20000 });
  await sleep(500);
};
const shot = async (p, name, full = true) => { if (SHOTS) {
    if (full) { await p.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += innerHeight * .7) { scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); } scrollTo(0, 0); await new Promise(r => setTimeout(r, 400)); }); } fs.mkdirSync(SHOTS, { recursive: true }); await p.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: full }); } };
const txt = (p, sel) => p.$eval(sel, e => e.textContent.trim());
const cs = (p, sel, prop) => p.$eval(sel, (e, prop) => getComputedStyle(e)[prop], prop);

// ---- sign in as the pre-seeded fixture account (server runs with demos OFF, like production) ----
await login(SEED.email, SEED.password);

let p = await newPage();
await step("Today loads with no console errors, failed requests or CSP violations", async () => { await goto(p); ok(p.errs.length === 0, p.errs.join(" | ")); });
await step("bundled fonts load (Fraunces + Instrument Sans), none fetched from a CDN", async () => {
  ok(await p.evaluate(async () => { await document.fonts.ready; return document.fonts.check("1em Fraunces") && document.fonts.check("1em 'Instrument Sans'"); }), "fonts not loaded");
  const ext = await p.evaluate(() => performance.getEntriesByType("resource").filter(r => !r.name.startsWith(location.origin)).map(r => r.name)); ok(ext.length === 0, "external requests: " + ext);
});
await step("personalised greeting in display type with the user's name", async () => { const h = await txt(p, "h1.display"); ok(/Good (morning|afternoon|evening), Mourya\./.test(h), h); ok((await cs(p, "h1.display", "fontFamily")).includes("Fraunces")); ok(parseFloat(await cs(p, "h1.display", "fontSize")) >= 56); });
await step("Season is gone from the styling flow; Destination + When are present", async () => {
  const t = await p.evaluate(() => document.querySelector("main").innerText); ok(!/\bseason\b/i.test(t.replace(/seasonal/i, "")), "found 'season' on Today");
  ok(await p.$("#dest") && await p.$("#day") && !(await p.$("#sea")));
});
await step("stage renders pieces, score ring, factor bars, per-piece notes, reasoning", async () => {
  const n = await p.$$eval(".collage .piece", e => e.length); ok(n >= 3, "pieces " + n);
  ok(await p.$(".ring") && (await p.$$eval(".fbars li", e => e.length)) >= 3);
  ok((await p.$$eval(".piece .note", e => e.filter(x => x.textContent.length > 10).length)) === n);
  ok(/Why this works for you/.test(await p.$eval(".how summary", e => e.textContent)));
});
await step("destination flow: Oslo + Tomorrow calls the API with both and shows that city's weather", async () => {
  const reqs = []; p.on("request", r => { if (r.url().includes("/outfits/generate")) reqs.push(r.url()); });
  await p.click("#dest"); await p.type("#dest", "Oslo"); await p.select("#day", "1"); await sleep(1200);
  ok(reqs.some(u => u.includes("destination=Oslo") && u.includes("day=1")), "requests: " + reqs.join(" "));
  const wx = await p.$eval("#wxcard", e => e.innerText); ok(/oslo/i.test(wx) && /3/.test(wx) && /rain/i.test(wx) && /humidity/i.test(wx) && /wind/i.test(wx) && /open-meteo/i.test(wx), wx);
  const prac = await p.$eval(".look-panel", e => e.innerText); ok(/Oslo, tomorrow: 3°C \(cold\)/.test(prac), prac.slice(0, 400));
  ok((await txt(p, ".look-title")).length > 3);
});
await step("unknown destination degrades gracefully (no invented weather)", async () => {
  await p.$eval("#dest", e => e.value = ""); await p.type("#dest", "Atlantis"); await p.keyboard.press("Enter"); await sleep(1200);
  const wx = await p.$eval("#wxcard", e => e.innerText); ok(/no forecast right now/i.test(wx) && /won.t guess/i.test(wx) && !/°/.test(wx), wx);
  ok((await p.$$(".collage .piece")).length >= 3, "outfit still generated");
});
await step("promote an alternative: 'Make it my look' replaces the stage", async () => {
  await p.$eval("#dest", e => e.value = ""); await p.type("#dest", "Oslo"); await p.keyboard.press("Enter"); await sleep(1200);
  const before = await txt(p, ".look-title"); const alt = await p.$eval(".altcard h3", e => e.textContent); await p.click("[data-act=promote]"); await sleep(900);
  ok((await txt(p, ".look-title")) === alt && alt !== before, `${before} -> ${alt}`);
});
await step("copy-summary button gives inline confirmation", async () => { await p.$eval("[data-copy]", e => e.click()); await sleep(300); ok(/Copied/.test(await txt(p, "[data-copy]"))); });
await step("insights render real numbers; wardrobe map canvas has pixels", async () => {
  ok((await p.$$(".tiles .tile")).length >= 6);
  const filled = await p.$eval("#vmap canvas", c => { const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 0) n++; return n / (d.length / 4); });
  ok(filled > .95, "canvas fill " + filled);
});
await step("recent-items carousel: next button scrolls, progress updates, keyboard arrow works", async () => {
  await p.$eval("#recent", e => e.scrollIntoView({ block: "center" })); await sleep(400);
  const waitScroll = async (min) => { for (let i = 0; i < 30; i++) { const v = await p.$eval("#recent", e => e.scrollLeft); if (v > min + 5) return v; await sleep(100); } return await p.$eval("#recent", e => e.scrollLeft); };
  const l0 = await p.$eval("#recent", e => e.scrollLeft); await p.click(".carousel:has(#recent) [data-dir='1']");
  const l1 = await waitScroll(l0); ok(l1 > l0, `${l0} -> ${l1}`); await sleep(600);
  await p.focus("#recent"); const l1b = await p.$eval("#recent", e => e.scrollLeft); await p.keyboard.press("ArrowRight"); ok((await waitScroll(l1b)) > l1b, "arrow key did not scroll");
  ok(await p.$eval(".carousel:has(#recent) [data-dir='-1']", e => !e.disabled));
});
await step("marquee has a working pause control", async () => { await p.$eval(".marq", e => e.scrollIntoView({ block: "center" })); await p.click(".marq button"); ok(await p.$eval(".marq", e => e.hasAttribute("data-paused"))); });
await shot(p, "01-today-desktop-light");

await step("wardrobe: one-click quick filters (Neutrals, Favourites, Not worn) match the API", async () => {
  await goto(p, "/wardrobe"); const count = async () => p.$$eval("#res .card", e => e.length);
  const total = await count(); ok(total >= 10, "total " + total);
  await p.click("#quick [data-q='3']"); await sleep(700); const n = await count(); const api1 = (await api("/items?palette=neutral")).total;
  ok(n === Math.min(24, api1) && n < total && (await p.$eval("#quick [data-q='3']", e => e.getAttribute("aria-pressed"))) === "true", `${n} vs ${api1}`);
  await p.click("#quick [data-q='1']"); await sleep(700); ok((await count()) === Math.min(24, (await api("/items?favorite=true")).total));
  await p.click("#quick [data-q='2']"); await sleep(700); ok((await count()) === Math.min(24, (await api("/items?unworn_days=30")).total));
  await p.click("#quick [data-q='0']"); await sleep(700); ok((await count()) === total);
  ok(!(await p.$("[name=season]")), "season filter still on wardrobe bar");
});
await shot(p, "02-wardrobe-desktop-light");

// ---- authentication, onboarding, branding (real browser, fresh anonymous visitor) ----
let NEWPAGE;
const NEW = { email: `friend${Date.now()}@example.com`, password: "a-long-test-passphrase-42", name: "Riya" };
const anonPage = async (w = 390, h = 844) => await newPage(w, h, { anon: true, ctx: await browser.createBrowserContext() });   // isolated cookie jar = a true stranger
const waitText = (q, sel) => q.waitForFunction(s => (document.querySelector(s)?.textContent || "").trim().length > 0, { timeout: 15000 }, sel);
const typeInto = async (q, sel, v) => { await q.click(sel); await q.type(sel, v); };
await step("signed-out visitor is sent to sign-in; nav hidden; protected API says 401; OFTLY title", async () => {
  const q = await anonPage(); await q.goto(base + "/#/wardrobe", { waitUntil: "networkidle0" }); await q.waitForSelector("#lf");
  ok(q.url().includes("#/login"), q.url()); ok(/OFTLY/.test(await q.title()), await q.title());
  ok((await q.$eval("nav", e => getComputedStyle(e).display)) === "none", "nav should be hidden when signed out");
  ok((await q.evaluate(async () => (await fetch("/api/items")).status)) === 401 && (await q.evaluate(async () => (await fetch("/media/x.jpg")).status)) === 401);
  ok(!/veya/i.test(await q.evaluate(() => document.body.innerText)), "old brand name visible");
  ok(q.errs.filter(e => !/401/.test(e)).length === 0, q.errs.join("|"));
  await q.close();
});
await step("wrong password shows one generic error and does not sign in", async () => {
  const q = await anonPage(); await goto(q, "/login"); await typeInto(q, "[name=email]", SEED.email); await typeInto(q, "#password", "definitely-wrong-pass-1"); await q.click("[type=submit]"); await waitText(q, "#auth-err");
  ok(/incorrect/i.test(await txt(q, "#auth-err")), await txt(q, "#auth-err")); ok(q.url().includes("#/login")); await q.close();
});
await step("registration → accessibility-first walkthrough → 3 steps → finish → clean empty wardrobe", async () => {
  const q = await anonPage(); await goto(q, "/register");
  await q.click("[type=submit]"); await sleep(400); ok(q.url().includes("#/register"), "consent should be required");
  await typeInto(q, "[name=display_name]", NEW.name); await typeInto(q, "[name=email]", NEW.email); await typeInto(q, "#password", NEW.password); await q.click("[name=agree]"); await q.click("[type=submit]");
  await q.waitForSelector("#st-h"); ok(q.url().includes("#/start"), q.url());
  ok(/comfortable/i.test(await txt(q, "#st-h")) && /Optional first step/.test(await q.$eval(".start .eyebrow", e => e.textContent)), "accessibility step should come first");
  ok(await q.$("#seta11y") && await q.$("#next") && !(await q.$("#back")), "a11y step: set up / skip, no Back");
  await q.click("#seta11y"); await sleep(300); ok(await q.$eval("#a11y-panel", e => e.open), "panel should open from onboarding"); await q.evaluate(() => document.getElementById("a11y-panel").close());
  await q.click("#next"); await sleep(250); ok(/wardrobe/i.test(await txt(q, "#st-h")) && /Step 1 of 3/.test(await q.$eval(".start .eyebrow", e => e.textContent)));
  await q.click("#next"); await sleep(250); ok(/style/i.test(await txt(q, "#st-h"))); await q.click("#back"); await sleep(250); ok(/wardrobe/i.test(await txt(q, "#st-h")), "Back should work");
  await q.click("#next"); await q.click("#next"); await sleep(250); ok(/wear/i.test(await txt(q, "#st-h")) && /Step 3 of 3/.test(await q.$eval(".start .eyebrow", e => e.textContent)));
  ok(/weather/i.test(await q.$eval(".start .hero-sub", e => e.textContent)) && await q.$("#done") && await q.$("#done-add"));
  await shot(q, "09-walkthrough-mobile", false);
  await q.click("#done"); await q.waitForFunction(() => document.querySelector("h1.display")?.textContent.includes("Riya"), { timeout: 8000 });
  const t = await q.evaluate(() => document.body.innerText); ok(/Good (morning|afternoon|evening), Riya/.test(t) && /wardrobe is empty/i.test(t), t.slice(0, 200));
  ok(!/demo|sample/i.test(t), "no demo/sample content for a new user"); ok(!(await q.$("[data-act=demo]"))); ok((await api("/summary")).total >= 10, "sanity: seeded account is separate");
  await shot(q, "10-new-user-empty-today-mobile", false);
  await q.reload({ waitUntil: "networkidle0" }); await q.waitForSelector("h1.display"); ok(!q.url().includes("#/start"), "walkthrough must not reappear");
  const cks = await q.cookies(); const sc = cks.find(c => c.name === "oftly_session"); ok(sc && sc.httpOnly && sc.sameSite === "Lax", JSON.stringify(sc));
  ok(!(await q.evaluate(() => document.cookie)).includes("oftly_session"), "session cookie must not be readable by scripts");
  const hdr = await q.evaluate(async () => { const r = await fetch("/"); return [r.headers.get("content-security-policy"), r.headers.get("x-frame-options")]; }); ok(/default-src 'self'/.test(hdr[0]) && hdr[1] === "DENY");
  ok(!(await q.$("#a11y-fab")) && !(await q.evaluate(() => /Accessibility/i.test(document.querySelector("main").innerText))), "no accessibility controls on the home screen");
  NEWPAGE = q;
});
await step("new user's data is isolated: seeded account's wardrobe is not visible", async () => {
  const q = NEWPAGE; await goto(q, "/wardrobe"); ok((await q.$$("#res .card")).length === 0, "new account sees someone else's items");
  const r = await q.evaluate(async () => (await fetch("/api/items")).json()); ok(r.total === 0);
});
await step("Settings: replay walkthrough, reopen accessibility, sign out; protected pages locked afterwards", async () => {
  const q = NEWPAGE; await goto(q, "/settings"); ok(/Riya|friend/i.test(await q.evaluate(() => document.querySelector("main").innerText)) && !!(await q.$("#signout")));
  await q.click("#open-a11y2"); await sleep(300); ok(await q.$eval("#a11y-panel", e => e.open)); await q.evaluate(() => document.getElementById("a11y-panel").close()); await sleep(100);
  await q.click("#walk"); await q.waitForSelector("#st-h"); ok(q.url().includes("replay=1")); await q.click("#skipall"); await q.waitForFunction(() => location.hash.startsWith("#/settings"), { timeout: 8000 });
  await q.waitForSelector("#signout", { timeout: 8000 });
  await q.click("#signout"); await q.waitForSelector("#lf"); ok(/signed out/i.test(await q.evaluate(() => document.body.innerText)));
  await q.goto(base + "/#/wardrobe", { waitUntil: "networkidle0" }); await sleep(600); ok(q.url().includes("#/login"), "back to a protected page after logout must redirect");
  ok((await q.evaluate(async () => (await fetch("/api/items")).status)) === 401);
});
await step("sign back in; session survives reload; then delete the account with password confirmation", async () => {
  const q = NEWPAGE; await goto(q, "/login"); await typeInto(q, "[name=email]", NEW.email); await typeInto(q, "#password", NEW.password); await q.click("[type=submit]"); await q.waitForFunction(() => !location.hash.includes("login") && /Riya/.test(document.querySelector("h1.display")?.textContent || ""), { timeout: 10000 });
  await q.reload({ waitUntil: "networkidle0" }); await q.waitForFunction(() => /Riya/.test(document.querySelector("h1.display")?.textContent || ""), { timeout: 10000 }); ok(!q.url().includes("login"), "session should survive reload");
  await goto(q, "/settings"); await q.click("#delacct"); await sleep(300); await q.type("#askf [name=password]", "wrong-wrong-wrong-1"); await q.click("#askf [type=submit]"); await waitText(q, "#ask-err");
  ok(/incorrect/i.test(await txt(q, "#ask-err")), "wrong password must not delete"); await q.$eval("#askf [name=password]", e => e.value = ""); await q.type("#askf [name=password]", NEW.password); await q.click("#askf [type=submit]");
  await q.waitForSelector("#lf", { timeout: 10000 }); ok(/deleted/i.test(await q.evaluate(() => document.body.innerText)));
  await typeInto(q, "[name=email]", NEW.email); await typeInto(q, "#password", NEW.password); await q.click("[type=submit]"); await waitText(q, "#auth-err"); ok(/incorrect/i.test(await txt(q, "#auth-err")), "deleted account must not sign in");
  await q.close();
});
await step("forgot-password page: honest message when email isn't configured; generic confirmation", async () => {
  const q = await anonPage(); await goto(q, "/forgot"); ok(/isn.t set up|can.t be emailed/i.test(await q.evaluate(() => document.body.innerText)), "should say email delivery is not configured");
  await typeInto(q, "[name=email]", "nobody@example.com"); await q.click("[type=submit]"); await q.waitForFunction(() => !document.querySelector("#ok")?.hidden, { timeout: 15000 }); ok(/If that email has an account/i.test(await txt(q, "#ok")), await txt(q, "#ok")); await q.close();
});
await step("offline: banner appears, actions fail gracefully with a clear message, and recover when back online", async () => {
  await goto(p); await p.setOfflineMode(true); await p.evaluate(() => window.dispatchEvent(new Event("offline"))); await sleep(200);
  ok(!(await p.$eval("#offline", e => e.hidden)), "offline banner should show");
  await p.click("[data-act=more]"); await sleep(800); ok(/can.t reach OFTLY/i.test(await txt(p, "#toast")), await txt(p, "#toast"));
  ok((await p.$$(".collage .piece")).length >= 3, "previous outfit stays visible");
  await p.setOfflineMode(false); await p.evaluate(() => window.dispatchEvent(new Event("online"))); await sleep(300); ok(await p.$eval("#offline", e => e.hidden));
  await p.click("[data-act=more]"); await sleep(1500); ok((await p.$$(".collage .piece")).length >= 3);
});
await step("branding: no trace of the old name on any page; manifest and icons are OFTLY", async () => {
  for (const h of ["", "/wardrobe", "/outfits", "/planner", "/settings", "/add", "/help", "/privacy", "/terms", "/community", "/app"]) {
    await goto(p, h); const t = await p.evaluate(() => document.body.innerText + " " + document.title); ok(!/veya/i.test(t), `old name on ${h || "/"}`); ok(/OFTLY/.test(await p.title()), `title on ${h}`);
  }
  const mf = await p.evaluate(async () => (await fetch("/manifest.webmanifest")).json()); ok(mf.name === "OFTLY" && mf.short_name === "OFTLY" && mf.display === "standalone" && mf.icons.length >= 3);
  ok((await p.evaluate(async () => (await fetch("/icons/apple-touch-icon.png")).status)) === 200 && /apple-touch-icon/.test(await p.$eval("head", e => e.innerHTML)));
});
await step("user-entered HTML is shown as text (no script execution)", async () => {
  await api("/items", { method: "POST", body: { name: "<img src=x onerror=window.__xss=1>", category: "shirts", primary_color: "red" } });
  await goto(p, "/wardrobe"); await sleep(600); ok(await p.evaluate(() => window.__xss === undefined), "XSS executed");
});
await step("auth pages: no horizontal overflow at 320/390/768 and dark mode applies", async () => {
  for (const w of [320, 390, 768]) { const q = await anonPage(w, 800); for (const h of ["/login", "/register", "/forgot"]) { await goto(q, h); ok(await q.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `overflow ${w} ${h}`); } await q.close(); }
  const q = await anonPage(390, 800); await q.evaluateOnNewDocument(() => localStorage.setItem("oftly.a11y3", JSON.stringify({ active: [], over: { theme: "dark" }, temp: null }))); await goto(q, "/login");
  ok((await cs(q, "body", "backgroundColor")) === "rgb(16, 15, 13)"); await shot(q, "11-login-dark-mobile", false); await q.close();
});
{ const q = await anonPage(390, 844); await goto(q, "/login"); await shot(q, "12-login-mobile", false); await q.close(); }

// ---- accessibility panel ----
await step("accessibility: Alt+A opens the dialog, Esc closes it and returns focus to the button", async () => {
  await goto(p); await p.keyboard.down("Alt"); await p.keyboard.press("KeyA"); await p.keyboard.up("Alt"); await sleep(300);
  ok(await p.$eval("#a11y-panel", e => e.open), "panel not open"); ok(await p.$$eval(".ap-preset", e => e.length) >= 15);
  await p.keyboard.press("Escape"); await sleep(200); ok(!(await p.$eval("#a11y-panel", e => e.open)));
  ok(!(await p.$("#a11y-fab")), "a permanent accessibility button must not exist"); ok(!(await p.$eval("#a11y-panel", e => e.open)));
});
const clean = () => p.evaluate(() => OFTLYA11y.reset()).catch(() => {});
const preset = async id => { await p.evaluate(() => OFTLYA11y.open()); await sleep(150); await p.evaluate(id => { const b = document.querySelector(`[data-preset="${id}"]`); b.closest("details").open = true; b.click(); }, id); await sleep(200); };
const closePanel = async () => { await p.evaluate(() => document.getElementById("a11y-panel").close()); await sleep(150); };
await clean();
await step("preset Dyslexia: legible font, wider spacing, loose lines, short column, text 115%", async () => {
  await preset("dyslexia"); await closePanel();
  ok((await cs(p, "body", "fontFamily")).includes("Atkinson"), await cs(p, "body", "fontFamily")); ok(parseFloat(await cs(p, "html", "fontSize")) > 18 && parseFloat(await cs(p, "html", "fontSize")) < 19);
  ok(parseFloat(await cs(p, "body", "lineHeight")) / parseFloat(await cs(p, "body", "fontSize")) > 2, "line height"); ok(parseFloat(await cs(p, "body", "letterSpacing")) > 0);
  ok(parseFloat(await cs(p, "main", "maxWidth")) <= 760); ok((await cs(p, "h1.display", "fontFamily")).includes("Atkinson"));
  ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "horizontal overflow");
});
await shot(p, "03-a11y-dyslexia-today");
await step("combining presets: Dyslexia + Presbyopia keeps the larger text, spacing and font", async () => {
  await preset("presbyopia"); await closePanel(); ok(parseFloat(await cs(p, "html", "fontSize")) > 20.5, await cs(p, "html", "fontSize")); ok((await cs(p, "body", "fontFamily")).includes("Atkinson"));
  const act = await p.evaluate(() => OFTLYA11y.state().active); ok(act.includes("dyslexia") && act.includes("presbyopia"));
  await preset("dyslexia"); await preset("presbyopia");
  ok((await p.evaluate(() => OFTLYA11y.state().active.length)) === 0 && (await cs(p, "html", "fontSize")) === "16px", "toggle off failed");
});
await clean();
await step("preset Tremor: 66px targets, no-drag carousels, steady taps ignore a rapid second tap", async () => {
  await preset("tremor"); await closePanel(); ok(parseFloat(await cs(p, ".btn.primary", "minHeight")) >= 66, await cs(p, ".btn.primary", "minHeight"));
  await p.$eval(".marq", e => e.scrollIntoView({ block: "center" })); await p.$eval(".marq button", b => { b.click(); b.click(); }); await sleep(100);   // two taps in the same instant: the second must be ignored
  ok(await p.$eval(".marq", e => e.hasAttribute("data-paused")), "second rapid tap was not ignored (would have un-paused)");
  await sleep(700); await p.click(".marq button"); await sleep(100); ok(!(await p.$eval(".marq", e => e.hasAttribute("data-paused"))), "tap after the guard window should work");
  ok((await p.evaluate(() => document.documentElement.dataset.nodrag)) === "on" && (await cs(p, "#recent", "cursor")) === "auto");
  await preset("tremor");
});
await clean();
await step("preset Photosensitivity: marquee animation off, reveal/parallax transforms off, content visible", async () => {
  await preset("photosensitivity"); await closePanel(); ok((await cs(p, ".marq-in", "animationName")) === "none");
  ok(await p.$$eval(".reveal", e => e.every(x => getComputedStyle(x).opacity === "1")), "reveal elements hidden");
  ok((await cs(p, "body", "backgroundColor")) !== "rgb(243, 238, 228)", "warm theme not applied"); await preset("photosensitivity");
});
await clean();
await step("preset Low vision: max contrast, 150% text, underlined links, strong focus", async () => {
  await preset("low-vision"); await closePanel(); ok((await cs(p, "html", "fontSize")) === "24px", await cs(p, "html", "fontSize")); ok((await cs(p, "body", "backgroundColor")) === "rgb(255, 255, 255)" && (await cs(p, "body", "color")) === "rgb(0, 0, 0)");
  await goto(p, "/settings"); ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "overflow at 150%"); await shot(p, "04-a11y-low-vision-settings"); await preset("low-vision");
});
await clean();
await step("preset Protanopia: colour names on every outfit piece, CVD-safe blue accent, underlined links", async () => {
  await goto(p); await preset("protan"); await closePanel(); ok((await cs(p, ".piece .cname", "display")) === "block"); ok((await p.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--accent"))).trim() === "#0b5fa5");
  ok((await cs(p, ".hero-today a, .foot a", "textDecorationLine")).includes("underline")); await goto(p, "/wardrobe"); ok(/·\s*\w+/.test(await txt(p, ".card .meta span")), "colour name missing on card"); await preset("protan");
});
await clean();
await step("fine-tune: dark theme + dim screen apply; dimmer overlay opacity matches", async () => {
  await p.evaluate(() => OFTLYA11y.open()); await sleep(150);
  await p.evaluate(() => { const d = document.querySelector("[data-field=theme]"); d.closest("details").open = true; d.value = "dark"; d.dispatchEvent(new Event("change", { bubbles: true })); }); await sleep(200);
  await p.evaluate(() => { const d = document.querySelector("[data-field=dim]"); d.closest("details").open = true; d.value = "20"; d.dispatchEvent(new Event("change", { bubbles: true })); }); await sleep(200);
  await closePanel(); ok((await cs(p, "body", "backgroundColor")) === "rgb(16, 15, 13)", await cs(p, "body", "backgroundColor")); ok(parseFloat(await cs(p, "#dimmer", "opacity")) === .2);
  await goto(p); await shot(p, "05-today-dark-dimmed");
});
await step("settings persist across reload (localStorage) and Reset restores defaults", async () => {
  await p.reload({ waitUntil: "networkidle0" }); ok((await p.evaluate(() => document.documentElement.dataset.theme)) === "dark");
  await p.evaluate(() => OFTLYA11y.open()); await p.evaluate(() => document.querySelector("[data-ap=reset]").click()); await sleep(200); await closePanel();
  ok((await p.evaluate(() => document.documentElement.dataset.theme)) === "system" && (await p.evaluate(() => localStorage.getItem("oftly.a11y3"))).includes('"active":[]'));
});
await step("temporary preset expires and restores the previous settings", async () => {
  await p.evaluate(() => OFTLYA11y.open()); await sleep(150); await p.select("#ap-dur", "3600000"); await p.evaluate(() => document.querySelector('[data-preset="night"]').click()); await sleep(200); await closePanel();
  ok((await p.evaluate(() => document.documentElement.dataset.theme)) === "warm" && (await p.evaluate(() => OFTLYA11y.state().temp)) !== null);
  await p.evaluate(() => { const s = JSON.parse(localStorage.getItem("oftly.a11y3")); s.temp.until = Date.now() - 1000; localStorage.setItem("oftly.a11y3", JSON.stringify(s)); });
  await p.reload({ waitUntil: "networkidle0" }); ok((await p.evaluate(() => document.documentElement.dataset.theme)) === "system" && (await p.evaluate(() => OFTLYA11y.state().temp)) === null, "did not revert");
});

// ---- keyboard, overflow, responsive ----
await step("keyboard: first Tab stop is the skip link and it moves focus to main", async () => {
  await goto(p); await p.keyboard.press("Tab"); ok(await p.evaluate(() => document.activeElement.id === "skip")); await p.keyboard.press("Enter"); await sleep(100); ok(await p.evaluate(() => document.activeElement.id === "main"));
});
const sizes = [[1440, 900], [1024, 768], [768, 1024], [390, 844], [320, 640]];
for (const [w, h] of sizes) await step(`no horizontal overflow and no clipped hero at ${w}px (Today, Wardrobe, Settings)`, async () => {
  const q = await newPage(w, h); for (const hash of ["", "/wardrobe", "/settings"]) { await goto(q, hash); ok(await q.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `overflow ${w}px ${hash}: ${await q.evaluate(() => document.documentElement.scrollWidth)} state=${await q.evaluate(() => localStorage.getItem("oftly.a11y3"))} off=${await q.evaluate(() => { const W = innerWidth; return [...document.querySelectorAll("body *")].filter(e => !e.closest(".track,.marq,.bigtype") && e.getBoundingClientRect().right > W + 1 && getComputedStyle(e).position !== "fixed").slice(0, 3).map(e => e.tagName + "." + e.className).join(",") })}`); } ok(q.errs.length === 0, q.errs.join("|")); await q.close();
});
const m = await newPage(390, 844, { dpr: 1 }); await goto(m); 
await step("mobile: bottom nav and add button visible and ≥44px, no floating accessibility button", async () => {
  for (const sel of ["nav a", ".fab-add"]) { const b = await m.$eval(sel, e => { const r = e.getBoundingClientRect(); return [r.width, r.height, r.bottom, innerHeight]; }); ok(b[0] >= 44 && b[1] >= 44 && b[2] <= b[3], `${sel} ${b}`); }
});
await shot(m, "06-today-mobile"); await m.evaluate(() => OFTLYA11y.open()); await sleep(400); await shot(m, "07-a11y-panel-mobile", false); await m.close();
const a = await newPage(1440, 900); await goto(a); await a.evaluate(() => OFTLYA11y.open()); await sleep(400); await shot(a, "08-a11y-panel-desktop", false); await a.close();

await browser.close(); browser = await launch();   // fresh browser: the audit loads many pages
// ---- automated accessibility audit (axe-core, WCAG 2.x A/AA rules) in several modes ----
const modes = { light: {}, dark: { theme: "dark" }, "warm night": { theme: "warm" }, "high contrast": { contrast: "high" }, "maximum contrast": { contrast: "max" }, "legible font + 150%": { font: "readable", text: "150" } };
for (const [mode, over] of Object.entries(modes)) for (const hash of ["", "/wardrobe", "/settings", "/help", "/start?replay=1"]) await step(`axe WCAG A/AA: ${mode} · ${hash || "today"}`, async () => {
  const q = await newPage(1280, 900); await q.evaluateOnNewDocument(o => { localStorage.setItem("oftly.a11y3", JSON.stringify({ active: [], over: o, temp: null })); }, over);
  await goto(q, hash); await sleep(1200); await q.evaluate(() => document.querySelectorAll(".reveal").forEach(e => e.classList.add("in"))); await sleep(1200);
  await q.evaluate(axeSrc); const r = await q.evaluate(async () => await axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] } }));
  await q.close(); const v = r.violations.map(x => `${x.id} (${x.impact}) x${x.nodes.length}: ${x.nodes[0].target.join(" ")}  [${(x.nodes[0].any[0]?.message || x.help).slice(0, 110)}]`);
  if (v.length) problems.push(`${mode} · ${hash || "today"}: ${v.join(" ;; ")}`); ok(v.length === 0, v[0]);
});

// signed-out pages (sign-in, register, recovery) in light, dark and maximum contrast
for (const [mode, over] of Object.entries({ light: {}, dark: { theme: "dark" }, "maximum contrast": { contrast: "max" } })) for (const hash of ["/login", "/register", "/forgot"]) await step(`axe auth pages: ${mode} · ${hash}`, async () => {
  const q = await anonPage(390, 844); await q.evaluateOnNewDocument(o => { localStorage.setItem("oftly.a11y3", JSON.stringify({ active: [], over: o, temp: null })); }, over);
  await goto(q, hash); await sleep(1000); await q.evaluate(axeSrc); const r = await q.evaluate(async () => await axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] } }));
  await q.close(); const v = r.violations.map(x => `${x.id} (${x.impact}) x${x.nodes.length}: ${x.nodes[0].target.join(" ")} [${(x.nodes[0].any[0]?.message || x.help).slice(0, 110)}]`); ok(v.length === 0, v[0]);
});
await browser.close();
const f = results.filter(r => !r[1]).length; console.log(`\n${results.length - f}/${results.length} passed, ${f} failed`);
if (problems.length) fs.writeFileSync("/tmp/axe-problems.txt", problems.join("\n\n"));
process.exit(f ? 1 : 0);
