/* OFTLY frontend: dependency-free single-page app (hash routing). All user text goes through esc(). */
const OCC = ["casual", "college", "work", "party", "date", "formal", "travel", "wedding"];
const SEASONS = ["spring", "summer", "autumn", "winter"];
const STYLES = ["casual", "smart-casual", "formal", "sporty", "streetwear", "classic", "minimalist", "ethnic", "bohemian"];
const PATTERNS = ["solid", "striped", "checked", "floral", "printed", "textured", "other"];
const COLORS = ["black","white","grey","beige","cream","brown","tan","khaki","navy","blue","light blue","denim","green","olive","teal","red","burgundy","pink","orange","yellow","mustard","purple","silver","gold"];
const FORMAL = ["", "Very casual", "Casual", "Smart casual", "Dressy", "Formal"];
const $ = (s, r = document) => r.querySelector(s);
const main = $("#main");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const cap = s => s ? s[0].toUpperCase() + s.slice(1) : "";
let CATS = [], PREFS = {};
let GEN = { list: [], seen: [], occ: "", dest: "", day: 0, msg: "", weather: null };

async function api(path, opts = {}) {
  const isForm = opts.body instanceof FormData, method = (opts.method || "GET").toUpperCase();
  const headers = { ...(opts.body && !isForm ? { "Content-Type": "application/json" } : {}), ...(method !== "GET" ? { "X-CSRF-Token": csrfToken() } : {}) };
  let r;
  try { r = await fetch("/api" + path, { ...opts, method, headers, body: opts.body && !isForm ? JSON.stringify(opts.body) : opts.body, credentials: "same-origin" }); }
  catch { throw new Error("Can’t reach OFTLY. Check your connection and try again."); }
  if (!r.ok) {
    let m = r.statusText;
    try { const j = await r.json(); m = Array.isArray(j.detail) ? j.detail.map(d => `${(d.loc || []).slice(-1)[0] || ""} ${d.msg}`).join("; ") : (j.detail || m); } catch {}
    if (r.status === 401 && !path.startsWith("/auth/") && SESSION) { SESSION = null; document.body.dataset.auth = "out"; location.hash = "#/login?msg=expired"; }
    if (r.status === 429) m = m || "Too many requests. Please wait a moment.";
    throw new Error(m);
  }
  return r.status === 204 ? null : r.json();
}
let toastT;
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("show"), window.OFTLYA11y ? OFTLYA11y.toastMs() : 3200); }
const guard = fn => async (...a) => { try { await fn(...a); } catch (e) { toast(e.message); } };
const catLabel = id => (CATS.find(c => c.id === id) || {}).label || id;
const img = (i, cls = "") => i.image_url ? `<img loading="lazy" src="${esc(i.image_url)}" alt="${esc(i.name)}">` : `<div class="noimg">${esc(i.category_label || "No photo")}</div>`;
const card = i => `<a class="card" href="#/item/${i.id}"><div class="ph">${img(i)}${i.favorite ? '<span class="fav" aria-label="Favourite">♥</span>' : ""}${i.is_demo ? '<span class="demo">Demo</span>' : ""}${i.status !== "available" ? `<span class="stat">${esc(i.status)}</span>` : ""}</div><div class="meta"><b>${esc(i.name)}</b><span>${esc(i.category_label)}${i.primary_color ? ` · <i class="dot" style="background:${FX.hex(i.primary_color)}"></i>${esc(i.primary_color)}` : ""}</span></div></a>`;
const opts = (list, sel, blank) => (blank !== undefined ? `<option value="">${esc(blank)}</option>` : "") + list.map(v => `<option value="${esc(v)}" ${v === sel ? "selected" : ""}>${esc(cap(v))}</option>`).join("");
const checks = (name, list, sel = []) => `<div class="chips">${list.map(v => `<label class="chip"><input type="checkbox" name="${name}" value="${esc(v)}" ${sel.includes(v) ? "checked" : ""}>${esc(cap(v))}</label>`).join("")}</div>`;
const checked = (root, name) => [...root.querySelectorAll(`input[name=${name}]:checked`)].map(i => i.value);
const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

/* ---------- router ---------- */
const pages = { today: pageToday, wardrobe: pageWardrobe, item: pageItem, add: pageAdd, outfits: pageOutfits, outfit: pageOutfit, planner: pagePlanner, settings: pageSettings, ...AUTH_PAGES,
  help: () => pageInfo("help"), privacy: () => pageInfo("privacy"), terms: () => pageInfo("terms"), community: () => pageInfo("community"), app: () => pageInfo("app") };
async function route() {
  const [path, qs] = (location.hash.slice(1) || "/").split("?");
  const [name = "today", arg] = path.split("/").filter(Boolean);
  if (!SESSION && !PUBLIC_PAGES.includes(name)) { location.hash = "#/login"; return; }
  if (SESSION && ["login", "register", "forgot"].includes(name)) { location.hash = "#/"; return; }
  document.querySelectorAll("[data-nav]").forEach(a => a.classList.toggle("on", a.dataset.nav === (["item", "add"].includes(name) ? "wardrobe" : name === "outfit" ? "outfits" : name)));
  main.setAttribute("aria-busy", "true"); main.innerHTML = '<div class="skeleton" role="status" aria-label="Loading"></div>';
  try { await (pages[name] || pageToday)(arg, Object.fromEntries(new URLSearchParams(qs || ""))); }
  catch (e) { main.innerHTML = `<div class="empty"><h2>That didn’t load</h2><p>${esc(e.message)}</p><a class="btn" href="#/">Back to today</a></div>`; }
  main.removeAttribute("aria-busy"); window.scrollTo(0, 0); if (route.n++) main.focus({ preventScroll: true }); FX.after(main);
  document.title = (main.querySelector("h1")?.textContent || "OFTLY").replace(/\s+/g, " ").trim().slice(0, 60) + " · OFTLY";
}
route.n = 0;
addEventListener("hashchange", route);
main.addEventListener("click", e => { const b = e.target.closest("[data-act]"); if (b) guard(ACTIONS[b.dataset.act])(b.dataset, b); });

/* ---------- modal ---------- */
function modal(html) { const d = $("#dlg"); d.innerHTML = html; d.showModal(); return d; }

/* ---------- outfit component ---------- */
const noteOf = (o, id) => ((o.style && o.style.pieces.find(p => p.id === id)) || {}).note || "";
const reasoning = o => { const s = o.style; if (!s) return ""; const adj = s.adjustments || {};
  return `<details class="how"><summary>Why this works for you</summary>
  <p><b>Intention.</b> ${esc(s.intention)}</p><p><b>Colour.</b> ${esc(s.colour_story)}</p><p>${esc(s.focal_point.text)}</p>
  <p><b>For today.</b></p><ul>${s.practical.map(t => `<li>${esc(t)}</li>`).join("")}</ul>
  <p><b>For you.</b></p><ul>${s.why_for_you.map(t => `<li>${esc(t)}</li>`).join("")}</ul>
  <p><b>Score factors.</b> ${s.factors.map(f => `${esc(f.label)} ${f.value}`).join(" · ")}${s.weakest ? ` · weakest: ${esc(s.weakest.label)} ${s.weakest.value}` : ""}${adj.learned ? ` · learned from your feedback ${adj.learned > 0 ? "+" : ""}${adj.learned}` : ""}${adj.avoided_colour ? ` · avoided colour ${adj.avoided_colour}` : ""}</p>
  <p class="muted"><small>OFTLY has no data on ${esc(s.not_assessed.join(" or "))}, so it doesn't comment on them.</small></p></details>`; };
