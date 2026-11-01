/* OFTLY interaction layer: preloader, scroll reveal, parallax, counters, carousels, marquee, copy buttons, wardrobe map.
   Everything respects the accessibility settings (OFTLYA11y): reduced/none motion, no-drag, simple view. No libraries. */
document.documentElement.classList.add("js");
const FX = (() => {
  const motionOff = () => window.OFTLYA11y ? OFTLYA11y.isMotionOff() : matchMedia("(prefers-reduced-motion: reduce)").matches;
  const nodrag = () => document.documentElement.dataset.nodrag === "on";
  const HEX = { black: "#1a1a1a", white: "#f4f1ea", grey: "#8a8a8a", gray: "#8a8a8a", beige: "#d8c3a5", cream: "#efe4c8", brown: "#6b4a2f", tan: "#c19a6b", khaki: "#b5a37a", navy: "#1f2a44",
    blue: "#2f6db5", "light blue": "#9cc3e6", denim: "#4a6a8f", green: "#3f7d4e", olive: "#7a7a3a", teal: "#2a8a8a", red: "#c0392b", burgundy: "#6d1f2f", pink: "#e7a1b5", orange: "#e07a2e",
    yellow: "#e9c53b", mustard: "#c9a227", purple: "#6f4a8e", silver: "#c0c0c4", gold: "#c9a24b" };
  const hex = c => HEX[(c || "").toLowerCase()] || "#b8ad98";

  /* --- preloader: once per browser session, never for reduced motion --- */
  function preloader() {
    if (motionOff() || sessionStorage.getItem("oftly.pre")) return;
    try { sessionStorage.setItem("oftly.pre", "1"); } catch { /* ignore */ }
    const el = document.createElement("div"); el.id = "pre"; el.setAttribute("aria-hidden", "true");
    el.innerHTML = `<span class="eyebrow">OFTLY · Your wardrobe, reimagined</span><span class="num">0</span>`;
    document.body.append(el); const n = el.querySelector(".num"), t0 = performance.now(), D = 900;
    const tick = t => { const p = Math.min(1, (t - t0) / D); n.textContent = Math.round(p * 100); p < 1 ? requestAnimationFrame(tick) : (el.classList.add("done"), setTimeout(() => el.remove(), 1000)); };
    requestAnimationFrame(tick);
  }

  /* --- reveal on scroll --- */
  const io = "IntersectionObserver" in window ? new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); countUp(e.target); } }), { threshold: .15, rootMargin: "0px 0px -6% 0px" }) : null;
  function countUp(root) {
    root.querySelectorAll?.("[data-count]").forEach(el => {
      const to = +el.dataset.count, dec = +(el.dataset.dec || 0); if (motionOff()) { el.textContent = to.toFixed(dec); return; }
      const t0 = performance.now(); const f = t => { const p = Math.min(1, (t - t0) / 1100), e = 1 - Math.pow(1 - p, 3); el.textContent = (to * e).toFixed(dec); if (p < 1) requestAnimationFrame(f); }; requestAnimationFrame(f);
    });
  }
  function observe(root = document) {
    root.querySelectorAll(".reveal,.ring,.fbars,.spark,.gauge,.tile").forEach((el, i) => { if (el.classList.contains("in")) return; el.style.setProperty("--d", Math.min(i % 6, 5) * .07 + "s"); io ? io.observe(el) : el.classList.add("in"); });
  }

  /* --- parallax (transform only; never moves scroll position) --- */
  let items = [], raf = 0;
  function parallaxTick() {
    raf = 0; if (motionOff()) { items.forEach(el => el.style.transform = ""); return; }
    const vh = innerHeight; items.forEach(el => { const r = el.getBoundingClientRect(); if (r.bottom < -200 || r.top > vh + 200) return;
      const off = (r.top + r.height / 2 - vh / 2) * (+el.dataset.speed || .1); el.style.transform = `translate3d(0,${(-off).toFixed(1)}px,0)`; });
  }
  addEventListener("scroll", () => { if (!raf && items.length) raf = requestAnimationFrame(parallaxTick); }, { passive: true });
  document.addEventListener("oftly:a11y", () => requestAnimationFrame(parallaxTick));

  /* --- carousel: buttons, keyboard, optional drag; progress indicator --- */
  function carousel(root) {
    const tr = root.querySelector(".track"), prev = root.querySelector("[data-dir='-1']"), next = root.querySelector("[data-dir='1']"), bar = root.querySelector(".prog i");
    if (!tr || tr.dataset.ready) return; tr.dataset.ready = 1;
    const upd = () => { const max = tr.scrollWidth - tr.clientWidth; const vis = tr.clientWidth / tr.scrollWidth;
      if (bar) { bar.style.setProperty("--w", Math.max(8, vis * 100) + "%"); bar.style.setProperty("--l", (max > 0 ? tr.scrollLeft / max * (100 - Math.max(8, vis * 100)) : 0) + "%"); }
      if (prev) prev.disabled = tr.scrollLeft < 4; if (next) next.disabled = tr.scrollLeft > max - 4; };
    const go = d => tr.scrollBy({ left: d * Math.max(240, tr.clientWidth * .8), behavior: motionOff() ? "auto" : "smooth" });
    prev?.addEventListener("click", () => go(-1)); next?.addEventListener("click", () => go(1));
    tr.addEventListener("scroll", () => requestAnimationFrame(upd), { passive: true }); addEventListener("resize", upd); upd();
    tr.addEventListener("keydown", e => { if (e.key === "ArrowRight") { e.preventDefault(); go(1); } else if (e.key === "ArrowLeft") { e.preventDefault(); go(-1); } });
    let down = null, moved = 0;
    tr.addEventListener("pointerdown", e => { if (e.pointerType !== "mouse" || nodrag() || e.target.closest("button,a,input,select")) return; down = { x: e.clientX, l: tr.scrollLeft }; moved = 0; });
    tr.addEventListener("pointermove", e => { if (!down) return; const dx = e.clientX - down.x; moved = Math.max(moved, Math.abs(dx)); if (moved > 5) { tr.classList.add("drag"); tr.scrollLeft = down.l - dx; } });
    const end = () => { if (!down) return; down = null; tr.classList.remove("drag"); };
    addEventListener("pointerup", end); tr.addEventListener("pointerleave", end);
    tr.addEventListener("click", e => { if (moved > 5) { e.preventDefault(); e.stopPropagation(); moved = 0; } }, true);
  }

  /* --- marquee pause button (WCAG 2.2.2) --- */
  function marquee(root) {
    root.querySelectorAll(".marq").forEach(m => { const b = m.querySelector("button"); if (!b) return;
      b.onclick = () => { const p = m.toggleAttribute("data-paused"); b.textContent = p ? "Play" : "Pause"; b.setAttribute("aria-pressed", p); }; });
  }

  /* --- copy to clipboard with inline confirmation --- */
  document.addEventListener("click", async e => {
    const b = e.target.closest("[data-copy]"); if (!b) return; const txt = b.dataset.copy, old = b.textContent;
    try { await navigator.clipboard.writeText(txt); } catch { const t = document.createElement("textarea"); t.value = txt; document.body.append(t); t.select(); try { document.execCommand("copy"); } catch { /* ignore */ } t.remove(); }
    b.textContent = "Copied ✓"; setTimeout(() => b.textContent = old, 1800);
  });

  /* --- wardrobe map: a Voronoi mosaic (inspired by nothing-to-watch's discovery map). Each cell is one garment. --- */
  function vmap(box, sites, onPick) {
    const cv = box.querySelector("canvas"), tip = box.querySelector(".tip"); if (!cv || !sites.length) return;
    const W = 320, H = 140; cv.width = W; cv.height = H; const ctx = cv.getContext("2d");
    const slots = [...new Set(sites.map(s => s.slot || "x"))];
    const hash = s => { let h = 2166136261; for (const c of String(s)) h = Math.imul(h ^ c.charCodeAt(0), 16777619); return ((h >>> 0) % 1000) / 1000; };
    const pts = sites.map(s => ({ ...s, x: ((s.formality - 1) / 4 * .8 + .1 + (hash(s.id + "x") - .5) * .09) * W, y: ((slots.indexOf(s.slot || "x") + .5) / slots.length * .8 + .1 + (hash(s.id + "y") - .5) * .09) * H }));
    const own = new Int16Array(W * H); const img = ctx.createImageData(W, H);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { let b = 0, bd = 1e9; for (let k = 0; k < pts.length; k++) { const dx = x - pts[k].x, dy = (y - pts[k].y) * 1.6, d = dx * dx + dy * dy; if (d < bd) { bd = d; b = k; } } own[y * W + x] = b; }
    const draw = hi => { for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const k = own[y * W + x], i = (y * W + x) * 4;
        const edge = (x + 1 < W && own[y * W + x + 1] !== k) || (y + 1 < H && own[(y + 1) * W + x] !== k); const c = hex(pts[k].colour);
        let r = parseInt(c.slice(1, 3), 16), g = parseInt(c.slice(3, 5), 16), b = parseInt(c.slice(5, 7), 16);
        if (hi === k) { r = Math.min(255, r + 38); g = Math.min(255, g + 38); b = Math.min(255, b + 38); }
        if (edge) { r = g = b = 245; } img.data[i] = r; img.data[i + 1] = g; img.data[i + 2] = b; img.data[i + 3] = 255; }
      ctx.putImageData(img, 0, 0); pts.forEach(p => { ctx.fillStyle = "rgba(0,0,0,.35)"; ctx.beginPath(); ctx.arc(p.x, p.y, 1.6, 0, 7); ctx.fill(); }); };
    draw(-1); const at = e => { const r = cv.getBoundingClientRect(); return own[Math.min(H - 1, Math.max(0, Math.floor((e.clientY - r.top) / r.height * H))) * W + Math.min(W - 1, Math.max(0, Math.floor((e.clientX - r.left) / r.width * W)))]; };
    cv.addEventListener("pointermove", e => { const k = at(e); draw(k); tip.textContent = `${pts[k].name} · ${pts[k].colour || "colour not set"}`; });
    cv.addEventListener("pointerleave", () => { draw(-1); tip.textContent = "Hover or tap a cell"; });
    cv.addEventListener("click", e => onPick(pts[at(e)]));
    cv.tabIndex = 0; cv.addEventListener("keydown", e => { if (e.key === "Enter") onPick(pts[0]); });
  }

  function after(root = document) {
    items = [...document.querySelectorAll("[data-speed]")]; observe(root); root.querySelectorAll(".carousel").forEach(carousel); marquee(root); parallaxTick();
  }
  document.getElementById("skip")?.addEventListener("click", () => document.getElementById("main").focus());
  document.addEventListener("DOMContentLoaded", preloader);
  return { after, hex, vmap, motionOff };
})();
