/* Reji uygulamasi sekmesi: sahne analizinden plan duzenleme, uretme ve guncelleme */
const UYG = { mod: "yeni", liste: null, meta: null, sorular: [], uygulamalar: [], hedefElle: false, sahneDamga: null, izle: null };

const GRUPLAR = [
  { k: "bant", baslik: "BANT", acik: "Tek seçimli satır. TEKLİ KJ VER / ÇİFTLİ KJ VER ile verilir." },
  { k: "kulakcik", baslik: "KULAKÇIK", acik: "Bandın üstüne eklenir. Metin yazılmaz, yalnızca giriş/çıkış oynar." },
  { k: "ozel", baslik: "ÖZEL BUTON", acik: "Kendi VER butonu olan tek satırlı tür (isimlik, lokasyon gibi)." },
  { k: "oge", baslik: "ÖĞE", acik: "Metinsiz grafik, ayrı VER / AL butonları (logo, kapak gibi)." },
];
const GRUP_ADI = { bant: "bant", kulakcik: "kulakçık", ozel: "özel buton", oge: "öğe" };

// ---------------------------------------------------------------- yukleme
async function uygYukle() {
  if (!MODEL) { $("#uPlan").innerHTML = '<div class="empty">Önce soldan bir sahne yükleyin.</div>'; return; }
  if (UYG.sahneDamga === MODEL.scene.scanned_at && UYG.liste) { uygCiz(); return; }
  try {
    const r = await api("/api/uygulama/analiz");
    UYG.sahneDamga = MODEL.scene.scanned_at;
    UYG.sorular = r.sorular; UYG.uygulamalar = r.uygulamalar; UYG.repos = r.repos; UYG.analizListe = r.liste;
    if (!$("#uSahne").value) $("#uSahne").value = r.sahne_yolu || "";
    const sel = $("#uMevcut");
    sel.innerHTML = r.uygulamalar.length
      ? r.uygulamalar.map(u => `<option value="${esc(u.hedef)}">${esc(u.uygulama)}  ·  ${esc(u.sahne_adi)}</option>`).join("")
      : '<option value="">viztools ile üretilmiş uygulama bulunamadı</option>';
    const eslesen = r.uygulamalar.find(u => u.sahne_adi === r.sahne_adi || u.sahne_adi.split("_V")[0] === r.sahne_adi.split("_V")[0]);
    if (eslesen) sel.value = eslesen.hedef;
    await modDegistir(UYG.mod);
  } catch (e) { toast(e.message, true); }
}

async function modDegistir(mod) {
  UYG.mod = mod;
  document.querySelectorAll(".seg-b").forEach(b => b.classList.toggle("active", b.dataset.mod === mod));
  document.querySelector(".mod-yeni").hidden = mod !== "yeni";
  document.querySelector(".mod-guncelle").hidden = mod !== "guncelle";
  $("#btnUret").textContent = mod === "yeni" ? "Uygulamayı üret ve derle" : "Uygulamayı güncelle ve derle";
  if (mod === "yeni") { UYG.liste = UYG.analizListe; UYG.meta = null; uygCiz(); return; }
  await mevcutKontrol();
}

async function mevcutKontrol() {
  const hedef = $("#uMevcut").value;
  if (!hedef) { UYG.liste = null; UYG.meta = null; $("#uMevcutBilgi").textContent = ""; uygCiz(); return; }
  try {
    const r = await api("/api/uygulama/kontrol", { hedef });
    UYG.liste = r.liste; UYG.meta = r.plan;
    $("#uSahne").value = r.plan.sahne || $("#uSahne").value;
    $("#uKelebek").value = r.plan.kelebek_klasoru || "";
    const yeni = r.liste.kalemler.filter(x => x.durum === "yeni").length, yok = r.liste.kalemler.filter(x => x.durum === "yok").length;
    $("#uMevcutBilgi").textContent = `${hedef}  ·  sahnede yeni: ${yeni}  ·  sahnede bulunamayan: ${yok}`;
    uygCiz();
  } catch (e) { toast(e.message, true); }
}