const outfitCard = (o, i, alt = false, opt = {}) => `<article class="outfit ${alt ? "alt" : ""}" data-i="${i}">
  ${o.style ? `<h3 class="o-title">${esc(o.style.title)}</h3>` : ""}
  <div class="o-items">${o.items.map(it => `<div class="o-item"><a href="#/item/${it.id}"><div class="ph">${img(it)}</div></a><div class="o-meta"><span>${esc(it.name)}</span><button class="link" data-act="swap" data-i="${i}" data-id="${it.id}" aria-label="Swap ${esc(it.name)}">Swap</button></div><small class="note">${esc(noteOf(o, it.id))}</small></div>`).join("")}</div>
  <div class="o-foot"><div>${o.score != null ? `<span class="score">${Math.round(o.score)}</span><small> / 100 match</small>` : ""}<p class="why">${esc(o.style ? o.style.intention : (o.reason || ""))}</p>${reasoning(o)}</div>
  <div class="row">${opt.saved ? "" : `<button class="btn sm" data-act="reject" data-i="${i}">Not for me</button><button class="btn sm" data-act="save" data-i="${i}">Save</button><button class="btn sm primary" data-act="wearnew" data-i="${i}">Wear today</button>`}</div></div></article>`;

function ctxOf(o) { return { item_ids: o.item_ids, occasion: GEN.occ, destination: GEN.dest, day: GEN.day }; }
async function swapFlow(o, replaceId, ctx, onPick) {
  const { alternatives } = await api("/outfits/alternatives", { method: "POST", body: { ...ctx, replace_id: replaceId } });
  const old = o.items.find(i => i.id === replaceId);
  const d = modal(`<h3>Swap ${esc(old.name)}</h3><p class="muted">Only your available ${esc(old.category_label.toLowerCase())} are shown, best match first. The rest of the outfit stays the same.</p>
    ${alternatives.length ? `<div class="alts">${alternatives.map(a => `<button data-pick="${a.item.id}"><div class="ph">${img(a.item)}</div><div class="meta"><b>${esc(a.item.name)}</b><span>${Math.round(a.score)} / 100</span></div></button>`).join("")}</div>` : '<div class="empty"><p>No other available items of this type. Add more to your wardrobe.</p></div>'}
    <div class="row" style="margin-top:1rem"><button class="btn" data-close>Cancel</button></div>`);
  d.querySelector("[data-close]").onclick = () => d.close();
  d.querySelectorAll("[data-pick]").forEach(b => b.onclick = guard(async () => {
    const a = alternatives.find(x => x.item.id === +b.dataset.pick); d.close(); await onPick(a.item_ids);
  }));
}
const evaluate = (ids, ctx) => api("/outfits/evaluate", { method: "POST", body: { item_ids: ids, occasion: ctx.occasion, destination: ctx.destination || "", day: ctx.day || 0 } });

const ACTIONS = {
  async swap({ i, id }) {
    if (document.body.dataset.page === "outfit") { const o = OUTFIT; return swapFlow(o, +id, {item_ids: o.item_ids}, async ids => { OUTFIT = await api(`/outfits/${o.id}`, { method: "PATCH", body: { item_ids: ids } }); renderOutfit(); toast("Swapped and saved"); }); }
    const o = GEN.list[+i];
    await swapFlow(o, +id, ctxOf(o), async ids => { GEN.list[+i] = await evaluate(ids, GEN); renderGen(); });
  },
  async save({ i }) { const s = await api("/outfits", { method: "POST", body: { name: (GEN.list[+i].style || {}).title || "", item_ids: GEN.list[+i].item_ids, score: GEN.list[+i].score, reason: GEN.list[+i].reason } });
    await api("/feedback", { method: "POST", body: { item_ids: GEN.list[+i].item_ids, action: "like" } }); toast("Saved to Outfits"); return s; },
  async reject({ i }) {
    const o = GEN.list[+i]; await api("/feedback", { method: "POST", body: { item_ids: o.item_ids, action: "reject" } });
    GEN.list.splice(+i, 1); GEN.list.length ? renderGen() : await generate();
  },
  async wearnew({ i }) { const o = GEN.list[+i]; const s = await api("/outfits", { method: "POST", body: { name: (o.style || {}).title || "", item_ids: o.item_ids, score: o.score, reason: o.reason } }); await api(`/outfits/${s.id}/wear`, { method: "POST", body: {} }); toast("Logged as worn today"); },
  async more() { await generate(); },
  promote({ i }) { const k = +i; [GEN.list[0], GEN.list[k]] = [GEN.list[k], GEN.list[0]]; renderGen(); $("#gen").scrollIntoView({ behavior: FX.motionOff() ? "auto" : "smooth", block: "start" }); },
  async wxon() { PREFS = await api("/preferences", { method: "PUT", body: { use_weather: true } }); GEN.seen = []; toast("Weather on. Only place names are sent to Open-Meteo."); await generate(); },
  async demo() { toast("Creating your demo wardrobe. This takes about ten seconds…"); await api("/demo", { method: "POST" }); await api("/preferences", { method: "PUT", body: { onboarded: true } }); PREFS.onboarded = true; toast("Demo wardrobe loaded"); location.hash = "#/"; route(); },
};

/* ---------- Today ---------- */
const RECENT = () => { try { return JSON.parse(localStorage.getItem("oftly.dests") || "[]"); } catch { return []; } };
const remember = d => { if (!d) return; const l = [d, ...RECENT().filter(x => x.toLowerCase() !== d.toLowerCase())].slice(0, 6); try { localStorage.setItem("oftly.dests", JSON.stringify(l)); } catch { /* storage blocked: fine */ } };
async function generate(retry) {
  const el = $("#gen"); if (el) el.setAttribute("aria-busy", "true");
  const p = new URLSearchParams({ count: 4, seed: Math.floor(Math.random() * 1e9), occasion: GEN.occ, destination: GEN.dest, day: GEN.day });
  if (GEN.seen.length && !retry) p.set("exclude", GEN.seen.join(";"));
  const r = await api("/outfits/generate?" + p);
  if (!r.outfits.length && GEN.seen.length && !retry) { GEN.seen = []; return generate(true); }
  GEN.list = r.outfits; GEN.msg = r.message; GEN.weather = r.weather; GEN.place = r.destination; r.outfits.forEach(o => GEN.seen.push(o.signature));
  renderGen(); renderWx(); if (el) el.removeAttribute("aria-busy");
}
const plain = o => `${o.style.title}\n${o.items.map(i => "- " + i.name).join("\n")}\n${o.style.intention}\nMatch score: ${Math.round(o.score)}/100 (OFTLY)`;
const slideHTML = (id, label, slides) => `<div class="carousel" role="region" aria-roledescription="carousel" aria-label="${esc(label)}"><div class="track" tabindex="0" id="${id}">${slides.map(x => `<div class="slide">${x}</div>`).join("")}</div>
  <div class="car-ui"><button class="arrow" data-dir="-1" aria-label="Previous" aria-controls="${id}">←</button><div class="prog" aria-hidden="true"><i></i></div><button class="arrow" data-dir="1" aria-label="Next" aria-controls="${id}">→</button></div></div>`;
