/* viztools web arayuzu */
const $ = (s) => document.querySelector(s);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

let MODEL = null, TAB = "dir", SEL = null, LAYER = "MAIN_SCENE";
const openState = new Map();   // id -> acik/kapali

// ---------------------------------------------------------------- yardimci
async function api(path, body) {
  const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}
let toastT;
function toast(msg, err) {
  const t = $("#toast"); t.textContent = msg; t.className = "toast" + (err ? " err" : ""); t.hidden = false;
  clearTimeout(toastT); toastT = setTimeout(() => (t.hidden = true), err ? 4000 : 1800);
}
async function copy(text, what) {
  try { await navigator.clipboard.writeText(text); toast((what || "Kopyalandı") + ": " + (text.length > 70 ? text.slice(0, 70) + "…" : text)); }
  catch { toast("Panoya yazılamadı", true); }
}
const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
function hl(text, q) {
  if (!q) return esc(text);
  const i = text.toLowerCase().indexOf(q); if (i < 0) return esc(text);
  return esc(text.slice(0, i)) + "<mark>" + esc(text.slice(i, i + q.length)) + "</mark>" + esc(text.slice(i + q.length));
}

// ---------------------------------------------------------------- durum
async function refreshStatus() {
  try {
    const s = await api("/api/status");
    $("#engineDot").className = "dot" + (s.engine ? " on" : "");
    $("#engineHint").textContent = s.engine ? (s.layers.MAIN_SCENE || "boş sahne") : "engine kapalı";
    $("#btnScan").disabled = !s.engine || s.scanning;
    if (s.scanning) {
      $("#progress").hidden = false;
      const [i, n] = s.progress; $("#bar").style.width = n ? (100 * i / n) + "%" : "15%";
      $("#progText").textContent = n ? `detay okunuyor ${i}/${n}` : "taranıyor…";
      setTimeout(refreshStatus, 400);
    } else {
      $("#progress").hidden = true;
      if (s.error) { toast("Tarama başarısız: " + s.error, true); }
    }
    // via dosyalari
    const sel = $("#viaFile"); const cur = sel.value;
    sel.innerHTML = '<option value="">— bulunan .via dosyaları —</option>' + s.via_files.map(f => `<option value="${esc(f.path)}">${esc(f.name)}  (${(f.size / 1048576).toFixed(1)} MB)</option>`).join("");
    if (cur) sel.value = cur;
    const rec = $("#recent"); rec.innerHTML = "";
    if (s.recent.length) {
      rec.appendChild(el("div", "label", "Son açılanlar"));
      s.recent.forEach(r => {
        const d = el("div", "item", (r.path.split(/[\\/]/).pop()) + (r.scene ? "  ›  " + r.scene : ""));
        d.title = r.path; d.onclick = () => loadVia(r.path, r.scene); rec.appendChild(d);
      });
    }
    const tr = $("#taramalar"); tr.innerHTML = "";
    (s.taramalar || []).forEach(t => {
      const d = el("div", "item", t.name + "  ·  " + new Date(t.zaman * 1000).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }));
      d.title = t.path;
      d.onclick = async () => { try { await api("/api/tarama/load", { path: t.path }); toast("Açıldı: " + t.name); await loadModel(); } catch (e) { toast(e.message, true); } };
      tr.appendChild(d);
    });
    if (!tr.childElementCount) tr.appendChild(el("div", "muted small", "Henüz tarama yok."));
    if (s.loaded && (!MODEL || MODEL.scene.scanned_at !== s.loaded.scanned_at)) await loadModel();
  } catch (e) { $("#engineHint").textContent = "sunucu yok"; }
}

