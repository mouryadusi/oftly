/* Veya frontend: dependency-free single-page app (hash routing). All user text goes through esc(). */
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
let GEN = { list: [], seen: [], occ: "", season: "", msg: "" };

async function api(path, opts = {}) {
  const isForm = opts.body instanceof FormData;
  const r = await fetch("/api" + path, { ...opts, headers: opts.body && !isForm ? { "Content-Type": "application/json" } : {},
    body: opts.body && !isForm ? JSON.stringify(opts.body) : opts.body });
  if (!r.ok) {
    let m = r.statusText;
    try { const j = await r.json(); m = Array.isArray(j.detail) ? j.detail.map(d => `${(d.loc || []).slice(-1)[0] || ""} ${d.msg}`).join("; ") : (j.detail || m); } catch {}
    throw new Error(m);
  }
  return r.status === 204 ? null : r.json();
}
let toastT;
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("show"), 3200); }
const guard = fn => async (...a) => { try { await fn(...a); } catch (e) { toast(e.message); } };
const catLabel = id => (CATS.find(c => c.id === id) || {}).label || id;
const img = (i, cls = "") => i.image_url ? `<img loading="lazy" src="${esc(i.image_url)}" alt="${esc(i.name)}">` : `<div class="noimg">${esc(i.category_label || "No photo")}</div>`;
const card = i => `<a class="card" href="#/item/${i.id}"><div class="ph">${img(i)}${i.favorite ? '<span class="fav" aria-label="Favourite">♥</span>' : ""}${i.is_demo ? '<span class="demo">Demo</span>' : ""}${i.status !== "available" ? `<span class="stat">${esc(i.status)}</span>` : ""}</div><div class="meta"><b>${esc(i.name)}</b><span>${esc(i.category_label)}${i.primary_color ? " · " + esc(i.primary_color) : ""}</span></div></a>`;
const opts = (list, sel, blank) => (blank !== undefined ? `<option value="">${esc(blank)}</option>` : "") + list.map(v => `<option value="${esc(v)}" ${v === sel ? "selected" : ""}>${esc(cap(v))}</option>`).join("");
const checks = (name, list, sel = []) => `<div class="chips">${list.map(v => `<label class="chip"><input type="checkbox" name="${name}" value="${esc(v)}" ${sel.includes(v) ? "checked" : ""}>${esc(cap(v))}</label>`).join("")}</div>`;
const checked = (root, name) => [...root.querySelectorAll(`input[name=${name}]:checked`)].map(i => i.value);
const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

/* ---------- router ---------- */
const pages = { today: pageToday, wardrobe: pageWardrobe, item: pageItem, add: pageAdd, outfits: pageOutfits, outfit: pageOutfit, planner: pagePlanner, settings: pageSettings, welcome: pageWelcome };
async function route() {
  const [path, qs] = (location.hash.slice(1) || "/").split("?");
  const [name = "today", arg] = path.split("/").filter(Boolean);
  document.querySelectorAll("[data-nav]").forEach(a => a.classList.toggle("on", a.dataset.nav === (["item", "add"].includes(name) ? "wardrobe" : name === "outfit" ? "outfits" : name)));
  main.innerHTML = '<p class="muted">Loading…</p>';
  try { await (pages[name] || pageToday)(arg, Object.fromEntries(new URLSearchParams(qs || ""))); }
  catch (e) { main.innerHTML = `<div class="empty"><h2>That didn’t load</h2><p>${esc(e.message)}</p><a class="btn" href="#/">Back to today</a></div>`; }
  window.scrollTo(0, 0);
}
addEventListener("hashchange", route);
main.addEventListener("click", e => { const b = e.target.closest("[data-act]"); if (b) guard(ACTIONS[b.dataset.act])(b.dataset, b); });

/* ---------- modal ---------- */
function modal(html) { const d = $("#dlg"); d.innerHTML = html; d.showModal(); return d; }

/* ---------- outfit component ---------- */
const outfitCard = (o, i, alt = false, opt = {}) => `<article class="outfit ${alt ? "alt" : ""}" data-i="${i}">
  <div class="o-items">${o.items.map(it => `<div class="o-item"><a href="#/item/${it.id}"><div class="ph">${img(it)}</div></a><div class="o-meta"><span>${esc(it.name)}</span><button class="link" data-act="swap" data-i="${i}" data-id="${it.id}" aria-label="Swap ${esc(it.name)}">Swap</button></div></div>`).join("")}</div>
  <div class="o-foot"><div>${o.score != null ? `<span class="score">${Math.round(o.score)}</span><small> / 100 match</small>` : ""}<p class="why">${esc(o.reason || "")}</p></div>
  <div class="row">${opt.saved ? "" : `<button class="btn sm" data-act="reject" data-i="${i}">Not for me</button><button class="btn sm" data-act="save" data-i="${i}">Save</button><button class="btn sm primary" data-act="wearnew" data-i="${i}">Wear today</button>`}</div></div></article>`;

