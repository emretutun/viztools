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
    UYG.sahneAdi = r.sahne_adi;
    UYG.kelebekAday = r.kelebek_adaylari || [];
    UYG.viaDosyalari = r.via_files || [];
    UYG.kelebekSecili = null;   // null: henuz dokunulmadi (guncellemede plandakiler secili gelir)
    UYG.yolEngineden = !!r.yol_engineden;
    if (UYG.yolEngineden || !$("#uSahne").value) $("#uSahne").value = r.sahne_yolu || "";
    $("#uSahne").readOnly = UYG.yolEngineden;
    $("#uSahne").placeholder = "/KLASOR/ALT_KLASOR/KJ/" + r.sahne_adi;
    sahneYoluDuzelt();
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
  if (mod === "yeni") { UYG.liste = UYG.analizListe; UYG.meta = null; UYG.kelebekSecili = null; uygCiz(); return; }
  await mevcutKontrol();
}

async function mevcutKontrol() {
  const hedef = $("#uMevcut").value;
  if (!hedef) { UYG.liste = null; UYG.meta = null; $("#uMevcutBilgi").textContent = ""; uygCiz(); return; }
  try {
    const r = await api("/api/uygulama/kontrol", { hedef });
    UYG.liste = r.liste; UYG.meta = r.plan;
    if (!UYG.yolEngineden) $("#uSahne").value = r.plan.sahne || $("#uSahne").value;
    sahneYoluDuzelt();
    if (UYG.yolEngineden && r.plan.sahne && r.plan.sahne.toLowerCase() !== $("#uSahne").value.toLowerCase())
      $("#uSahneIpucu").textContent = `Uygulamadaki yol farklıydı (${r.plan.sahne}). Güncellemede engine'den okunan yol yazılacak.`;
    $("#uKelebek").value = r.plan.kelebek_klasoru || "";
    UYG.kelebekSecili = null;
    const yeni = r.liste.kalemler.filter(x => x.durum === "yeni").length, yok = r.liste.kalemler.filter(x => x.durum === "yok").length;
    $("#uMevcutBilgi").textContent = `${hedef}  ·  sahnede yeni: ${yeni}  ·  sahnede bulunamayan: ${yok}`;
    uygCiz();
  } catch (e) { toast(e.message, true); }
}