async function loadModel() {
  const r = await api("/api/model");
  if (!r.model) return;
  MODEL = r.model; SEL = null; openState.clear(); $("#search").value = "";
  const s = MODEL.scene;
  $("#sceneName").textContent = s.name;
  $("#sceneMeta").textContent = `${s.source || "canlı engine"} · ${s.layer} · ${s.scanned_at.replace("T", " ")}`;
  const closed = MODEL.directors.filter(d => d.open === false);
  const chips = $("#chips"); chips.innerHTML = "";
  chips.appendChild(el("span", "chip", `${s.container_count} container`));
  chips.appendChild(el("span", "chip", `${s.director_count} director`));
  const fromVia = (s.source || "").toUpperCase().startsWith("VIA");
  chips.appendChild(fromVia ? el("span", "chip", ".via dosyasından")
    : el("span", "chip " + (closed.length ? "warn" : "ok"), closed.length ? `${closed.length} director kapalı` : "tümü okundu"));
  const w = $("#warn"); w.innerHTML = "";
  if (MODEL.warnings.length) {
    w.hidden = false; w.appendChild(el("span", null, MODEL.warnings[0]));
    if (closed.length) { const b = el("button", "btn", "Kapalı listesini kopyala"); b.onclick = () => copy(closed.map(d => d.name_path).join("\n"), "Kapalı director listesi"); w.appendChild(b); }
  } else w.hidden = true;
  $("#actions").hidden = false;
  $("#cntDir").textContent = MODEL.directors.length; $("#cntCon").textContent = MODEL.containers.length;
  renderTree(); renderDetail(null);
  UYG.sahneDamga = null; if (!$("#uyg").hidden) uygYukle();
}

// ---------------------------------------------------------------- agac
function dirTree() {
  const byPath = new Map(); const roots = [];
  MODEL.directors.forEach(d => { d._kids = []; byPath.set(d.name_path, d); });
  MODEL.directors.forEach(d => {
    const pp = d.name_path.includes("$", 1) ? d.name_path.slice(0, d.name_path.lastIndexOf("$")) : "";
    const p = byPath.get(pp); (p ? p._kids : roots).push(d);
  });
  return roots;
}
function renderTree() {
  const q = $("#search").value.trim().toLowerCase();
  const box = $("#tree"); box.innerHTML = "";
  if (!MODEL) { box.appendChild(el("div", "empty", "Önce bir sahne yükleyin.")); return; }
  const nodes = TAB === "dir" ? dirTree() : MODEL.tree;
  const kids = (n) => TAB === "dir" ? n._kids : n.children;
  const matches = (n) => !q || (n.name + " " + n.name_path + " " + (n.text || "")).toLowerCase().includes(q);
  const sub = (n) => kids(n).some(k => matches(k) || sub(k));
  let shown = 0;
  const build = (list, parent, depth) => {
    list.forEach(n => {
      const self = matches(n), deep = sub(n);
      if (q && !self && !deep) return;
      shown++;
      const id = n.name_path; const wrap = el("div", "node");
      const row = el("div", "node-row" + (SEL && SEL.name_path === id && SEL._kind === TAB ? " sel" : "") + (n.active === false ? " off" : ""));
      const has = kids(n).length > 0;
      const tw = el("span", "twisty" + (has ? "" : " leaf"));
      const isOpen = openState.has(id) ? openState.get(id) : (q ? true : (TAB === "dir" ? true : depth < 1));
      tw.textContent = isOpen ? "▼" : "▶";
      tw.onclick = (e) => { e.stopPropagation(); openState.set(id, !isOpen); renderTree(); };
      row.appendChild(tw);
      const nm = el("span", "nm"); nm.innerHTML = hl(n.name, q); row.appendChild(nm);
      if (TAB === "con") {
        const info = n.text ? `"${n.text}"` : (n.plugins && n.plugins.length ? n.plugins.slice(0, 2).join(", ") : "");
        if (info) { const s = el("span", "sub"); s.innerHTML = hl(info, q); row.appendChild(s); }
        if (n.active === false) row.appendChild(el("span", "badge off", "pasif"));
      } else {
        if (n.open === false) row.appendChild(el("span", "badge closed", "kapalı"));
        else if (n.animated && n.animated.length) row.appendChild(el("span", "badge", n.animated.length + " kanal"));
      }
      row.onclick = () => { SEL = Object.assign({ _kind: TAB }, n); renderTree(); renderDetail(n); };
      row.ondblclick = () => copy(n.name_path, "Yol");
      wrap.appendChild(row);
      if (has) { const ch = el("div", "children" + (isOpen ? "" : " hid")); build(kids(n), ch, depth + 1); wrap.appendChild(ch); }
      parent.appendChild(wrap);
    });
  };
  build(nodes, box, 0);
  if (!shown) box.appendChild(el("div", "empty", "Eşleşen kayıt yok."));
}
function setAll(open) { if (!MODEL) return; const nodes = TAB === "dir" ? MODEL.directors : MODEL.containers; nodes.forEach(n => openState.set(n.name_path, open)); renderTree(); }