function ctxOf(o) { return { item_ids: o.item_ids, occasion: GEN.occ, season: GEN.season }; }
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
const evaluate = (ids, ctx) => api("/outfits/evaluate", { method: "POST", body: { item_ids: ids, occasion: ctx.occasion, season: ctx.season } });

const ACTIONS = {
  async swap({ i, id }) {
    if (document.body.dataset.page === "outfit") { const o = OUTFIT; return swapFlow(o, +id, {item_ids: o.item_ids}, async ids => { OUTFIT = await api(`/outfits/${o.id}`, { method: "PATCH", body: { item_ids: ids } }); renderOutfit(); toast("Swapped and saved"); }); }
    const o = GEN.list[+i];
    await swapFlow(o, +id, ctxOf(o), async ids => { GEN.list[+i] = await evaluate(ids, GEN); renderGen(); });
  },
  async save({ i }) { const s = await api("/outfits", { method: "POST", body: { item_ids: GEN.list[+i].item_ids, score: GEN.list[+i].score, reason: GEN.list[+i].reason } }); toast("Saved to Outfits"); return s; },
  async reject({ i }) {
    const o = GEN.list[+i]; await api("/feedback", { method: "POST", body: { item_ids: o.item_ids, action: "reject" } });
    GEN.list.splice(+i, 1); GEN.list.length ? renderGen() : await generate();
  },
  async wearnew({ i }) { const o = GEN.list[+i]; const s = await api("/outfits", { method: "POST", body: { item_ids: o.item_ids, score: o.score, reason: o.reason } }); await api(`/outfits/${s.id}/wear`, { method: "POST", body: {} }); toast("Logged as worn today"); },
  async more() { await generate(); },
  async demo() { await api("/demo", { method: "POST" }); await api("/preferences", { method: "PUT", body: { onboarded: true } }); PREFS.onboarded = true; toast("Demo wardrobe loaded"); location.hash = "#/"; route(); },
};

/* ---------- Today ---------- */
async function generate(retry) {
  const p = new URLSearchParams({ count: 3, seed: Math.floor(Math.random() * 1e9), occasion: GEN.occ, season: GEN.season });
  if (GEN.seen.length && !retry) p.set("exclude", GEN.seen.join(";"));
  const r = await api("/outfits/generate?" + p);
  if (!r.outfits.length && GEN.seen.length && !retry) { GEN.seen = []; return generate(true); }
  GEN.list = r.outfits; GEN.msg = r.message; r.outfits.forEach(o => GEN.seen.push(o.signature)); renderGen();
}
function renderGen() {
  const el = $("#gen"); if (!el) return;
  if (!GEN.list.length) { el.innerHTML = `<div class="empty"><h3>No outfit to suggest yet</h3><p>${esc(GEN.msg)}</p><a class="btn" href="#/add">Add an item</a></div>`; return; }
  el.innerHTML = `<h2>Today’s outfit</h2>${outfitCard(GEN.list[0], 0)}${GEN.list.length > 1 ? `<h2>Alternatives</h2>${GEN.list.slice(1).map((o, k) => outfitCard(o, k + 1, true)).join("")}` : ""}${GEN.msg ? `<p class="muted">${esc(GEN.msg)}</p>` : ""}`;
}
async function pageToday() {
  document.body.dataset.page = "today";
  const [sum, recent, saved] = await Promise.all([api("/summary"), api("/items?sort=recent&page_size=6"), api("/outfits")]);
  if (!sum.total && !PREFS.onboarded) { location.hash = "#/welcome"; return; }
  const now = new Date(), h = now.getHours();
  const head = `<div class="hero"><h1>${h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"}.</h1><p>${now.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</p></div>`;
  if (!sum.total) { main.innerHTML = head + `<div class="empty"><h3>Your wardrobe is empty</h3><p>Add a few shirts, bottoms and shoes and Veya will start suggesting outfits.</p><div class="row" style="justify-content:center"><a class="btn primary" href="#/add">Add your first item</a><button class="btn" data-act="demo">Try the demo wardrobe</button></div></div>`; return; }
  if (!GEN.occ && GEN.occ !== PREFS.default_occasion && !GEN.init) { GEN.occ = PREFS.default_occasion || ""; GEN.season = PREFS.default_season || ""; GEN.init = true; }
  main.innerHTML = `${head}<div class="bar"><label>Occasion<select id="occ">${opts(OCC, GEN.occ, "Any")}</select></label><label>Season<select id="sea">${opts(SEASONS, GEN.season, "Any")}</select></label><button class="btn primary" data-act="more">Another outfit</button></div>
  <div id="gen"></div>
  <h2>Browse by category</h2><div class="chips">${CATS.map(c => `<a class="chip" href="#/wardrobe?category=${c.id}">${esc(c.label)}${sum.by_category[c.id] ? ` (${sum.by_category[c.id]})` : ""}</a>`).join("")}</div>
  <h2>Recently added</h2><div class="grid">${recent.items.map(card).join("")}</div>
  <h2>Saved outfits</h2>${saved.length ? `<div class="grid">${saved.slice(0, 4).map(o => `<a class="card" href="#/outfit/${o.id}"><div class="ph">${img(o.items[0] || {})}</div><div class="meta"><b>${esc(o.name || "Outfit " + o.id)}</b><span>${o.items.length} pieces</span></div></a>`).join("")}</div>` : '<p class="muted">Nothing saved yet. Save an outfit you like and it will appear here.</p>'}
  <h2>Wardrobe summary</h2><div class="stats"><div><b>${sum.total}</b>items</div><div><b>${sum.available}</b>available</div><div><b>${sum.laundry}</b>in laundry</div><div><b>${sum.favorites}</b>favourites</div><div><b>${sum.saved_outfits}</b>saved outfits</div></div>`;
  $("#occ").onchange = e => { GEN.occ = e.target.value; GEN.seen = []; guard(generate)(); };
  $("#sea").onchange = e => { GEN.season = e.target.value; GEN.seen = []; guard(generate)(); };
  if (GEN.list.length) renderGen(); else await generate();
}