/** Yol sahnenin kendisini gostermeli: klasor yazildiysa sonuna sahne adini ekler. */
function sahneYoluDuzelt() {
  const kutu = $("#uSahne"), ad = UYG.sahneAdi || "";
  if (UYG.yolEngineden) { $("#uSahneIpucu").textContent = "Engine'den okundu. Elle yazmanız gerekmez."; return; }
  let v = kutu.value.trim().split(String.fromCharCode(92)).join("/").replace(/\/+$/, "");
  if (v && !v.startsWith("/")) v = "/" + v;
  let eklendi = false;
  if (v && ad && !ad.startsWith("#") && v.split("/").pop().toLowerCase() !== ad.toLowerCase()) { v += "/" + ad; eklendi = true; }
  kutu.value = v;
  $("#uSahneIpucu").textContent = !ad ? "" : eklendi ? `Sahne adı sona eklendi. Yol sahnenin kendisini göstermeli, klasörü değil.`
    : `Artist'te sol altta yazan yolun tamamı. Sonu sahne adıyla biter: …/${ad}`;
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

/** x'i ana (NORMAL) bant yapar; onceki ana bant siradan bir banda doner. */
function anaBantYap(x) {
  const anahtarYap = (v) => (v.etiket || v.tek).toLocaleUpperCase("tr-TR").replace(/[ÇĞİÖŞÜ]/g, c => ({ "Ç": "C", "Ğ": "G", "İ": "I", "Ö": "O", "Ş": "S", "Ü": "U" }[c]))
    .replace(/[^A-Z0-9]+/g, "_").replace(/^_|_$/g, "") || v.tek;
  UYG.liste.kalemler.filter(k => k.grup === "bant" && k.veri.anahtar === "" && k !== x).forEach(k => {
    if (k.veri.etiket === "NORMAL") k.veri.etiket = k.veri.tek.replace(/_/g, " ");
    k.veri.anahtar = anahtarYap(k.veri);
  });
  x.veri.anahtar = ""; x.secili = true;
}

function uygCiz() {
  kelebekCiz();
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
  const tag = el("span", "tags");
  if (x.durum === "yeni") tag.appendChild(el("span", "tag yeni", "sahnede yeni"));
  if (x.durum === "yok") tag.appendChild(el("span", "tag yok", "sahnede yok"));
  if (x.grup === "bant" && x.durum !== "yok") {
    // ana bant: TEKLI / CIFTLI KJ VER'in hicbir sey secilmeden verdigi bant. Tam bir tane olmali.
    const lb = el("label", "ana" + (normal ? " secili" : "")), rd = el("input");
    rd.type = "radio"; rd.name = "anaBant"; rd.checked = normal;
    rd.onchange = () => { anaBantYap(x); uygCiz(); };
    lb.appendChild(rd); lb.appendChild(document.createTextNode(" ana bant")); tag.appendChild(lb);
  }
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

// ---------------------------------------------------------------- kelebekler
// Kelebek ayri sahnedir: Artist'te acilip taranir; taranmis kelebekler burada listelenir, secilenler uygulamaya eklenir.
/** Kelebek kimligi: sahne yolu. Ayni adli sahne (3LU_SAG_DSF) her programda ayri sahnedir; taranmamis olan "elle/<ad>". */
const kid = k => k.sahne || ("elle/" + k.anahtar);

function kelebekSecim() {
  if (UYG.kelebekSecili) return UYG.kelebekSecili;
  const plandaki = (UYG.meta && UYG.meta.kelebekler || []).map(kid);
  return UYG.kelebekSecili = new Set(plandaki);
}

function kelebekTumu() {
  const aday = UYG.kelebekAday || [];
  const plandaki = (UYG.meta && UYG.meta.kelebekler || []).filter(k => !aday.some(a => kid(a) === kid(k)));
  const elle = (UYG.kelebekElle || []).filter(k => !aday.some(a => kid(a) === kid(k)) && !plandaki.some(a => kid(a) === kid(k)));
  return [...aday, ...plandaki, ...elle];
}

/** Taranmamis kelebek: Show TV adlandirmasiyla (ISIM1 / TITLE1 / isimlik_bg_1) addan kurulur; pencere sayisi addaki 2LI / 3LU'dan. */
function kelebekAddan(ad) {
  const m = /(^|_)(\d)_?(LI|LU)(_|$)/i.exec(ad); if (!m) return null;
  const n = +m[2], pencereler = [];
  for (let i = 1; i <= n; i++) pencereler.push({ isim: "$ISIM" + i, titr: "$TITLE" + i, gizle: "$isimlik_bg_" + i, titr_gizle: true });
  return { anahtar: ad, etiket: ad.replace(/_/g, " "), sahne: "", akis: "duz", pencereler, adet: n, kaynak: "elle (taranmadı)" };
}

function kelebekCiz() {
  const kutu = $("#uKelebekler"); if (!kutu) return;
  kutu.innerHTML = "";
  const secili = kelebekSecim(), tumu = kelebekTumu(), klasor = $("#uKelebek").value.trim().replace(/\/+$/, "");
  kutu.appendChild(el("div", "muted small",
    "viztools Graphic Hub klasörünü okuyamaz; klasör yolu yalnızca sahne yolunu kurmak içindir. Kelebekleri üç yoldan biriyle ekleyin: " +
    "(1) klasörü yazıp o klasörün .via arşivinden topluca alın, (2) her kelebeği Artist'te açıp tarayın, (3) Show TV adlandırmasındaki (ISIM1 / TITLE1) kelebeklerin adlarını aşağıya yazın."));

  if ((UYG.viaDosyalari || []).length) {
    const s = el("div"), sec = document.createElement("select"), b = el("button", "btn", "Arşivdeki kelebekleri topluca al");
    s.style.cssText = "display:flex;gap:6px;margin:6px 0"; sec.className = "input"; sec.style.flex = "1"; b.type = "button";
    UYG.viaDosyalari.forEach(v => { const o = el("option", null, v.name); o.value = v.path; sec.appendChild(o); });
    b.onclick = async () => {
      b.disabled = true; b.textContent = "Arşiv okunuyor...";
      try {
        const r = await api("/api/kelebek/via", { path: sec.value, klasor: $("#uKelebek").value.trim() });
        UYG.kelebekAday = r.kelebek_adaylari || []; UYG.kelebekKaynak = sec.options[sec.selectedIndex].text;
        toast(r.alinan.length + " kelebek sahnesi alındı" + (r.hatali.length ? ", " + r.hatali.length + " sahne okunamadı" : ""));
      } catch (e) { toast(e.message, true); }
      kelebekCiz();
    };
    s.appendChild(sec); s.appendChild(b); kutu.appendChild(s);
  }

  // (3) addan ekleme
  const e = el("div"), giris = document.createElement("input"), eb = el("button", "btn", "Adıyla ekle");
  e.style.cssText = "display:flex;gap:6px;margin:6px 0"; giris.className = "input mono"; giris.style.flex = "1"; eb.type = "button";
  giris.placeholder = "2LI_ESIT, 3LU_ESIT, 3LU_ORTA_DSF ...";
  eb.onclick = () => {
    const adlar = giris.value.split(/[,;\s]+/).map(x => x.trim()).filter(Boolean), kotu = [];
    UYG.kelebekElle = UYG.kelebekElle || [];
    adlar.forEach(ad => { const k = kelebekAddan(ad); if (!k) { kotu.push(ad); return; }
      if (!kelebekTumu().some(x => kid(x) === kid(k))) UYG.kelebekElle.push(k); secili.add(kid(k)); });
    if (kotu.length) toast("Adında pencere sayısı (2LI, 3LU...) olmayanlar eklenmedi: " + kotu.join(", "), true);
    kelebekCiz();
  };
  e.appendChild(giris); e.appendChild(eb); kutu.appendChild(e);
  if (!tumu.length) return;

  // kaynak suzgeci: baska programin taramalari listeyi doldurmasin
  const kaynaklar = [...new Set(tumu.map(k => k.kaynak || "tarama"))];
  if (UYG.kelebekKaynak && !kaynaklar.includes(UYG.kelebekKaynak)) UYG.kelebekKaynak = "";
  const goster = tumu.filter(k => !UYG.kelebekKaynak || (k.kaynak || "tarama") === UYG.kelebekKaynak || secili.has(kid(k)));
  const ust = el("div"), suz = document.createElement("select"), hepsi = el("button", "btn", "Görünenleri seç"), hic = el("button", "btn", "Seçimi kaldır");
  ust.style.cssText = "display:flex;gap:6px;margin:6px 0"; suz.className = "input"; suz.style.flex = "1"; hepsi.type = hic.type = "button";
  [["", "Kaynak: hepsi (" + tumu.length + ")"], ...kaynaklar.map(k => [k, k + " (" + tumu.filter(x => (x.kaynak || "tarama") === k).length + ")"])]
    .forEach(([v, t]) => { const o = el("option", null, t); o.value = v; suz.appendChild(o); });
  suz.value = UYG.kelebekKaynak || "";
  suz.onchange = () => { UYG.kelebekKaynak = suz.value; kelebekCiz(); };
  hepsi.onclick = () => { goster.forEach(k => secili.add(kid(k))); kelebekCiz(); };
  hic.onclick = () => { secili.clear(); kelebekCiz(); };
  ust.appendChild(suz); ust.appendChild(hepsi); ust.appendChild(hic); kutu.appendChild(ust);
  kutu.appendChild(el("div", "muted small", secili.size + " kelebek seçili"));

  goster.forEach(k => {
    const satir = el("label"), c = document.createElement("input"), yazi = el("span", "small");
    satir.style.cssText = "display:flex;gap:8px;align-items:flex-start;margin:4px 0;cursor:pointer";
    c.type = "checkbox"; c.checked = secili.has(kid(k)); c.style.marginTop = "3px";
    c.onchange = () => { c.checked ? secili.add(kid(k)) : secili.delete(kid(k)); kelebekCiz(); };
    const akis = { duz: "yazı + katman", stage: "tüm animasyon", director: "IN / İSİM animasyonlu" }[k.akis] || k.akis;
    const elle = (k.kaynak || "").startsWith("elle");
    const yol = k.sahne || (elle ? (klasor ? klasor + "/" + k.anahtar : "YOL YOK: kelebek klasörünü yazın")
                                 : "YOL YOK: klasörünü yazıp arşivi yeniden alın ya da sahneyi engine'den tarayın");
    yazi.textContent = `${k.etiket} · ${k.adet || (k.pencereler || []).length} pencere · ${akis} · ${yol} · ${k.kaynak || "tarama"}`;
    satir.appendChild(c); satir.appendChild(yazi); kutu.appendChild(satir);
  });
}

function kelebekPlan(klasor) {
  const secili = kelebekSecim();
  return kelebekTumu().filter(k => secili.has(kid(k))).map(k => {
    const c = Object.assign({}, k); delete c.kaynak;
    // Klasor yalnizca adiyla eklenen (taranmamis) kelebege uygulanir; taranmis sahnenin yolu taramasindan gelir
    if (!c.sahne && klasor && (k.kaynak || "").startsWith("elle")) c.sahne = klasor.replace(/\/+$/, "") + "/" + c.anahtar;
    return c;
  });
}

// ---------------------------------------------------------------- plan + uretim
function planKur() {
  const sec = UYG.liste.kalemler.filter(x => x.secili);
  const al = (g) => sec.filter(x => x.grup === g).map(x => Object.assign({}, x.veri));
  const plan = { bantlar: al("bant"), kulakciklar: al("kulakcik"), ozeller: al("ozel"), ogeler: al("oge") };
  if (!plan.bantlar.some(b => b.anahtar === "")) throw new Error("Ana bant seçilmemiş. BANT bölümünde normal bandın satırındaki \"ana bant\" seçeneğini işaretleyin.");
  const anah = plan.bantlar.map(b => b.anahtar);
  if (new Set(anah).size !== anah.length) throw new Error("Aynı bant iki kez seçilmiş: " + anah.filter((a, i) => anah.indexOf(a) !== i).join(", "));
  if ([...plan.bantlar, ...plan.kulakciklar, ...plan.ozeller, ...plan.ogeler].some(x => !String(x.etiket).trim()))
    throw new Error("Boş etiket var.");
  const kodlar = new Set(plan.bantlar.flatMap(b => [b.tek, b.cift, b.alt_satir].filter(Boolean)).concat(plan.ozeller.map(o => o.kod)));
  plan.turler = UYG.liste.turler.filter(t => kodlar.has(t.kod)).map(t => { const c = Object.assign({}, t); delete c._gecerli; return c; });
  return plan;
}

async function uret() {
  try {
    if (!UYG.liste) throw new Error("Önce bir sahne yükleyin.");
    sahneYoluDuzelt();
    const sahne = $("#uSahne").value.trim();
    if (!sahne.startsWith("/")) throw new Error("KJ sahnesinin Graphic Hub yolunu yazın (/ ile başlar).");
    const plan = planKur();
    plan.sahne = sahne; plan.kelebek_klasoru = $("#uKelebek").value.trim();
    plan.kelebekler = kelebekPlan(plan.kelebek_klasoru);
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
$("#uSahne").onblur = sahneYoluDuzelt;
$("#uKelebek").addEventListener("input", () => kelebekCiz());
$("#btnKlasor").onclick = () => api("/api/uygulama/ac?what=klasor&hedef=" + encodeURIComponent(UYG.sonHedef || "")).catch(e => toast(e.message, true));
$("#btnCozum").onclick = () => api("/api/uygulama/ac?what=cozum&hedef=" + encodeURIComponent(UYG.sonHedef || "")).catch(e => toast(e.message, true));
