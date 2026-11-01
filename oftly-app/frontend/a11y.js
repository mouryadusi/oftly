/* OFTLY accessibility layer. Loaded in <head> so saved settings apply before first paint (no flash).
   Model: active presets (combinable) + individual overrides -> computed settings -> data-* attributes and CSS variables.
   Everything is stored on this device only (localStorage "oftly.a11y3"). Presets are convenience starting points, not medical advice. */
(() => {
  const KEY = "oftly.a11y3";
  const D = { theme: "system", contrast: "normal", text: "100", lh: "normal", spacing: "normal", font: "editorial", bold: "off", links: "normal",
    dim: "0", cvd: "off", motion: "system", targets: "normal", focus: "normal", steady: "off", nodrag: "off", simple: "off", width: "normal" };
  const RANK = { contrast: ["normal", "high", "max"], lh: ["normal", "relaxed", "loose"], spacing: ["normal", "wide", "wider"], targets: ["normal", "large", "xl"], motion: ["system", "reduce", "none"], focus: ["normal", "strong"] };
  const NUM = ["text", "dim"];                               // merge = max
  const PRESETS = [
    { g: "Vision", id: "low-vision", t: "Low vision", d: "Very large text, maximum contrast, bold type, strong focus rings", s: { text: "150", contrast: "max", targets: "large", links: "underline", focus: "strong", bold: "on", lh: "relaxed" } },
    { g: "Vision", id: "cataracts", t: "Cataracts", d: "Dark high-contrast screen to cut glare, larger bold text", s: { theme: "dark", contrast: "high", text: "130", bold: "on", lh: "relaxed", focus: "strong" } },
    { g: "Vision", id: "presbyopia", t: "Presbyopia", d: "Larger text, roomier spacing, firmer contrast", s: { text: "130", lh: "relaxed", spacing: "wide", contrast: "high", targets: "large" } },
    { g: "Vision", id: "amd", t: "Macular degeneration (AMD)", d: "Largest text, widest spacing, narrow column, fewer distractions", s: { text: "175", contrast: "max", theme: "dark", bold: "on", spacing: "wider", lh: "loose", simple: "on", width: "narrow", targets: "xl", links: "underline", focus: "strong" } },
    { g: "Vision", id: "fatigue", t: "Visual fatigue", d: "Warm low-blue night screen, dimmed, calmer motion", s: { theme: "warm", dim: "20", motion: "reduce", text: "115", lh: "relaxed" } },
    { g: "Colour vision", id: "protan", t: "Protanopia (red-weak)", d: "Blue/orange interface colours, colour names on every item, underlined links", s: { cvd: "protan", links: "underline", contrast: "high" } },
    { g: "Colour vision", id: "deutan", t: "Deuteranopia (green-weak)", d: "Blue/orange interface colours, colour names on every item, underlined links", s: { cvd: "deutan", links: "underline", contrast: "high" } },
    { g: "Colour vision", id: "tritan", t: "Tritanopia (blue-weak)", d: "Red/teal interface colours, colour names on every item, underlined links", s: { cvd: "tritan", links: "underline", contrast: "high" } },
    { g: "Colour vision", id: "achroma", t: "Achromatopsia / no colour", d: "Black-and-white interface that never relies on colour, bold type", s: { cvd: "achroma", links: "underline", contrast: "high", bold: "on" } },
    { g: "Reading & focus", id: "dyslexia", t: "Dyslexia", d: "Highly legible typeface, wide spacing, short lines, left-aligned text", s: { font: "readable", spacing: "wider", lh: "loose", width: "narrow", text: "115", links: "underline", motion: "reduce" } },
    { g: "Reading & focus", id: "simple", t: "Simple & calm", d: "Hides decoration and extras, one thing at a time, larger targets", s: { simple: "on", motion: "reduce", width: "narrow", targets: "large", text: "115" } },
    { g: "Motion & sensitivity", id: "photosensitivity", t: "Photosensitivity", d: "All animation, marquees and parallax off; warm dimmed screen", s: { motion: "none", theme: "warm", dim: "10" } },
    { g: "Movement", id: "tremor", t: "Tremor", d: "Extra-large targets, ignores accidental double taps, no dragging", s: { targets: "xl", steady: "on", nodrag: "on", motion: "reduce", focus: "strong" } },
    { g: "Movement", id: "parkinsons", t: "Parkinson’s", d: "Extra-large targets, steady taps, no dragging, fewer choices", s: { targets: "xl", steady: "on", nodrag: "on", motion: "reduce", text: "115", simple: "on" } },
    { g: "Movement", id: "arthritis", t: "Osteoarthritis / sore hands", d: "Large targets, no dragging or swiping, fewer clicks", s: { targets: "large", nodrag: "on", simple: "on" } },
    { g: "Comfort", id: "night", t: "Night comfort", d: "Warm low-blue theme, dimmed", s: { theme: "warm", dim: "20" } },
    { g: "Comfort", id: "bright", t: "Bright light / outdoors", d: "Light theme, high contrast, slightly larger text", s: { theme: "light", contrast: "high", text: "115" } },
  ];
  const FIELDS = [   // fine-tune controls, grouped
    { g: "Seeing", k: "theme", l: "Theme", o: [["system", "Match my device"], ["light", "Light"], ["dark", "Dark"], ["warm", "Warm night"]] },
    { g: "Seeing", k: "contrast", l: "Contrast", o: [["normal", "Standard"], ["high", "High"], ["max", "Maximum"]] },
    { g: "Seeing", k: "text", l: "Text size", o: [["100", "100%"], ["115", "115%"], ["130", "130%"], ["150", "150%"], ["175", "175%"]] },
    { g: "Seeing", k: "dim", l: "Dim screen", o: [["0", "Off"], ["10", "10%"], ["20", "20%"], ["30", "30%"]] },
    { g: "Seeing", k: "cvd", l: "Colour support", o: [["off", "Off"], ["protan", "Protan (red-weak)"], ["deutan", "Deutan (green-weak)"], ["tritan", "Tritan (blue-weak)"], ["achroma", "No colour"]] },
    { g: "Reading", k: "font", l: "Typeface", o: [["editorial", "OFTLY editorial"], ["readable", "Highly legible"]] },
    { g: "Reading", k: "lh", l: "Line spacing", o: [["normal", "Standard"], ["relaxed", "Relaxed"], ["loose", "Loose"]] },
    { g: "Reading", k: "spacing", l: "Letter & word spacing", o: [["normal", "Standard"], ["wide", "Wide"], ["wider", "Wider"]] },
    { g: "Reading", k: "width", l: "Line length", o: [["normal", "Standard"], ["narrow", "Short lines"]] },
    { g: "Reading", k: "bold", l: "Bold text", t: 1 }, { g: "Reading", k: "links", l: "Always underline links", t: 1, on: "underline" },
    { g: "Motion", k: "motion", l: "Animation", o: [["system", "Match my device"], ["reduce", "Reduced"], ["none", "Off (no motion at all)"]] },
    { g: "Easier interaction", k: "targets", l: "Button & tap size", o: [["normal", "Standard"], ["large", "Large"], ["xl", "Extra large"]] },
    { g: "Easier interaction", k: "focus", l: "Focus outline", o: [["normal", "Standard"], ["strong", "Strong"]] },
    { g: "Easier interaction", k: "steady", l: "Steady taps (ignore accidental double taps)", t: 1 },
    { g: "Easier interaction", k: "nodrag", l: "No dragging or swiping (buttons only)", t: 1 },
    { g: "Easier interaction", k: "simple", l: "Simple view (hide decoration & extras)", t: 1 },
  ];
  const DURATIONS = [["0", "Until I change it"], ["3600000", "For 1 hour"], ["86400000", "For 1 day"], ["604800000", "For 1 week"]];

  const load = () => { try { return { active: [], over: {}, temp: null, ...JSON.parse(localStorage.getItem(KEY) || "{}") }; } catch { return { active: [], over: {}, temp: null }; } };
  let S = load();
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch { /* storage may be blocked; settings then last for this page only */ } };

  function merge(ids) {
    const out = { ...D };
    for (const p of PRESETS.filter(p => ids.includes(p.id))) for (const [k, v] of Object.entries(p.s)) {
      if (NUM.includes(k)) out[k] = String(Math.max(+out[k], +v));
      else if (RANK[k]) out[k] = RANK[k][Math.max(RANK[k].indexOf(out[k]), RANK[k].indexOf(v))];
      else if (v === "on" || v === "underline") out[k] = v;           // protective settings win
      else if (out[k] === D[k]) out[k] = v;                              // otherwise first non-default wins
    }
    return out;
  }
  const compute = () => ({ ...merge(S.active), ...S.over });
  const LH = { normal: 1.55, relaxed: 1.8, loose: 2.1 }, LS = { normal: ["0", "0"], wide: [".02em", ".08em"], wider: [".05em", ".16em"] }, TAP = { normal: 44, large: 54, xl: 66 };

  function apply() {
    const s = compute(), r = document.documentElement;
    for (const k of Object.keys(D)) r.dataset[k] = s[k];
    r.style.setProperty("--ts", +s.text / 100); r.style.setProperty("--lh", LH[s.lh]);
    r.style.setProperty("--ls", LS[s.spacing][0]); r.style.setProperty("--ws", LS[s.spacing][1]); r.style.setProperty("--tap", TAP[s.targets] + "px");
    r.style.setProperty("--dim", (+s.dim / 100).toFixed(2));
    document.dispatchEvent(new CustomEvent("oftly:a11y", { detail: s }));
  }
  function expire() {
    if (S.temp && Date.now() > S.temp.until) { S.active = S.temp.prev.active; S.over = S.temp.prev.over; S.temp = null; save(); return true; }
    return false;
  }
  expire(); apply();
  document.addEventListener("visibilitychange", () => { if (!document.hidden && expire()) { apply(); render(); } });

  // Steady taps: ignore a second click on the same control within 600 ms (tremor / Parkinson's).
  let last = { el: null, t: 0 };
  document.addEventListener("click", e => {
    if (compute().steady !== "on") return;
    const el = e.target.closest("button,a,[role=button],label.chip,summary");
    if (!el || el.closest("#a11y-panel")) return;
    if (el === last.el && e.timeStamp - last.t < 600) { e.preventDefault(); e.stopImmediatePropagation(); return; }
    last = { el, t: e.timeStamp };
  }, true);

  window.OFTLYA11y = { get: compute, PRESETS, FIELDS, toastMs: () => (compute().steady === "on" ? 8000 : 3200), isMotionOff: () => {
    const m = compute().motion; return m === "none" || m === "reduce" || matchMedia("(prefers-reduced-motion: reduce)").matches; },
    reset() { S = { active: [], over: {}, temp: null }; save(); apply(); }, apply, setOver: (k, v) => { S.over[k] = v; save(); apply(); }, state: () => S };

  /* ---------- panel UI ---------- */
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  let dlg;
  function render() {
    if (!dlg) return;
    const s = compute(), groups = [...new Set(PRESETS.map(p => p.g))], fg = [...new Set(FIELDS.map(f => f.g))];
    const customised = Object.keys(S.over).length;
    dlg.querySelector(".ap-body").innerHTML = `
      <p class="ap-note">Pick any that apply, in any combination. They change this app only and are saved on this device. They are starting points, not medical advice. Fine-tune below.</p>
      <label class="ap-dur">Apply presets<select id="ap-dur">${DURATIONS.map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select></label>
      ${S.temp ? `<p class="ap-temp" role="status">Temporary settings end ${new Date(S.temp.until).toLocaleString()}. <button class="link" data-ap="keep">Keep them</button></p>` : ""}
      <h3>Quick presets</h3>
      ${groups.map((g, i) => `<details ${i === 0 ? "open" : ""}><summary>${esc(g)}<span class="ap-count">${PRESETS.filter(p => p.g === g && S.active.includes(p.id)).length || ""}</span></summary><div class="ap-presets">
        ${PRESETS.filter(p => p.g === g).map(p => `<button type="button" class="ap-preset" data-preset="${p.id}" aria-pressed="${S.active.includes(p.id)}"><b>${esc(p.t)}</b><span>${esc(p.d)}</span></button>`).join("")}</div></details>`).join("")}
      <h3>Fine-tune ${customised ? `<small>(${customised} custom)</small>` : ""}</h3>
      ${fg.map(g => `<details><summary>${esc(g)}</summary><div class="ap-fields">${FIELDS.filter(f => f.g === g).map(f => f.t
        ? `<label class="ap-toggle"><input type="checkbox" data-field="${f.k}" ${s[f.k] === (f.on || "on") ? "checked" : ""}><span>${esc(f.l)}</span></label>`
        : `<label>${esc(f.l)}<select data-field="${f.k}">${f.o.map(([v, l]) => `<option value="${v}" ${s[f.k] === v ? "selected" : ""}>${esc(l)}</option>`).join("")}</select></label>`).join("")}</div></details>`).join("")}
      <div class="ap-foot"><button class="btn" data-ap="reset">Reset everything</button></div>`;
    
  }
  function build() {
    dlg = document.createElement("dialog"); dlg.id = "a11y-panel"; dlg.setAttribute("aria-labelledby", "ap-title");
    dlg.innerHTML = `<div class="ap-head"><h2 id="ap-title">Make OFTLY work for you</h2><button type="button" class="btn sm" data-ap="close" aria-label="Close accessibility panel">Close</button></div><div class="ap-body"></div>`;
    document.body.append(dlg);
    const dim = document.createElement("div"); dim.id = "dimmer"; dim.setAttribute("aria-hidden", "true"); document.body.append(dim);
    let opener = null;
    const open = () => { opener = document.activeElement; render(); if (!dlg.open) dlg.showModal(); };
    dlg.addEventListener("close", () => { if (opener && document.contains(opener)) opener.focus(); });
    dlg.addEventListener("click", e => {
      if (e.target === dlg) return dlg.close();
      const p = e.target.closest("[data-preset]"), a = e.target.closest("[data-ap]");
      if (p) {
        const id = p.dataset.preset, was = S.active.includes(id), ms = +dlg.querySelector("#ap-dur").value;
        if (ms && !was && !S.temp) S.temp = { until: Date.now() + ms, prev: { active: [...S.active], over: { ...S.over } } };
        S.active = was ? S.active.filter(x => x !== id) : [...S.active, id]; S.over = {};
        if (!S.active.length && S.temp) S.temp = null;
        save(); apply(); render(); dlg.querySelector(`[data-preset="${id}"]`)?.focus();
      } else if (a?.dataset.ap === "close") dlg.close();
      else if (a?.dataset.ap === "reset") { S = { active: [], over: {}, temp: null }; save(); apply(); render(); }
      else if (a?.dataset.ap === "keep") { S.temp = null; save(); render(); }
    });
    dlg.addEventListener("change", e => {
      const f = e.target.dataset.field; if (!f) return;
      const fld = FIELDS.find(x => x.k === f); S.over[f] = fld.t ? (e.target.checked ? (fld.on || "on") : "off") : e.target.value;
      if (fld.t && !e.target.checked && fld.on) S.over[f] = "normal";
      save(); apply(); const open = [...dlg.querySelectorAll("details")].map(d => d.open); render();
      dlg.querySelectorAll("details").forEach((d, i) => d.open = open[i]); dlg.querySelector(`[data-field="${f}"]`)?.focus();
    });
    document.addEventListener("keydown", e => { if (e.altKey && e.key.toLowerCase() === "a" && !dlg.open) { e.preventDefault(); open(); } });
    document.getElementById("open-a11y")?.addEventListener("click", open);
    window.OFTLYA11y.open = open;
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build); else build();
})();