function stage(o) {
  const s = o.style, sc = Math.round(o.score), n = o.items.length, bars = [...s.factors, ...(s.weakest ? [{ label: s.weakest.label + " (weakest)", value: s.weakest.value }] : [])];
  return `<div class="stage"><div class="collage n${n === 4 ? 4 : 3}">${o.items.map((it, k) => `<figure class="piece"><a class="ph" href="#/item/${it.id}">${img(it)}</a><span class="idx" aria-hidden="true">${String(k + 1).padStart(2, "0")}</span>
    <figcaption><span><b>${esc(it.name)}</b><span class="cname">${esc(it.primary_color || "colour not set")}</span><small class="note">${esc(noteOf(o, it.id))}</small></span><button class="btn sm ghost" data-act="swap" data-i="0" data-id="${it.id}" aria-label="Swap ${esc(it.name)}">Swap</button></figcaption></figure>`).join("")}</div>
  <div class="look-panel"><span class="eyebrow">Today’s look · ref ${esc(o.signature)}</span><h2 class="look-title">${esc(s.title)}</h2>
    <div class="score-row"><div class="ring" style="--p:${sc}" role="img" aria-label="Match score ${sc} out of 100"><svg viewBox="0 0 104 104" aria-hidden="true"><circle class="bg" cx="52" cy="52" r="46"/><circle class="fg" cx="52" cy="52" r="46"/></svg><span class="num" data-count="${sc}" aria-hidden="true">${sc}</span></div>
      <p class="why">${esc(s.intention)}</p></div>
    <ul class="fbars">${bars.map(f => `<li><span>${esc(f.label)}</span><span class="gbar" aria-hidden="true"><i style="--v:${f.value}%"></i></span><b>${f.value}</b></li>`).join("")}</ul>
    <p class="why">${esc(s.focal_point.text)}</p>${s.practical[0] ? `<p class="why"><b>Today:</b> ${esc(s.practical[0])}</p>` : ""}${reasoning(o)}
    <div class="row"><button class="btn primary" data-act="wearnew" data-i="0">Wear today</button><button class="btn" data-act="save" data-i="0">Save</button><button class="btn ghost" data-act="reject" data-i="0">Not for me</button><button class="btn ghost" data-copy="${esc(plain(o))}">Copy summary</button></div>
  </div></div>`;
}
const altSlide = (o, i) => `<article class="altcard"><div class="minigrid">${o.items.slice(0, 3).map(it => `<div class="ph">${img(it)}</div>`).join("")}</div>
  <div><span class="eyebrow">Option ${String(i).padStart(2, "0")}</span><h3>${esc(o.style.title)}</h3></div><p>${esc(o.style.colour_story)}</p>
  <div class="row between"><span class="sc">${Math.round(o.score)}<small> / 100</small></span><button class="btn sm primary" data-act="promote" data-i="${i}">Make it my look</button></div>
  <div class="row"><button class="btn sm ghost" data-act="save" data-i="${i}">Save</button><button class="btn sm ghost" data-act="reject" data-i="${i}">Not for me</button></div></article>`;