// ---------------------------------------------------------------- detay
function cmdRows(kind, n) {
  const L = LAYER, p = n.name_path;
  if (kind === "dir") return [
    ["Yol", p], ["Start", `${L}*STAGE*DIRECTOR*${p} START`], ["Continue", `${L}*STAGE*DIRECTOR*${p} CONTINUE`],
    ["Stop", `${L}*STAGE*DIRECTOR*${p} STOP`], ["Başa sar", `${L}*STAGE*DIRECTOR*${p}*GOTO_TRIO 0`],
    ["VizScript", `Stage.FindDirector("${p.replace(/^\$/, "").replace(/\$/g, "/")}").StartAnimation()`]];
  return [
    ["Yol", p], ["Text", `${L}*TREE*${p}*GEOM*TEXT SET metin`], ["Aktif", `${L}*TREE*${p}*ACTIVE SET 1`],
    ["Pozisyon", `${L}*TREE*${p}*TRANSFORMATION*POSITION SET 0 0 0`], ["Resim", `${L}*TREE*${p}*IMAGE SET IMAGE*/yol/resim`],
    ["VizScript", `Scene.FindContainer("${n.name}").Geometry.Text = "metin"`]];
}
function renderDetail(n) {
  const d = $("#detail"); d.innerHTML = "";
  if (!n) { d.innerHTML = '<div class="empty">Soldan bir director ya da container seçin.<br><span class="muted">Satıra tıkla: detay · çift tık: yolu kopyala</span></div>'; return; }
  const kind = TAB;
  d.appendChild(el("div", "kind", kind === "dir" ? "Director" : "Container"));
  d.appendChild(el("h2", null, n.name));
  const pills = el("div", "pills");
  if (kind === "dir") {
    if (n.open === false) d.appendChild(el("div", "desc", "Artist'te kapalı: içeriği okunamadı. Stage'de dalı açıp kaydedin, tekrar tarayın."));
    if (n.sub_directors && n.sub_directors.length) n.sub_directors.forEach(s => pills.appendChild(el("span", "pill", "↳ " + s)));
    (n.animated || []).forEach(a => pills.appendChild(el("span", "pill", a.container ? `${a.container} · ${a.channels.join("/") || "kapalı"}` : a.channels.join("/"))));
    if (!pills.childElementCount && n.open !== false) d.appendChild(el("div", "desc", "Oynattığı container bilgisi yok (.via'dan okunmuş olabilir)."));
  } else {
    pills.appendChild(el("span", "pill", "#" + n.id));
    if (n.active != null) pills.appendChild(el("span", "pill", n.active ? "aktif" : "pasif"));
    (n.plugins || []).forEach(p => pills.appendChild(el("span", "pill", p)));
    if (n.children && n.children.length) pills.appendChild(el("span", "pill", n.children.length + " alt container"));
    if (n.text) d.appendChild(el("div", "desc", `“${n.text}”`));
  }
  if (pills.childElementCount) d.appendChild(pills);
  d.appendChild(el("div", "sect", "Tıkla → kopyala"));
  cmdRows(kind, n).forEach(([lab, val]) => {
    const c = el("div", "cmd"); c.appendChild(el("span", "lab", lab)); c.appendChild(el("span", "val", val)); c.appendChild(el("span", "cp", "kopyala"));
    c.onclick = () => copy(val, lab); d.appendChild(c);
  });
  $("#cmd").value = kind === "dir" ? `${LAYER}*STAGE*DIRECTOR*${n.name_path}*NAME GET` : `${LAYER}*TREE*${n.name_path}*GEOM*TEXT GET`;
}