/* ---------- Welcome ---------- */
async function pageWelcome() {
  main.innerHTML = `<div class="hero" style="max-width:640px;margin:3rem auto"><h1>Your Wardrobe. Reimagined.</h1><p>Style more, buy less. Veya turns the clothes you already own into outfits for every day. Everything stays on this computer.</p>
  <h3 style="margin-top:1.5rem">What do you wear most?</h3><div class="chips">${CATS.map(c => `<label class="chip"><input type="checkbox" name="pc" value="${c.id}" ${(PREFS.preferred_categories || []).includes(c.id) ? "checked" : ""}>${esc(c.label)}</label>`).join("")}</div>
  <div class="row" style="margin-top:1.5rem"><button class="btn primary" id="go">Add my first item</button><button class="btn" data-act="demo">Try the demo wardrobe</button><button class="btn" id="skip">Skip</button></div></div>`;
  const done = async dest => { await api("/preferences", { method: "PUT", body: { onboarded: true, preferred_categories: checked(main, "pc") } }); PREFS.onboarded = true; location.hash = dest; };
  $("#go").onclick = guard(() => done("#/add")); $("#skip").onclick = guard(() => done("#/"));
}

/* ---------- Wardrobe ---------- */
async function pageWardrobe(_, q) {
  const f = { q: "", category: "", color: "", brand: "", style: "", occasion: "", season: "", favorite: "", status: "", sort: "recent", page: 1, ...q };
  const fac = await api("/facets");
  const draw = async () => {
    const p = new URLSearchParams(Object.entries(f).filter(([, v]) => v !== "" && v !== false));
    const r = await api("/items?" + p);
    $("#res").innerHTML = r.items.length ? `<div class="grid">${r.items.map(card).join("")}</div><div class="pager"><button class="btn sm" id="pv" ${r.page <= 1 ? "disabled" : ""}>Previous</button><span class="muted">Page ${r.page} of ${r.pages} · ${r.total} items</span><button class="btn sm" id="nx" ${r.page >= r.pages ? "disabled" : ""}>Next</button></div>`
      : `<div class="empty"><h3>No items match</h3><p>Try removing a filter, or add something new.</p><a class="btn" href="#/add">Add an item</a></div>`;
    if (r.items.length) { $("#pv").onclick = () => { f.page--; draw(); }; $("#nx").onclick = () => { f.page++; draw(); }; }
  };
  main.innerHTML = `<h1>My wardrobe</h1><div class="chips" style="margin:1rem 0"><a class="chip ${f.category ? "" : "on"}" href="#/wardrobe">All</a>${CATS.map(c => `<a class="chip ${f.category === c.id ? "on" : ""}" href="#/wardrobe?category=${c.id}">${esc(c.label)}</a>`).join("")}</div>
  <div class="bar" id="flt"><label>Search<input name="q" value="${esc(f.q)}" placeholder="Name, brand…"></label>
  <label>Colour<select name="color">${opts(fac.colors, f.color, "Any")}</select></label><label>Brand<input name="brand" value="${esc(f.brand)}" list="brands"></label><datalist id="brands">${fac.brands.map(b => `<option value="${esc(b)}">`).join("")}</datalist>
  <label>Style<select name="style">${opts(STYLES, f.style, "Any")}</select></label><label>Occasion<select name="occasion">${opts(OCC, f.occasion, "Any")}</select></label>
  <label>Season<select name="season">${opts(SEASONS, f.season, "Any")}</select></label>
  <label>Show<select name="favorite"><option value="">All</option><option value="true" ${f.favorite === "true" ? "selected" : ""}>Favourites</option></select></label>
  <label>Status<select name="status">${opts(["available", "laundry", "retired"], f.status, "Any")}</select></label>
  <label>Sort<select name="sort"><option value="recent">Recently added</option><option value="name" ${f.sort === "name" ? "selected" : ""}>Name</option><option value="most_worn" ${f.sort === "most_worn" ? "selected" : ""}>Most worn</option><option value="least_worn" ${f.sort === "least_worn" ? "selected" : ""}>Least worn</option></select></label></div><div id="res"></div>`;
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
  <div class="wide"><label>Occasions</label>${checks("occasions", OCC, it.occasions)}</div><div class="wide"><label>Seasons</label>${checks("seasons", SEASONS, it.seasons)}</div>
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
  $("#copy").onclick = guard(async () => { await navigator.clipboard.writeText(`${o.name || "Outfit"} (Veya)\n` + o.items.map(i => `- ${i.name} (${i.category_label}${i.primary_color ? ", " + i.primary_color : ""})`).join("\n") + (o.notes ? `\nNotes: ${o.notes}` : "")); toast("Summary copied"); });
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
  main.innerHTML = `<h1>Settings</h1><form class="f" id="pf" style="margin-top:1.2rem">
  <div class="wide"><label>Preferred styles</label>${checks("preferred_styles", STYLES, PREFS.preferred_styles)}</div>
  <label class="wide">Favourite colours (comma separated)<input name="favorite_colors" list="colors" value="${esc(PREFS.favorite_colors.join(", "))}"></label><datalist id="colors">${COLORS.map(c => `<option value="${c}">`).join("")}</datalist>
  <div class="wide"><label>Preferred occasions</label>${checks("preferred_occasions", OCC, PREFS.preferred_occasions)}</div>
  <label>Default occasion<select name="default_occasion">${opts(OCC, PREFS.default_occasion, "Any")}</select></label><label>Default season<select name="default_season">${opts(SEASONS, PREFS.default_season, "Any")}</select></label>
  <div class="wide"><label>Clothing categories I use</label><div class="chips">${CATS.map(c => `<label class="chip"><input type="checkbox" name="preferred_categories" value="${c.id}" ${PREFS.preferred_categories.includes(c.id) ? "checked" : ""}>${esc(c.label)}</label>`).join("")}</div></div>
  <div class="wide"><button class="btn primary">Save preferences</button></div></form>
  <h2>Your data</h2><div class="row"><a class="btn" href="/api/export" download>Export data (JSON)</a><a class="btn" href="/api/export/backup" download>Backup (database + photos)</a><button class="btn" id="rdemo">Remove demo items</button><button class="btn" data-act="demo">Load demo items</button><button class="btn danger" id="wipe">Delete all my data</button></div>
  <h2>About Veya</h2><p class="muted" style="max-width:60ch">Your Wardrobe. Reimagined. Style More. Buy Less.<br>Veya runs on this computer. Photos and data are stored locally, nothing is sent to AI services, and there is no tracking. Outfit suggestions come from a transparent rule-based engine (colour harmony, formality, occasion, season, your preferences and wear history). Automatic colour detection from photos is only a suggestion — you confirm it.</p>`;
  const f = $("#pf");
  f.onsubmit = guard(async e => { e.preventDefault(); const v = n => f.elements[n].value;
    PREFS = await api("/preferences", { method: "PUT", body: { preferred_styles: checked(f, "preferred_styles"), preferred_occasions: checked(f, "preferred_occasions"), preferred_categories: checked(f, "preferred_categories"), favorite_colors: v("favorite_colors").split(",").map(s => s.trim().toLowerCase()).filter(Boolean), default_occasion: v("default_occasion"), default_season: v("default_season") } });
    GEN = { list: [], seen: [], occ: "", season: "", msg: "" }; toast("Preferences saved"); });
  $("#rdemo").onclick = guard(async () => { if (confirm("Remove all demo items?")) { const r = await api("/demo", { method: "DELETE" }); GEN.list = []; toast(`Removed ${r.removed} demo items`); } });
  $("#wipe").onclick = guard(async () => { if (prompt("This permanently deletes every item, outfit and photo. Type DELETE to confirm.") === "DELETE") { await api("/data?confirm=true", { method: "DELETE" }); GEN = { list: [], seen: [], occ: "", season: "", msg: "" }; PREFS = await api("/preferences"); toast("All data deleted"); location.hash = "#/"; } });
}

(async () => { CATS = await api("/categories"); PREFS = await api("/preferences"); route(); })().catch(e => main.innerHTML = `<div class="empty"><h2>Can’t reach Veya’s backend</h2><p>${esc(e.message)}</p></div>`);