function renderGen() {
  const el = $("#gen"); if (!el) return;
  if (!GEN.list.length) { el.innerHTML = `<div class="empty"><h3>No outfit to suggest yet</h3><p>${esc(GEN.msg)}</p><a class="btn" href="#/add">Add an item</a></div>`; return; }
  el.innerHTML = `<div class="sect-head"><div><span class="eyebrow">01 — The look</span><h2>Dressed for <em>${esc(GEN.place || "today")}</em></h2></div></div><div class="reveal">${stage(GEN.list[0])}</div>
  ${GEN.list.length > 1 ? `<div class="sect-head deco"><div><span class="eyebrow">02 — Alternatives</span><h2>More ways to <em>wear it</em></h2></div></div><div class="reveal deco">${slideHTML("alts", "Alternative outfits", GEN.list.slice(1).map((o, k) => altSlide(o, k + 1)))}</div>` : ""}
  ${GEN.msg ? `<p class="muted">${esc(GEN.msg)}</p>` : ""}`;
  FX.after(el);
}
function renderWx() {
  const el = $("#wxcard"); if (!el) return; const w = GEN.weather;
  const bar = (l, v, max, unit) => `<div class="gauge"><span class="eyebrow">${l}</span><b>${v == null ? "n/a" : Math.round(v) + unit}</b><span class="gbar" aria-hidden="true"><i style="--v:${v == null ? 0 : Math.min(100, v / max * 100)}%"></i></span></div>`;
  if (!PREFS.use_weather) el.innerHTML = `<div class="wx-off"><span class="eyebrow">Weather</span><h2>Plan around the forecast</h2><p>Turn weather on and OFTLY styles for the temperature, rain, humidity and wind at your destination. Only the place name is sent to Open-Meteo. Nothing is guessed while it’s off.</p><button class="btn primary" data-act="wxon">Turn on weather</button></div>`;
  else if (w && w.available) { const d = new Date(w.date + "T12:00"); el.innerHTML = `<div class="where"><span class="eyebrow">${esc(w.city)}${w.country ? ", " + esc(w.country) : ""} · ${GEN.day ? d.toLocaleDateString(undefined, { weekday: "long" }) : "now"}</span><span class="tech">${esc(w.source)}</span></div>
    <div class="row between" style="align-items:flex-end"><span class="num temp"><span data-count="${w.temp_c}" data-dec="0">${Math.round(w.temp_c)}</span>°</span><span class="eyebrow">${{ winter: "Cold", autumn: "Cool", spring: "Mild", summer: "Hot" }[w.band]}${w.temp_min != null ? ` · ${Math.round(w.temp_min)}–${Math.round(w.temp_max)}°` : ""}</span></div>
    <div class="gauges">${bar("Rain", w.rain_chance, 100, "%")}${bar("Humidity", w.humidity, 100, "%")}${bar("Wind", w.wind_kph, 60, " km/h")}</div>`; }
  else el.innerHTML = `<div class="wx-off"><span class="eyebrow">Weather</span><h2>No forecast right now</h2><p>${esc((w && w.reason) || (GEN.place ? "Weather is unavailable." : "Add a destination, or set a home city in Settings."))} Styling continues without it, and OFTLY won’t guess.</p></div>`;
  FX.after(el);
}
async function pageToday() {
  document.body.dataset.page = "today";
  const [sum, recent, saved] = await Promise.all([api("/summary"), api("/items?sort=recent&page_size=8"), api("/outfits")]);
  if (!PREFS.walkthrough_done) { location.hash = "#/start"; return; }
  const now = new Date();
  const hero = `<section class="hero-today"><div class="meta-row tech"><span>OFTLY · ${now.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</span><span>${now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span><span>${sum.total} piece${sum.total === 1 ? "" : "s"} in your wardrobe</span></div>
    <h1 class="display">${greeting(now, PREFS.preferred_name)}</h1><p class="hero-sub">${esc(dayLine(now))}</p></section>`;
  if (!sum.total) { main.innerHTML = hero + `<div class="empty"><h3>Your wardrobe is empty</h3><p>Add a few shirts, bottoms and shoes and OFTLY will start suggesting outfits.</p><div class="row" style="justify-content:center"><a class="btn primary" href="#/add">Add your first item</a>${CFG.demo_enabled ? '<button class="btn" data-act="demo">Load sample items (testing only)</button>' : ""}</div></div>`; return; }
  if (!GEN.init) { GEN.occ = PREFS.default_occasion || ""; GEN.init = true; }
  const days = Array.from({ length: 7 }, (_, k) => k === 0 ? "Today" : k === 1 ? "Tomorrow" : new Date(Date.now() + k * 864e5).toLocaleDateString(undefined, { weekday: "long" }));
  const ins = await api("/insights");
  const tot = Math.max(1, ins.total), pct = Math.round(ins.worn_30d / tot * 100), colTotal = ins.colours.reduce((a, [, n]) => a + n, 0) || 1;
  main.innerHTML = `${hero}
  <section class="planner reveal"><form class="plan-card" id="plan"><h2>Where are you <em>headed</em>?</h2>
    <div class="plan-grid"><label>Destination<input id="dest" list="dests" maxlength="80" autocomplete="off" placeholder="${esc(PREFS.city || "City or place")}" value="${esc(GEN.dest)}"></label>
      <label>When<select id="day">${days.map((d, k) => `<option value="${k}" ${GEN.day === k ? "selected" : ""}>${esc(d)}</option>`).join("")}</select></label></div>
    <datalist id="dests">${RECENT().map(d => `<option value="${esc(d)}">`).join("")}</datalist>
    <div class="seg" role="group" aria-label="Occasion">${["", ...OCC].map(o => `<button type="button" data-occ="${o}" aria-pressed="${GEN.occ === o}">${o ? cap(o) : "Any occasion"}</button>`).join("")}</div>
    <div class="row" style="margin-top:1.1rem"><button class="btn primary" type="submit">Style me</button><button type="button" class="btn" data-act="more">Another outfit</button>${PREFS.city ? `<button type="button" class="btn ghost" id="home">Use ${esc(PREFS.city)}</button>` : ""}</div></form>
    <aside class="plan-card wx" id="wxcard" aria-live="polite"><div class="skeleton" style="min-height:140px"></div></aside></section>
  <div class="marq deco" role="presentation"><div class="marq-in">${[0, 1].map(k => `<span ${k ? 'aria-hidden="true"' : ""}>Your Wardrobe. Reimagined. <b>✦</b></span><span ${k ? 'aria-hidden="true"' : ""}>Style More. Buy Less. <b>✦</b></span><span ${k ? 'aria-hidden="true"' : ""}>Wear what you own <b>✦</b></span>`).join("")}</div><button class="btn sm" type="button" aria-pressed="false">Pause</button></div>
  <div id="gen" aria-live="polite"></div>
  <div class="sect-head"><div><span class="eyebrow">03 — Your wardrobe, measured</span><h2>Insights from <em>what you actually wear</em></h2></div><a class="btn sm" href="#/wardrobe">Open wardrobe</a></div>
  <div class="tiles">
    <div class="tile t4 keep"><span class="eyebrow">Worn this month</span><div class="ring" style="--p:${pct}"><svg viewBox="0 0 104 104" aria-hidden="true"><circle class="bg" cx="52" cy="52" r="46"/><circle class="fg" cx="52" cy="52" r="46"/></svg><span class="num" aria-hidden="true">${pct}%</span></div><p class="muted" style="margin:0">${ins.worn_30d} of ${ins.total} pieces in the last 30 days</p></div>
    <div class="tile t4 keep"><span class="eyebrow">Resting</span><span class="num" data-count="${ins.dormant_60d}">${ins.dormant_60d}</span><p class="muted" style="margin:0">pieces not worn in 60+ days. ${ins.never_worn} never worn.</p><a class="link" href="#/wardrobe?unworn_days=60">Show them</a></div>
    <div class="tile t4"><span class="eyebrow">Palette balance</span>${ins.neutral_share == null ? '<p class="muted">Add item colours to see this.</p>' : `<span class="num">${Math.round(ins.neutral_share * 100)}%</span><div class="split" role="img" aria-label="${Math.round(ins.neutral_share * 100)}% neutral, ${100 - Math.round(ins.neutral_share * 100)}% colour"><i style="width:${ins.neutral_share * 100}%"></i><i style="width:${100 - ins.neutral_share * 100}%"></i></div><p class="muted" style="margin:0">neutral · ${100 - Math.round(ins.neutral_share * 100)}% colour</p>`}</div>
    <div class="tile t8"><span class="eyebrow">Weekly rhythm · outfits worn per week</span>${Math.max(...ins.wears_by_week) ? `<div class="spark" role="img" aria-label="Outfits worn per week, oldest to newest: ${ins.wears_by_week.join(", ")}">${ins.wears_by_week.map(v => `<i style="--h:${Math.max(4, v / Math.max(...ins.wears_by_week) * 100)}%"></i>`).join("")}</div><p class="muted" style="margin:0">Last 8 weeks, oldest to newest.</p>` : '<p class="muted">Mark outfits as worn and your rhythm appears here.</p>'}</div>
    <div class="tile t4"><span class="eyebrow">Best value per wear</span>${ins.cost_per_wear.length ? `<ul class="cpw">${ins.cost_per_wear.map(c => `<li><a href="#/item/${c.id}">${esc(c.name)}</a><b>${c.per_wear}</b></li>`).join("")}</ul>` : '<p class="muted">Add prices and wear history to see cost per wear.</p>'}</div>
    <div class="tile t12 deco"><span class="eyebrow">Your palette</span><div class="palette" role="img" aria-label="Colour mix: ${ins.colours.map(([c, n]) => c + " " + n).join(", ")}">${ins.colours.map(([c, n]) => `<i style="--n:${n};background:${FX.hex(c)}" title="${esc(c)} · ${n}"></i>`).join("")}</div>
      <div class="legend">${ins.colours.map(([c, n]) => `<span><i class="dot" style="background:${FX.hex(c)}"></i>${esc(c)} ${Math.round(n / colTotal * 100)}%</span>`).join("")}</div></div>
    <div class="tile t12 deco"><span class="eyebrow">Wardrobe map · formality across, category down</span><div class="vmap" id="vmap"><canvas role="img" aria-label="Map of your wardrobe: each coloured cell is one garment, placed by formality and category"></canvas><span class="tip" aria-hidden="true">Hover or tap a cell</span></div></div>
  </div>
  <div class="sect-head deco"><div><span class="eyebrow">04 — Browse</span><h2>By <em>category</em></h2></div></div>
  <div class="chips reveal deco">${CATS.map(c => `<a class="chip" href="#/wardrobe?category=${c.id}">${esc(c.label)}${sum.by_category[c.id] ? ` (${sum.by_category[c.id]})` : ""}</a>`).join("")}</div>
  <div class="sect-head deco"><div><span class="eyebrow">05 — Recently added</span><h2>Fresh in your <em>wardrobe</em></h2></div></div>
  <div class="reveal deco">${slideHTML("recent", "Recently added items", recent.items.map(card))}</div>
  <div class="sect-head deco"><div><span class="eyebrow">06 — Saved</span><h2>Looks you <em>kept</em></h2></div></div>
  ${saved.length ? `<div class="reveal deco">${slideHTML("savedc", "Saved outfits", saved.map(o => `<a class="card" href="#/outfit/${o.id}"><div class="ph">${img(o.items[0] || {})}</div><div class="meta"><b>${esc(o.name || "Outfit " + o.id)}</b><span>${o.items.length} pieces</span></div></a>`))}</div>` : '<p class="muted">Nothing saved yet. Press Save on a look you like.</p>'}
  <div class="bigtype deco" aria-hidden="true" data-speed="0.07">OFTLY</div>`;
  const plan = $("#plan"), apply = () => { GEN.dest = $("#dest").value.trim(); GEN.day = +$("#day").value; remember(GEN.dest); GEN.seen = []; return guard(generate)(); };
  plan.onsubmit = e => { e.preventDefault(); apply(); };
  $("#day").onchange = apply;
  $("#home")?.addEventListener("click", () => { $("#dest").value = ""; apply(); });
  plan.querySelector(".seg").onclick = e => { const b = e.target.closest("[data-occ]"); if (!b) return; GEN.occ = b.dataset.occ; plan.querySelectorAll("[data-occ]").forEach(x => x.setAttribute("aria-pressed", x === b)); GEN.seen = []; guard(generate)(); };
  FX.vmap($("#vmap"), ins.sites, it => { location.hash = "#/item/" + it.id; });
  FX.after(main); renderWx(); if (GEN.list.length) renderGen(); else await generate();
}
const greeting = (d, name) => { const h = d.getHours(), p = h >= 5 && h < 12 ? "Good morning" : h >= 12 && h < 17 ? "Good afternoon" : "Good evening";
  return name ? `${p}, <em>${esc(name)}.</em>` : `${p.split(" ")[0]} <em>${p.split(" ")[1]}.</em>`; };