// ---------------------------------------------------------------- via
async function loadVia(path, scene) {
  if (!path) { toast("Bir .via dosyası seçin ya da yolunu yazın", true); return; }
  try {
    const r = await api("/api/via/load", { path, scene });
    if (r.choose) { const s = await chooseScene(r.choose, path); if (s) return loadVia(path, s); return; }
    toast("Yüklendi: " + r.scene.name); await loadModel(); refreshStatus();
  } catch (e) { toast(e.message, true); }
}
function chooseScene(scenes, path) {
  return new Promise(res => {
    const m = $("#modal"), list = $("#modalList"), f = $("#modalFilter");
    $("#modalTitle").textContent = `${path.split(/[\\/]/).pop()} · ${scenes.length} sahne`;
    const fill = () => { const q = f.value.toLowerCase(); list.innerHTML = ""; scenes.filter(s => s.toLowerCase().includes(q)).forEach(s => { const d = el("div", null, s); d.onclick = () => { m.hidden = true; res(s); }; list.appendChild(d); }); };
    f.value = ""; f.oninput = fill; fill(); m.hidden = false; f.focus();
    f.onkeydown = (e) => { if (e.key === "Enter" && list.firstChild) list.firstChild.click(); if (e.key === "Escape") { m.hidden = true; res(null); } };
    $("#modalClose").onclick = () => { m.hidden = true; res(null); };
  });
}

// ---------------------------------------------------------------- olaylar
$("#btnScan").onclick = async () => { LAYER = $("#layer").value; try { await api("/api/scan", { layer: LAYER, details: $("#details").checked }); refreshStatus(); } catch (e) { toast(e.message, true); } };
$("#btnVia").onclick = () => loadVia($("#viaPath").value.trim() || $("#viaFile").value);
$("#viaFile").onchange = () => { if ($("#viaFile").value) $("#viaPath").value = ""; };
$("#layer").onchange = () => { LAYER = $("#layer").value; if (SEL) renderDetail(SEL); };
document.querySelectorAll(".tab").forEach(t => t.onclick = () => {
  document.querySelectorAll(".tab").forEach(x => x.classList.remove("active")); t.classList.add("active");
  const uyg = t.dataset.tab === "uyg";
  $("#uyg").hidden = !uyg; $("#split").hidden = uyg; document.querySelectorAll(".tree-only").forEach(x => x.hidden = uyg);
  if (uyg) { uygYukle(); return; }
  TAB = t.dataset.tab; SEL = null; renderTree(); renderDetail(null);
});
$("#search").oninput = renderTree;
$("#btnExpand").onclick = () => setAll(true);
$("#btnCollapse").onclick = () => setAll(false);
document.querySelectorAll("[data-open]").forEach(b => b.onclick = () => api("/api/open?what=" + b.dataset.open).catch(e => toast(e.message, true)));
$("#btnVizScript").onclick = async () => { try { const r = await api("/api/vizscript"); copy(r.text, "VizScript iskeleti"); } catch (e) { toast(e.message, true); } };
$("#btnSend").onclick = async () => { try { const r = await api("/api/send", { command: $("#cmd").value }); $("#cmdOut").textContent = r.result; } catch (e) { $("#cmdOut").textContent = e.message; } };
$("#cmd").onkeydown = (e) => { if (e.key === "Enter") $("#btnSend").click(); };
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f") { e.preventDefault(); $("#search").focus(); $("#search").select(); }
  if (e.key === "Escape" && document.activeElement === $("#search")) { $("#search").value = ""; renderTree(); }
});

refreshStatus();
setInterval(() => { if (!$("#progress").hidden) return; refreshStatus(); }, 8000);