// ---------------------------------------------------------------- cizim
function kodMetni(x) {
  const v = x.veri;
  if (x.grup === "bant") return v.tek === v.cift ? v.tek : `${v.tek}  /  ${v.cift}`;
  if (x.grup === "ozel") return v.kod;
  return v.giris;
}
function izinliGruplar(x) {
  if (x.grup === "bant") return x.veri.anahtar === "" ? ["bant"] : (x.veri.tek === x.veri.cift ? ["bant", "ozel"] : ["bant"]);
  if (x.grup === "ozel") return ["ozel", "bant"];
  return ["kulakcik", "oge"];
}
function grupDegistir(x, yeni) {
  const v = x.veri;
  if (x.grup === "ozel" && yeni === "bant") x.veri = { anahtar: v.kod, etiket: v.etiket, tek: v.kod, cift: v.kod };
  else if (x.grup === "bant" && yeni === "ozel") x.veri = { kod: v.tek, etiket: v.etiket };
  x.grup = yeni;
}

function uygCiz() {
  const so = $("#uSorular");
  if (UYG.sorular.length && UYG.mod === "yeni") {
    so.hidden = false;
    so.innerHTML = "<strong>Analizin emin olamadığı noktalar</strong><ol>" + UYG.sorular.map(q => `<li>${esc(q)}</li>`).join("") + "</ol>";
  } else so.hidden = true;

  const box = $("#uPlan"); box.innerHTML = "";
  if (!UYG.liste) { box.appendChild(el("div", "empty", UYG.mod === "yeni" ? "Önce soldan bir sahne yükleyin." : "Güncellenecek uygulamayı seçin.")); return; }
  GRUPLAR.forEach(g => {
    const kal = UYG.liste.kalemler.filter(x => x.grup === g.k);
    const grp = el("div", "grp");
    const h = el("div", "grp-h"); h.appendChild(el("span", null, g.baslik)); h.appendChild(el("span", "muted small", g.acik)); grp.appendChild(h);
    if (!kal.length) grp.appendChild(el("div", "muted small", "  Bu sahnede yok."));
    kal.forEach(x => grp.appendChild(kalemSatiri(x)));
    box.appendChild(grp);
  });
}

function kalemSatiri(x) {
  const normal = x.grup === "bant" && x.veri.anahtar === "";
  if (normal) x.secili = x.durum !== "yok";
  const r = el("div", "kal" + (x.secili ? "" : " off"));
  const cb = el("input"); cb.type = "checkbox"; cb.checked = x.secili; cb.disabled = normal || x.durum === "yok";
  cb.onchange = () => { x.secili = cb.checked; r.classList.toggle("off", !x.secili); };
  r.appendChild(cb);
  const et = el("input", "input"); et.value = x.veri.etiket; et.oninput = () => (x.veri.etiket = et.value.toLocaleUpperCase("tr-TR"));
  et.onblur = () => (et.value = x.veri.etiket);
  r.appendChild(et);
  const kod = el("span", "kod", kodMetni(x)); kod.title = kodMetni(x); r.appendChild(kod);
  const tag = normal ? el("span", "tag sabit", "zorunlu")
    : x.durum === "yeni" ? el("span", "tag yeni", "sahnede yeni")
    : x.durum === "yok" ? el("span", "tag yok", "sahnede yok") : el("span");
  r.appendChild(tag);
  const izin = izinliGruplar(x);
  if (izin.length > 1) {
    const s = el("select", "select");
    izin.forEach(g => { const o = el("option", null, GRUP_ADI[g]); o.value = g; s.appendChild(o); });
    s.value = x.grup; s.onchange = () => { grupDegistir(x, s.value); uygCiz(); };
    r.appendChild(s);
  } else r.appendChild(el("span", "muted small", GRUP_ADI[x.grup]));
  return r;
}

// ---------------------------------------------------------------- plan + uretim
function planKur() {
  const sec = UYG.liste.kalemler.filter(x => x.secili);
  const al = (g) => sec.filter(x => x.grup === g).map(x => Object.assign({}, x.veri));
  const plan = { bantlar: al("bant"), kulakciklar: al("kulakcik"), ozeller: al("ozel"), ogeler: al("oge") };
  if (!plan.bantlar.some(b => b.anahtar === "")) throw new Error("NORMAL bant sahnede bulunamadı. Sahneyi kontrol edin.");
  const anah = plan.bantlar.map(b => b.anahtar);
  if (new Set(anah).size !== anah.length) throw new Error("Aynı bant iki kez seçilmiş: " + anah.filter((a, i) => anah.indexOf(a) !== i).join(", "));
  if ([...plan.bantlar, ...plan.kulakciklar, ...plan.ozeller, ...plan.ogeler].some(x => !String(x.etiket).trim()))
    throw new Error("Boş etiket var.");
  const kodlar = new Set(plan.bantlar.flatMap(b => [b.tek, b.cift]).concat(plan.ozeller.map(o => o.kod)));
  plan.turler = UYG.liste.turler.filter(t => kodlar.has(t.kod)).map(t => { const c = Object.assign({}, t); delete c._gecerli; return c; });
  return plan;
}