const DAY_LINES = ["Here’s what your wardrobe suggests today.", "A fresh look from clothes you already own.", "Let’s find something that feels like you.", "Your wardrobe, rearranged for today.", "Dress for the day you’re actually having.", "Style more, buy less.", "Worth wearing again."];
const dayLine = d => DAY_LINES[(d.getFullYear() * 366 + Math.floor((d - new Date(d.getFullYear(), 0, 0)) / 864e5)) % DAY_LINES.length];

/* ---------- Welcome ---------- */

/* ---------- Wardrobe ---------- */
async function pageWardrobe(_, q) {
  const f = { q: "", category: "", color: "", brand: "", style: "", occasion: "", season: "", favorite: "", status: "", sort: "recent", unworn_days: "", palette: "", min_formality: "", page: 1, ...q };
  const QUICK = [["All", {}], ["Favourites", { favorite: "true" }], ["Not worn in 30 days", { unworn_days: "30" }], ["Neutrals", { palette: "neutral" }], ["Colour", { palette: "colour" }], ["Dressy", { min_formality: "4" }], ["Work", { occasion: "work" }], ["In laundry", { status: "laundry" }]];
  const QK = ["favorite", "unworn_days", "palette", "min_formality", "occasion", "status"];
  const isOn = o => QK.every(k => (o[k] ?? "") === (Object.keys(o).length ? f[k] : "")) || false;
  const fac = await api("/facets");
  let draw = async () => {
    const p = new URLSearchParams(Object.entries(f).filter(([, v]) => v !== "" && v !== false));
    const r = await api("/items?" + p);
    $("#res").innerHTML = r.items.length ? `<div class="grid">${r.items.map(card).join("")}</div><div class="pager"><button class="btn sm" id="pv" ${r.page <= 1 ? "disabled" : ""}>Previous</button><span class="muted">Page ${r.page} of ${r.pages} · ${r.total} items</span><button class="btn sm" id="nx" ${r.page >= r.pages ? "disabled" : ""}>Next</button></div>`
      : `<div class="empty"><h3>No items match</h3><p>Try removing a filter, or add something new.</p><a class="btn" href="#/add">Add an item</a></div>`;
    if (r.items.length) { $("#pv").onclick = () => { f.page--; draw(); }; $("#nx").onclick = () => { f.page++; draw(); }; }
  };
  main.innerHTML = `<h1>My wardrobe</h1><div class="chips" style="margin:1rem 0"><a class="chip ${f.category ? "" : "on"}" href="#/wardrobe">All</a>${CATS.map(c => `<a class="chip ${f.category === c.id ? "on" : ""}" href="#/wardrobe?category=${c.id}">${esc(c.label)}</a>`).join("")}</div>
  <div class="quick" id="quick" role="group" aria-label="Quick filters">${QUICK.map(([l, o], k) => `<button type="button" class="chip" data-q="${k}" aria-pressed="false">${l}</button>`).join("")}</div>
  <div class="bar" id="flt"><label>Search<input name="q" value="${esc(f.q)}" placeholder="Name, brand…"></label>
  <label>Colour<select name="color">${opts(fac.colors, f.color, "Any")}</select></label><label>Brand<input name="brand" value="${esc(f.brand)}" list="brands"></label><datalist id="brands">${fac.brands.map(b => `<option value="${esc(b)}">`).join("")}</datalist>
  <label>Style<select name="style">${opts(STYLES, f.style, "Any")}</select></label><label>Occasion<select name="occasion">${opts(OCC, f.occasion, "Any")}</select></label>
  <label>Show<select name="favorite"><option value="">All</option><option value="true" ${f.favorite === "true" ? "selected" : ""}>Favourites</option></select></label>
  <label>Status<select name="status">${opts(["available", "laundry", "retired"], f.status, "Any")}</select></label>
  <label>Sort<select name="sort"><option value="recent">Recently added</option><option value="name" ${f.sort === "name" ? "selected" : ""}>Name</option><option value="most_worn" ${f.sort === "most_worn" ? "selected" : ""}>Most worn</option><option value="least_worn" ${f.sort === "least_worn" ? "selected" : ""}>Least worn</option></select></label></div><div id="res"></div>`;
  const syncQuick = () => document.querySelectorAll("#quick [data-q]").forEach(b => { const o = QUICK[+b.dataset.q][1], on = Object.keys(o).length ? Object.entries(o).every(([k, v]) => f[k] === v) && QK.filter(k => !(k in o)).every(k => !f[k]) : QK.every(k => !f[k]); b.setAttribute("aria-pressed", on); b.classList.toggle("on", on); });
  $("#quick").onclick = e => { const b = e.target.closest("[data-q]"); if (!b) return; QK.forEach(k => f[k] = ""); Object.assign(f, QUICK[+b.dataset.q][1]); f.page = 1;
    $("#flt").querySelectorAll("select,input").forEach(x => { if (x.name in f) x.value = f[x.name]; }); syncQuick(); guard(draw)(); };
  const _draw = draw; draw = async () => { await _draw(); syncQuick(); };
  let t; $("#flt").addEventListener("input", e => { f[e.target.name] = e.target.value; f.page = 1; clearTimeout(t); t = setTimeout(guard(draw), 250); });
  await draw();
}

/* ---------- Item form (add + edit) ---------- */
function itemForm(it = {}) {
  return `<form class="f" id="form">
  <div class="wide photo"><div><div class="ph" id="prev">${it.image_url ? `<img src="${esc(it.image_url)}" alt="">` : '<div class="noimg">No photo yet</div>'}</div></div>
    <div><p class="muted" style="margin-top:0">Photo (JPEG, PNG or WebP, up to 8 MB)</p><div class="row"><label class="btn sm">Upload photo<input type="file" id="file" accept="image/*" hidden></label><label class="btn sm">Take photo<input type="file" id="cam" accept="image/*" capture="environment" hidden></label></div>
    <p id="detect" class="muted"></p></div></div>
  ${it.id ? "" : `<div class="wide"><label>Import from a product link (optional)<span class="row"><input id="url" style="flex:1" placeholder="https://…"><button type="button" class="btn sm" id="imp">Fetch details</button></span></label><small id="impmsg">Some shops block automatic import. If it fails, fill in the details yourself.</small></div>`}
  <label>Item name *<input name="name" required maxlength="120" value="${esc(it.name)}"></label>
  <label>Category *<select name="category" required>${CATS.map(c => `<option value="${c.id}" ${c.id === it.category ? "selected" : ""}>${esc(c.label)}</option>`).join("")}</select></label>
  <label>Subcategory<input name="subcategory" value="${esc(it.subcategory)}" placeholder="e.g. Oxford, hoodie"></label>
  <label>Primary colour<input name="primary_color" list="colors" value="${esc(it.primary_color)}"></label><datalist id="colors">${COLORS.map(c => `<option value="${c}">`).join("")}</datalist>
  <label>Other colours (comma separated)<input name="secondary_colors" value="${esc((it.secondary_colors || []).join(", "))}"></label>
  <label>Pattern<select name="pattern">${opts(PATTERNS, it.pattern || "solid")}</select></label>
  <label>Brand<input name="brand" value="${esc(it.brand)}"></label><label>Price<input name="price" type="number" min="0" step="0.01" value="${it.price ?? ""}"></label>
  <label>Product URL<input name="product_url" type="url" value="${esc(it.product_url)}"></label>
  <label>Style<select name="style">${opts(STYLES, it.style, "Not set")}</select></label>
  <label>Formality <output id="fo">${FORMAL[it.formality || 3]}</output><input name="formality" type="range" min="1" max="5" value="${it.formality || 3}"></label>
  <label>Status<select name="status">${["available", "laundry", "retired"].map(s => `<option value="${s}" ${s === (it.status || "available") ? "selected" : ""}>${{ available: "Available", laundry: "In laundry", retired: "No longer owned" }[s]}</option>`).join("")}</select></label>
  <div class="wide"><label>Occasions</label>${checks("occasions", OCC, it.occasions)}</div><div class="wide"><label>Climate it suits <small>(used with destination weather: winter = cold, autumn = cool, spring = mild, summer = hot)</small></label>${checks("seasons", SEASONS, it.seasons)}</div>
  <label class="wide" style="flex-direction:row;align-items:center;gap:.5rem"><input type="checkbox" name="favorite" ${it.favorite ? "checked" : ""}> Favourite</label>
  <label class="wide">Description<textarea name="description" maxlength="2000">${esc(it.description)}</textarea></label>
  <label class="wide">Notes<textarea name="notes" maxlength="2000">${esc(it.notes)}</textarea></label>
  <div class="wide row"><button class="btn primary" type="submit">${it.id ? "Save changes" : "Add to wardrobe"}</button>${it.id ? '<button type="button" class="btn danger" id="del">Delete item</button>' : ""}<span id="ferr" class="err"></span></div></form>`;
}
function bindForm(it, onSaved) {
  const form = $("#form"); let image = it.image || null;
  form.elements.formality.oninput = () => $("#fo").textContent = FORMAL[form.elements.formality.value];
  const fromData = d => { image = d.image; $("#prev").innerHTML = `<img src="${esc(d.image_url)}" alt="">`; if (d.suggested_color) { $("#detect").innerHTML = `Detected colour (automatic suggestion): <b>${esc(d.suggested_color)}</b> <button type="button" class="link" id="usec">Use it</button>`; $("#usec").onclick = () => form.elements.primary_color.value = d.suggested_color; if (!form.elements.primary_color.value) form.elements.primary_color.value = d.suggested_color; } };
  const up = guard(async e => { const f = e.target.files[0]; if (!f) return; const fd = new FormData(); fd.append("file", f); fromData(await api("/uploads", { method: "POST", body: fd })); });
  $("#file").onchange = up; $("#cam").onchange = up;
  if ($("#imp")) $("#imp").onclick = guard(async () => {
    const b = $("#imp"); b.disabled = true; $("#impmsg").textContent = "Fetching…";
    try {
      const r = await api("/import-url", { method: "POST", body: { url: $("#url").value } });
      if (!r.ok) { $("#impmsg").textContent = r.error + " You can still add this item manually."; return; }
      for (const [k, v] of Object.entries(r.fields)) if (form.elements[k] && v) form.elements[k].value = v;
      if (r.image) fromData(r);
      $("#impmsg").textContent = ["Imported what was available — please check every field.", ...r.warnings].join(" ");
    } finally { b.disabled = false; }
  });
  form.onsubmit = guard(async e => {
    e.preventDefault(); $("#ferr").textContent = "";
    const v = n => form.elements[n].value;
    const body = { name: v("name"), category: v("category"), subcategory: v("subcategory"), primary_color: v("primary_color"), pattern: v("pattern"), brand: v("brand"),
      product_url: v("product_url"), price: v("price") === "" ? null : +v("price"), description: v("description"), style: v("style"), formality: +v("formality"), status: v("status"),
      notes: v("notes"), favorite: form.elements.favorite.checked, occasions: checked(form, "occasions"), seasons: checked(form, "seasons"),
      secondary_colors: v("secondary_colors").split(",").map(s => s.trim()).filter(Boolean), image };
    try { const saved = it.id ? await api(`/items/${it.id}`, { method: "PATCH", body }) : await api("/items", { method: "POST", body }); toast(it.id ? "Changes saved" : "Added to your wardrobe"); onSaved(saved); }
    catch (err) { $("#ferr").textContent = err.message; }
  });
  if ($("#del")) $("#del").onclick = guard(async () => { if (!confirm(`Delete “${it.name}”? Saved outfits that use it will lose this piece.`)) return; await api(`/items/${it.id}`, { method: "DELETE" }); toast("Item deleted"); location.hash = "#/wardrobe"; });
}
async function pageAdd() { document.body.dataset.page = "add"; main.innerHTML = `<h1>Add an item</h1><p class="muted">Upload or take a photo, import from a link, or just type the details.</p>${itemForm()}`; bindForm({}, s => location.hash = `#/item/${s.id}`); }
async function pageItem(id) {
  document.body.dataset.page = "item"; const it = await api(`/items/${id}`);
  main.innerHTML = `<p><a href="#/wardrobe">← Wardrobe</a></p><div class="row between"><h1>${esc(it.name)}</h1><div class="row"><button class="btn sm" id="fav">${it.favorite ? "♥ Favourite" : "♡ Mark favourite"}</button></div></div>
  <p class="muted">${esc(it.category_label)} · worn ${it.wear_count} time${it.wear_count === 1 ? "" : "s"}${it.last_worn ? ", last on " + esc(it.last_worn) : ""}${it.is_demo ? " · Demo item" : ""}</p>${itemForm(it)}`;
  bindForm(it, () => route());
  $("#fav").onclick = guard(async () => { await api(`/items/${id}`, { method: "PATCH", body: { favorite: !it.favorite } }); route(); });
}