async function uret() {
  try {
    if (!UYG.liste) throw new Error("Önce bir sahne yükleyin.");
    const sahne = $("#uSahne").value.trim();
    if (!sahne.startsWith("/")) throw new Error("KJ sahnesinin Graphic Hub yolunu yazın (/ ile başlar).");
    const plan = planKur();
    plan.sahne = sahne; plan.kelebek_klasoru = $("#uKelebek").value.trim();
    let hedef, guncelle = UYG.mod === "guncelle";
    if (guncelle) {
      hedef = $("#uMevcut").value; if (!hedef) throw new Error("Güncellenecek uygulamayı seçin.");
      plan.uygulama = UYG.meta.uygulama; plan.namespace = UYG.meta.namespace;
    } else {
      plan.uygulama = $("#uAd").value.trim(); if (!plan.uygulama) throw new Error("Uygulama adını yazın.");
      hedef = $("#uHedef").value.trim(); if (!hedef) throw new Error("Klasörü yazın.");
      plan.namespace = (await api("/api/uygulama/hedef", { ad: plan.uygulama })).namespace;
    }
    await api("/api/uygulama/uret", { plan, hedef, guncelle });
    $("#btnUret").disabled = true; $("#uSonuc").hidden = false; $("#uSonucBtn").hidden = true; $("#uLog").textContent = "";
    clearInterval(UYG.izle); UYG.izle = setInterval(durumIzle, 700);
  } catch (e) { toast(e.message, true); }
}

async function durumIzle() {
  const d = await api("/api/uygulama/durum").catch(() => null);
  if (!d) return;
  $("#uLog").textContent = d.satirlar.join("\n") + (d.calisiyor ? "\n… derleniyor" : "");
  if (d.calisiyor) return;
  clearInterval(UYG.izle); $("#btnUret").disabled = false;
  UYG.sonHedef = d.hedef;
  $("#uSonucBtn").hidden = !d.cozum;
  toast(d.ok ? "Hazır: uygulama derlendi" : "Üretim ya da derleme başarısız, kayda bakın", !d.ok);
  if (d.ok) { UYG.sahneDamga = null; if (UYG.mod === "yeni") { UYG.mod = "guncelle"; await uygYukle(); mevcutSec(d.hedef); await mevcutKontrol(); } else await mevcutKontrol(); }
}

/** Listede yoksa (repos disinda bir klasor) secenek olarak ekler ve secer. */
function mevcutSec(hedef) {
  const sel = $("#uMevcut");
  if (![...sel.options].some(o => o.value === hedef)) {
    if (sel.options.length === 1 && !sel.options[0].value) sel.innerHTML = "";
    const o = el("option", null, hedef.split(/[\\/]/).pop() + "  ·  " + hedef); o.value = hedef; sel.appendChild(o);
  }
  sel.value = hedef;
}

// ---------------------------------------------------------------- olaylar
document.querySelectorAll(".seg-b").forEach(b => b.onclick = () => modDegistir(b.dataset.mod));
$("#uMevcut").onchange = mevcutKontrol;
$("#uMevcutYol").onkeydown = (e) => { const v = $("#uMevcutYol").value.trim(); if (e.key === "Enter" && v) { mevcutSec(v); mevcutKontrol(); } };
let adT;
$("#uAd").oninput = () => {
  clearTimeout(adT);
  adT = setTimeout(async () => { if (UYG.hedefElle) return; try { $("#uHedef").value = (await api("/api/uygulama/hedef", { ad: $("#uAd").value })).hedef; } catch {} }, 250);
};
$("#uHedef").oninput = () => (UYG.hedefElle = !!$("#uHedef").value.trim());
$("#btnUret").onclick = uret;
$("#btnKlasor").onclick = () => api("/api/uygulama/ac?what=klasor&hedef=" + encodeURIComponent(UYG.sonHedef || "")).catch(e => toast(e.message, true));
$("#btnCozum").onclick = () => api("/api/uygulama/ac?what=cozum&hedef=" + encodeURIComponent(UYG.sonHedef || "")).catch(e => toast(e.message, true));