/* ---------- Saved outfits ---------- */
let OUTFIT = null;
async function pageOutfits() {
  const list = await api("/outfits");
  main.innerHTML = `<h1>Saved outfits</h1>${list.length ? `<div class="grid" style="margin-top:1.2rem">${list.map(o => `<a class="card" href="#/outfit/${o.id}"><div class="ph">${img(o.items[0] || {})}</div><div class="meta"><b>${esc(o.name || "Outfit " + o.id)}${o.favorite ? " ♥" : ""}</b><span>${o.items.length} pieces · worn ${o.wear_count}×${o.all_available ? "" : " · needs attention"}</span></div></a>`).join("")}</div>` : '<div class="empty"><h3>No saved outfits yet</h3><p>Generate an outfit on Today and choose Save.</p><a class="btn" href="#/">Get an outfit</a></div>'}`;
}
function renderOutfit() {
  const o = OUTFIT, today = iso(new Date());
  main.innerHTML = `<p><a href="#/outfits">← Saved outfits</a></p><div class="row between"><h1>${esc(o.name || "Outfit " + o.id)}</h1><button class="btn sm" id="ofav">${o.favorite ? "♥ Favourite" : "♡ Mark favourite"}</button></div>
  ${o.all_available ? "" : '<p class="err">Some pieces are in laundry or no longer owned. Swap them to keep this outfit usable.</p>'}${outfitCard(o, 0, false, { saved: true })}
  <form class="f" id="of"><label>Name<input name="name" value="${esc(o.name)}" maxlength="120"></label><label>Plan or log for<input type="date" name="date" value="${today}"></label>
  <label class="wide">Notes<textarea name="notes">${esc(o.notes)}</textarea></label>
  <div class="wide row"><button class="btn primary" type="submit">Save notes</button><button type="button" class="btn" id="plan">Plan for date</button><button type="button" class="btn" id="wore">Mark as worn on date</button><button type="button" class="btn" id="copy">Copy summary</button><button type="button" class="btn danger" id="odel">Delete</button></div></form>`;
  const f = $("#of");
  $("#ofav").onclick = guard(async () => { OUTFIT = await api(`/outfits/${o.id}`, { method: "PATCH", body: { favorite: !o.favorite } }); renderOutfit(); });
  f.onsubmit = guard(async e => { e.preventDefault(); OUTFIT = await api(`/outfits/${o.id}`, { method: "PATCH", body: { name: f.elements.name.value, notes: f.elements.notes.value } }); toast("Saved"); renderOutfit(); });
  $("#plan").onclick = guard(async () => { await api("/calendar", { method: "POST", body: { date: f.elements.date.value, outfit_id: o.id } }); toast("Added to planner"); });
  $("#wore").onclick = guard(async () => { await api(`/outfits/${o.id}/wear`, { method: "POST", body: { date: f.elements.date.value } }); OUTFIT = await api(`/outfits/${o.id}`); toast("Logged as worn"); renderOutfit(); });
  $("#copy").onclick = guard(async () => { await navigator.clipboard.writeText(`${o.name || "Outfit"} (OFTLY)\n` + o.items.map(i => `- ${i.name} (${i.category_label}${i.primary_color ? ", " + i.primary_color : ""})`).join("\n") + (o.notes ? `\nNotes: ${o.notes}` : "")); toast("Summary copied"); });
  $("#odel").onclick = guard(async () => { if (confirm("Delete this saved outfit? Its planner entries will be removed too.")) { await api(`/outfits/${o.id}`, { method: "DELETE" }); location.hash = "#/outfits"; } });
}
async function pageOutfit(id) { document.body.dataset.page = "outfit"; OUTFIT = await api(`/outfits/${id}`); renderOutfit(); }

/* ---------- Planner ---------- */
const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
async function pagePlanner(_, q) {
  document.body.dataset.page = "planner";
  const base = q.w ? new Date(q.w + "T00:00:00") : new Date(); const start = addDays(base, -((base.getDay() + 6) % 7)), end = addDays(start, 6);
  const [cal, outfits, hist] = await Promise.all([api(`/calendar?start=${iso(start)}&end=${iso(end)}`), api("/outfits"), api("/history?days=60")]);
  const mini = o => `<div class="minis">${o.items.map(i => i.image_url ? `<img src="${esc(i.image_url)}" alt="${esc(i.name)}" title="${esc(i.name)}">` : "").join("")}</div>`;
  main.innerHTML = `<div class="row between"><h1>Planner</h1><div class="row"><a class="btn sm" href="#/planner?w=${iso(addDays(start, -7))}">Previous week</a><a class="btn sm" href="#/planner">This week</a><a class="btn sm" href="#/planner?w=${iso(addDays(start, 7))}">Next week</a></div></div>
  <div class="week" style="margin-top:1.2rem">${[...Array(7)].map((_, k) => { const d = addDays(start, k), key = iso(d), es = cal.filter(e => e.date === key);
    return `<div class="day ${key === iso(new Date()) ? "today" : ""}"><b>${d.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })}</b>
    ${es.map(e => `<div class="entry"><a href="#/outfit/${e.outfit_id}">${esc(e.outfit.name || "Outfit " + e.outfit_id)}</a>${mini(e.outfit)}<div class="row"><button class="link" data-act="worn" data-id="${e.id}" data-v="${e.worn ? 0 : 1}">${e.worn ? "Worn ✓ (undo)" : "Mark worn"}</button><button class="link" data-act="unplan" data-id="${e.id}">Remove</button></div></div>`).join("")}
    ${outfits.length ? `<div class="row" style="margin-top:.5rem"><select id="s${key}" aria-label="Outfit for ${key}">${outfits.map(o => `<option value="${o.id}">${esc(o.name || "Outfit " + o.id)}</option>`).join("")}</select><button class="btn sm" data-act="plan" data-d="${key}">Plan</button></div>` : '<small>Save an outfit to plan it.</small>'}</div>`; }).join("")}</div>
  <h2>Recently worn</h2>${hist.entries.length ? hist.entries.slice(0, 12).map(e => `<div class="entry"><b>${esc(e.date)}</b> · <a href="#/outfit/${e.outfit_id}">${esc(e.outfit.name || "Outfit " + e.outfit_id)}</a> ${e.repeat_of ? `<span class="badge warn">Repeat of ${esc(e.repeat_of)}</span>` : ""}${e.recent_items.length ? `<span class="badge">Re-worn this week: ${esc(e.recent_items.join(", "))}</span>` : ""}${mini(e.outfit)}</div>`).join("") : '<p class="muted">Nothing logged yet. Mark an outfit as worn to build your history.</p>'}
  <h2>Give these a turn</h2><p class="muted">Available pieces not worn in the last 30 days.</p>${hist.rotation.not_worn_recently.length ? `<div class="grid">${hist.rotation.not_worn_recently.map(card).join("")}</div>` : '<p class="muted">Everything has had a recent outing.</p>'}`;
}
Object.assign(ACTIONS, {
  async worn({ id, v }) { await api(`/calendar/${id}`, { method: "PATCH", body: { worn: v === "1" } }); route(); },
  async unplan({ id }) { await api(`/calendar/${id}`, { method: "DELETE" }); route(); },
  async plan({ d }) { await api("/calendar", { method: "POST", body: { date: d, outfit_id: +$(`#s${d}`).value } }); toast("Planned"); route(); },
});

/* ---------- Settings ---------- */
async function pageSettings() {
  document.body.dataset.page = "settings"; PREFS = await api("/preferences");
  main.innerHTML = `<h1>Settings</h1>${accountSection()}<h2>Accessibility</h2><p class="muted" style="max-width:60ch">Presets for vision, colour vision, reading, movement and comfort, plus fine-tuning. Reopen it here whenever you like (keyboard shortcut: Alt + A).</p><div class="row" style="margin:.8rem 0 1.4rem"><button class="btn primary" type="button" id="open-a11y2">Open accessibility settings</button></div>
  <h2>About you</h2><form class="f" id="pf" style="margin-top:1.2rem">
  <label>Preferred name<input name="preferred_name" maxlength="80" autocomplete="given-name" value="${esc(PREFS.preferred_name)}"></label>
  <label>Gender <small>(optional)</small><select name="gender">${[["", "Skip"], ["woman", "Woman"], ["man", "Man"], ["non-binary", "Non-binary"], ["self-describe", "Prefer to self-describe"], ["prefer-not-to-say", "Prefer not to say"]].map(([v, l]) => `<option value="${v}" ${PREFS.gender === v ? "selected" : ""}>${l}</option>`).join("")}</select></label>
  <label>Preferred fit<select name="fit">${[["", "No preference"], ["relaxed", "Relaxed"], ["regular", "Regular"], ["fitted", "Fitted"]].map(([v, l]) => `<option value="${v}" ${PREFS.fit === v ? "selected" : ""}>${l}</option>`).join("")}</select></label>
  <label>City <small>(for weather)</small><input name="city" maxlength="80" autocomplete="address-level2" value="${esc(PREFS.city)}"></label>
  <label class="chip wide"><input type="checkbox" name="use_weather" ${PREFS.use_weather ? "checked" : ""}>Use weather for suggestions — sends only my city name to Open-Meteo (off by default)</label>
  <label class="wide">Colours I avoid (comma separated)<input name="disliked_colors" list="colors" value="${esc(PREFS.disliked_colors.join(", "))}"></label>
  <div class="wide"><label>Preferred styles</label>${checks("preferred_styles", STYLES, PREFS.preferred_styles)}</div>
  <label class="wide">Favourite colours (comma separated)<input name="favorite_colors" list="colors" value="${esc(PREFS.favorite_colors.join(", "))}"></label><datalist id="colors">${COLORS.map(c => `<option value="${c}">`).join("")}</datalist>
  <div class="wide"><label>Preferred occasions</label>${checks("preferred_occasions", OCC, PREFS.preferred_occasions)}</div>
  <label>Default occasion<select name="default_occasion">${opts(OCC, PREFS.default_occasion, "Any")}</select></label>
  <div class="wide"><label>Clothing categories I use</label><div class="chips">${CATS.map(c => `<label class="chip"><input type="checkbox" name="preferred_categories" value="${c.id}" ${PREFS.preferred_categories.includes(c.id) ? "checked" : ""}>${esc(c.label)}</label>`).join("")}</div></div>
  <div class="wide"><button class="btn primary">Save preferences</button></div></form>
  <h2>Your data</h2><div class="row"><a class="btn" href="/api/export" download>Export data (JSON)</a><a class="btn" href="/api/export/backup" download>Backup (database + photos)</a>${CFG.demo_enabled ? '<button class="btn" id="rdemo">Remove sample items</button><button class="btn" data-act="demo">Load sample items (testing only)</button>' : ""}<button class="btn danger" id="wipe">Delete all my data</button></div>
  <h2>About OFTLY</h2><p class="muted" style="max-width:60ch">Your Wardrobe. Reimagined. Style More. Buy Less.<br>OFTLY runs on this computer. Photos and data are stored locally, nothing is sent to AI services, and there is no tracking. Outfit suggestions come from a transparent rule-based engine (colour harmony, formality, occasion, season, your preferences and wear history). Automatic colour detection from photos is only a suggestion — you confirm it.</p>`;
  const f = $("#pf");
  f.onsubmit = guard(async e => { e.preventDefault(); const v = n => f.elements[n].value;
    PREFS = await api("/preferences", { method: "PUT", body: { preferred_styles: checked(f, "preferred_styles"), preferred_occasions: checked(f, "preferred_occasions"), preferred_categories: checked(f, "preferred_categories"), favorite_colors: v("favorite_colors").split(",").map(s => s.trim().toLowerCase()).filter(Boolean), default_occasion: v("default_occasion"),
      preferred_name: v("preferred_name").trim(), gender: v("gender"), fit: v("fit"), city: v("city").trim(), use_weather: f.elements.use_weather.checked,
      disliked_colors: v("disliked_colors").split(",").map(s => s.trim().toLowerCase()).filter(Boolean) } });
    GEN = { list: [], seen: [], occ: "", dest: "", day: 0, msg: "", weather: null }; toast("Preferences saved"); });
  $("#open-a11y2").onclick = () => OFTLYA11y.open(); wireAccount();
  if ($("#rdemo")) $("#rdemo").onclick = guard(async () => { if (confirm("Remove all demo items?")) { const r = await api("/demo", { method: "DELETE" }); GEN.list = []; toast(`Removed ${r.removed} demo items`); } });
  $("#wipe").onclick = guard(async () => { if (prompt("This permanently deletes every item, outfit and photo. Type DELETE to confirm.") === "DELETE") { await api("/data?confirm=true", { method: "DELETE" }); GEN = { list: [], seen: [], occ: "", season: "", msg: "" }; PREFS = await api("/preferences"); toast("All data deleted"); location.hash = "#/"; } });
}

addEventListener("online", () => $("#offline").hidden = true); addEventListener("offline", () => $("#offline").hidden = false);
(async () => {
  if (!navigator.onLine) $("#offline").hidden = false;
  CFG = { ...CFG, ...(await api("/auth/config").catch(() => ({}))) };
  SESSION = await api("/auth/me").catch(() => null);
  if (SESSION) { CATS = await api("/categories"); PREFS = await api("/preferences"); document.body.dataset.auth = "in"; } else document.body.dataset.auth = "out";
  route();
})().catch(e => { main.innerHTML = `<div class="empty"><h2>Can’t reach OFTLY</h2><p>${esc(e.message)}</p><button class="btn" onclick="location.reload()">Try again</button></div>`; });
