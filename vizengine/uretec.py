"""
Reji uygulamasi ureticisi: onaylanmis kumanda planindan (kumanda.json) C# WinForms cozumu yazar.

  Yeni uygulama : sablon/winforms kopyalanir, yer tutucular doldurulur, sahneye ait dosyalar uretilir,
                  kumanda paneli Designer'a yazilir, .sln olusturulur, git init yapilir (commit YOK).
  Guncelleme    : yalnizca sahneye bagli dosyalar yeniden yazilir (KjTipleri.Sahne.cs, VizScenes/*.cs,
                  kumanda.json). Elle yapilan duzenlemeler korunur. --arayuz verilirse kumanda paneli de
                  yeniden dizilir (yalnizca uretilmis adli kontroller; elle eklenenler kalir).

kumanda.json alanlari:
  uygulama, namespace, sahne (Graphic Hub yolu), kelebek_klasoru (ops.), tarama (vizscan JSON yolu),
  turler[{kod, etiket, giris, cikis, ust, alt|null}], bantlar[{anahtar, etiket, tek, cift}],
  kulakciklar[{anahtar, etiket, giris, cikis}], ozeller[{kod, etiket}], ogeler[{anahtar, etiket, giris, cikis}]
Satir bazli bant: bantlar[{..., tek = cift = ust satir turu, alt_satir (alt satir turunun kodu), alt_cikis (alt satiri alan director)}]
Istege bagli (canli uygulamalardan ogrenilen davranislar; ayrinti REJI_KALIPLARI.md):
  turler[]:  alan, yuvalar[{giris, cikis, ust, alt, ayirac}], ayirac (alt satir bosken gizlenen container),
             resim {container, varsayilan} (fotografli grafik: GOZAT butonu)
  ozeller[]: kaynak "liste" | "isim" | "kutu" (metin KJ listesinden / ISIMLER listesinden / kendi kutusundan),
             tus "F3" (VER kisayolu), al_tus "F4" (AL kisayolu)
  ogeler[]:  metin {container, secenekler[]} (yazili oge), kj_ile true|false ("KJ ile" kutusu ve ilk durumu),
             gorunur [container], oto_al_sn, bandi_al
  fon:       {secenekler[], varsayilan, ayarlar[{hedef, tip "imageclip"|"image"|"director", yol, degerler{secenek: deger}}]}
Kelebek (ikinci motor, ayri sahneler; vizengine/kelebek.py):
  kelebekler[{anahtar, etiket, sahne, tarama, akis "duz"|"stage"|"director", pencereler[{isim, titr, gizle, titr_gizle}],
              giris, basa_cek, isim_in, isim_out, titr_in, titr_out, gorunur[], klip}]
  kelebek_ayar: {katman "BACK"|"MAIN", klip (arka plan klibi dosyasi)}
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess

from .gen_csharp import ident, render_csharp, short_paths, class_name, tek_satir
from . import kelebek as _kelebek

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SABLON = os.path.join(KOK, "sablon", "winforms")
NL = "\n"


class UretimHatasi(RuntimeError):
    pass


# =========================================================================
#  PLAN DOGRULAMA
# =========================================================================
def plan_oku(yol: str) -> dict:
    with open(yol, encoding="utf-8") as f:
        plan = json.load(f)
    for alan in ("uygulama", "namespace", "sahne", "tarama", "turler", "bantlar"):
        if not plan.get(alan):
            raise UretimHatasi(f"kumanda.json: '{alan}' eksik")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", plan["namespace"]):
        raise UretimHatasi(f"namespace gecersiz: {plan['namespace']} (harf, rakam, alt cizgi)")
    for alan in ("kulakciklar", "ozeller", "ogeler"):
        plan.setdefault(alan, [])
    return plan


def model_oku(plan: dict, plan_klasoru: str) -> dict:
    yol = plan["tarama"]
    if not os.path.isabs(yol):
        yol = os.path.join(plan_klasoru, yol)
    if not os.path.exists(yol):
        raise UretimHatasi(f"tarama dosyasi yok: {yol} (vizscan.py --details ile tarayin)")
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def dogrula(plan: dict, model: dict) -> list[str]:
    """Plandaki her yolun sahnede bulundugunu kontrol eder; hata listesi doner."""
    hatalar = []
    dirs = {d["name_path"] for d in model["directors"]}
    kisa = {v.lstrip("!") for v in short_paths(model["containers"]).values() if v}
    tam = {c["name_path"] for c in model["containers"]}
    kodlar = {t["kod"] for t in plan["turler"]}

    # Sahne yolu sahnenin KENDISINI gostermeli (klasoru degil): son parca sahne adi olmali.
    sahne_adi = model["scene"]["name"]
    yol = str(plan.get("sahne", "")).strip().rstrip("/")
    gercek = str(model["scene"].get("path") or "").rstrip("/")
    if gercek and yol.lower() != gercek.lower():
        hatalar.append(f"Sahne yolu yanlis: '{yol}'. Engine'de bu sahnenin yolu: '{gercek}'")
    elif gercek:
        pass
    elif not yol.startswith("/"):
        hatalar.append("Sahne yolu / ile baslamali (Graphic Hub yolu), orn. /KLASOR/ALT/KJ/" + sahne_adi)
    elif re.search(r"[0-9A-Za-z]", sahne_adi) and not sahne_adi.startswith("#") \
            and yol.rsplit("/", 1)[-1].lower() != sahne_adi.lower():
        oneri = yol + "/" + sahne_adi
        hatalar.append(f"Sahne yolu sahne adiyla bitmiyor: '{yol}'. Klasor degil sahnenin kendisi yazilmali: '{oneri}'")

    def dir_var(y, ne):
        if y not in dirs:
            hatalar.append(f"{ne}: director sahnede yok: {y}")

    def con_var(y, ne):
        if y and y not in kisa and y not in tam:
            hatalar.append(f"{ne}: metin alani sahnede yok: {y}")

    for t in plan["turler"]:
        dir_var(t["giris"], t["kod"]); dir_var(t["cikis"], t["kod"])
        con_var(t["ust"], t["kod"]); con_var(t.get("alt"), t["kod"])
        for i, y in enumerate(t.get("yuvalar") or [], 2):
            dir_var(y["giris"], f"{t['kod']} {i}. yuva"); con_var(y["ust"], f"{t['kod']} {i}. yuva")
            if y.get("cikis"):
                dir_var(y["cikis"], f"{t['kod']} {i}. yuva")
            con_var(y.get("alt"), f"{t['kod']} {i}. yuva")
    for b in plan["bantlar"]:
        for k in (b["tek"], b["cift"]) + ((b["alt_satir"],) if b.get("alt_satir") else ()):
            if k not in kodlar:
                hatalar.append(f"bant {b['etiket']}: tur '{k}' turler listesinde yok")
        if b.get("alt_satir"):
            if b["tek"] != b["cift"]:
                hatalar.append(f"bant {b['etiket']}: satir bazli bantta tek ve cift ayni tur (ust satir) olmali")
            if b.get("alt_cikis"):
                dir_var(b["alt_cikis"], f"bant {b['etiket']} alt satir cikisi")
    if not any(b["anahtar"] == "" for b in plan["bantlar"]):
        hatalar.append("bantlar: NORMAL (anahtar \"\") bant yok")
    for o in plan["ozeller"]:
        if o["kod"] not in kodlar:
            hatalar.append(f"ozel {o['etiket']}: tur '{o['kod']}' turler listesinde yok")
        if o.get("kaynak", "liste") not in ("liste", "isim", "kutu"):
            hatalar.append(f"ozel {o['etiket']}: kaynak 'liste', 'isim' ya da 'kutu' olmali: {o.get('kaynak')}")
        for alan in ("tus", "al_tus"):
            if o.get(alan) and not re.fullmatch(r"F([1-9]|1[0-2])", o[alan]) or o.get(alan) in ("F7", "F8"):
                hatalar.append(f"ozel {o['etiket']}: {alan} F1..F12 olmali (F7 ve F8 ayrilmis): {o.get(alan)}")
    for t in plan["turler"]:
        con_var(t.get("ayirac"), t["kod"] + " ayirac")
        for y in t.get("yuvalar") or []:
            con_var(y.get("ayirac"), t["kod"] + " yuva ayirac")
        if t.get("resim"):
            con_var(t["resim"].get("container"), t["kod"] + " resim")
            if not t["resim"].get("container"):
                hatalar.append(f"{t['kod']}: resim.container eksik")
    for o in plan["ogeler"]:
        if o.get("metin"):
            con_var(o["metin"].get("container"), "oge " + o["etiket"] + " metin")
        for g in o.get("gorunur") or []:
            con_var(g, "oge " + o["etiket"] + " gorunur")
    fon = plan.get("fon")
    if fon:
        if not fon.get("secenekler"):
            hatalar.append("fon: secenekler bos")
        for a in fon.get("ayarlar", []):
            ne = f"fon ayari ({a.get('hedef')})"
            if a.get("tip") not in ("imageclip", "image", "director"):
                hatalar.append(f"{ne}: tip 'imageclip', 'image' ya da 'director' olmali: {a.get('tip')}")
            elif a["tip"] == "director":
                dir_var(a.get("yol"), ne)
            else:
                con_var(a.get("yol"), ne)
            for k in a.get("degerler", {}):
                if k != "*" and k not in fon.get("secenekler", []):
                    hatalar.append(f"{ne}: '{k}' fon seceneklerinde yok")
    for k in plan["kulakciklar"]:
        dir_var(k["giris"], "kulakcik " + k["etiket"]); dir_var(k["cikis"], "kulakcik " + k["etiket"])
    for o in plan["ogeler"]:
        dir_var(o["giris"], "oge " + o["etiket"]); dir_var(o["cikis"], "oge " + o["etiket"])
    anahtarlar = [b["anahtar"] for b in plan["bantlar"]]
    if len(set(anahtarlar)) != len(anahtarlar):
        hatalar.append("bantlar: ayni anahtar birden fazla")
    hatalar += _kelebek.dogrula(plan)
    return hatalar


# =========================================================================
#  URETILEN C# DOSYALARI
# =========================================================================
BANT_ALANI = "altbant"
SABLON_SURUMU = 7          # Main.Kj.cs / KjTipleri.cs mantigi degisince artar; guncellemede eski surum yenilenir
SABLON_MANTIK = ("Main.Kj.cs", "KjTipleri.cs", "VizrtExt.cs", "KelebekForm.cs", "KelebekTipleri.cs")


def sablon_surumu(proje: str) -> int:
    try:
        m = re.search(r"viztools-sablon:\s*(\d+)", open(os.path.join(proje, "Main.Kj.cs"), encoding="utf-8-sig").read())
    except OSError:
        return 0
    return int(m.group(1)) if m else 1


def sablonu_yenile(proje: str, plan: dict) -> list[str]:
    """Eski sablonla uretilmis uygulamada kumanda mantigini (Main.Kj.cs, KjTipleri.cs) yeniler; eskisi .yedek olarak kalir."""
    if sablon_surumu(proje) >= SABLON_SURUMU:
        return []
    for f in SABLON_MANTIK:
        hedef = os.path.join(proje, f)
        if os.path.exists(hedef) and not os.path.exists(hedef + ".yedek"):   # ilk yedek korunur
            os.replace(hedef, hedef + ".yedek")
        s = open(os.path.join(SABLON, f), encoding="utf-8").read()
        s = s.replace("__NS__", plan["namespace"]).replace("__BASLIK__", plan["uygulama"]).replace("__SAHNE__", plan["sahne"])
        open(hedef, "w", encoding="utf-8-sig").write(s)
    return ["Kumanda mantigi yeni surume gecirildi (Main.Kj.cs, KjTipleri.cs, VizrtExt.cs). Eski dosyalar .yedek olarak duruyor; "
            "bu dosyalara elle kod eklediyseniz yedekten tasiyin."]


def _cs(s: str | None) -> str:
    if s is None:
        return "null"
    return '"' + tek_satir(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def sahne_cs(plan: dict, model: dict | None = None) -> str:
    ns = plan["namespace"]
    kaynaklar = {o["kod"]: o.get("kaynak", "liste") for o in plan["ozeller"]}
    L = ["// <auto-generated>",
         f"//   viztools ureticisi tarafindan kumanda.json'dan yazildi. Elle duzenlemeyin;",
         f"//   sahne degisince: vizuret.py --plan kumanda.json --hedef . --guncelle",
         "// </auto-generated>", "", f"namespace {ns}", "{",
         "    public static partial class KjTipleri", "    {",
         f"        public const string SahneYolu = {_cs(plan['sahne'])};", "",
         "        public static readonly IReadOnlyList<KjTipi> Tumu = new List<KjTipi>", "        {"]
    bant_kodlari = {k for b in plan["bantlar"] for k in (b["tek"], b["cift"], b.get("alt_satir")) if k}
    satirli = {b["tek"]: b for b in plan["bantlar"] if b.get("alt_satir")}   # ust satir turu -> bant
    for t in plan["turler"]:
        # Bant turleri ayni alani paylasir; ozel turler banttan bagimsizdir (plan 'alan' vermediyse kendi alani).
        alan = BANT_ALANI if t["kod"] in bant_kodlari else (t.get("alan") or t["kod"].lower())
        yuva = ""
        if t.get("yuvalar"):
            yuva = ", Yuvalar = new KjYuva[] { " + ", ".join(
                f"new({_cs(y['giris'])}, {_cs(y['ust'])}, {_cs(y.get('alt'))}, {_cs(y.get('cikis') or t['cikis'])}"
                + (f", {_cs(y['ayirac'])}" if y.get("ayirac") else "") + ")" for y in t["yuvalar"]) + " }"
        ek = ""
        if kaynaklar.get(t["kod"], "liste") != "liste":
            ek += f", Kaynak = {_cs(kaynaklar[t['kod']])}"
        if t.get("ayirac"):
            ek += f", Ayirac = {_cs(t['ayirac'])}"
        if t["kod"] in satirli:
            ek += f", AltTur = {_cs(satirli[t['kod']]['alt_satir'])}, AltCikis = {_cs(satirli[t['kod']].get('alt_cikis'))}"
        if t.get("resim"):
            ek += f", Resim = {_cs(t['resim']['container'])}"
            if t["resim"].get("varsayilan"):
                ek += f", ResimVarsayilan = {_cs(t['resim']['varsayilan'])}"
        L.append(f"            new() {{ Kod = {_cs(t['kod'])}, Etiket = {_cs(t['etiket'])}, Alan = {_cs(alan)}, Giris = {_cs(t['giris'])}, "
                 f"Cikis = {_cs(t['cikis'])}, Ust = {_cs(t['ust'])}, Alt = {_cs(t.get('alt'))}{yuva}{ek} }},")
    L += ["        };", "", "        public static readonly IReadOnlyList<Varyant> Varyantlar = new List<Varyant>", "        {"]
    L += [f"            new({_cs(b['anahtar'])}, {_cs(b['etiket'])}, {_cs(b['tek'])}, {_cs(b['cift'])})," for b in plan["bantlar"]]
    L += ["        };", "", "        public static readonly IReadOnlyList<Kulakcik> Kulakciklar = new List<Kulakcik>", "        {"]
    L += [f"            new({_cs(k['anahtar'])}, {_cs(k['etiket'])}, {_cs(k['giris'])}, {_cs(k['cikis'])})," for k in plan["kulakciklar"]]
    L += ["        };", "", "        public static readonly IReadOnlyList<Ozel> Ozeller = new List<Ozel>", "        {"]
    L += [f"            new({_cs(o['kod'])}, {_cs(o['etiket'])})," for o in plan["ozeller"]]
    L += ["        };", "", "        public static readonly IReadOnlyList<Oge> Ogeler = new List<Oge>", "        {"]
    for o in plan["ogeler"]:
        ek = []
        if o.get("metin"):
            ek.append(f"Metin = {_cs(o['metin']['container'])}")
        if o.get("gorunur"):
            ek.append("Gorunur = new[] { " + ", ".join(_cs(g) for g in o["gorunur"]) + " }")
        if o.get("oto_al_sn"):
            ek.append(f"OtoAlSn = {int(o['oto_al_sn'])}")
        if o.get("bandi_al"):
            ek.append("BandiAl = true")
        L.append(f"            new({_cs(o['anahtar'])}, {_cs(o['etiket'])}, {_cs(o['giris'])}, {_cs(o['cikis'])})"
                 + (" { " + ", ".join(ek) + " }" if ek else "") + ",")
    fon = plan.get("fon") or {}
    L += ["        };", "", "        public static readonly IReadOnlyList<string> FonSecenekleri = new List<string>", "        {"]
    L += [f"            {_cs(x)}," for x in fon.get("secenekler", [])]
    L += ["        };", "", f"        public const string FonVarsayilan = {_cs(fon.get('varsayilan') or '')};", "",
          "        public static readonly IReadOnlyList<FonAyari> FonAyarlari = new List<FonAyari>", "        {"]
    for a in fon.get("ayarlar", []):
        deger = ", ".join(f"[{_cs(k)}] = {_cs(v)}" for k, v in a.get("degerler", {}).items())
        L.append(f"            new({_cs(a['hedef'])}, {_cs(a['tip'])}, {_cs(a['yol'])}, new Dictionary<string, string> {{ {deger} }}),")
    L += ["        };", "", "        /// <summary>isimler.json yokken ISIMLER listesine konan ornek satirlar (sahnedeki metinler).</summary>",
          "        public static readonly IReadOnlyList<(string Isim, string Titr)> IsimOrnekleri = new List<(string, string)>", "        {"]
    L += [f"            ({_cs(a)}, {_cs(b)})," for a, b in isim_ornekleri(plan, model)]
    L += ["        };", "    }", "}", ""]
    return NL.join(L)


def _sahne_metinleri(model: dict | None) -> dict:
    metin = {}
    if not model:
        return metin
    kisa = short_paths(model["containers"])
    for c in model["containers"]:
        if c.get("text"):
            metin[c["name_path"]] = c["text"]
            if kisa.get(c["name_path"]):
                metin.setdefault(kisa[c["name_path"]].lstrip("!"), c["text"])
    return metin


def isim_ornekleri(plan: dict, model: dict | None) -> list[tuple[str, str]]:
    metin = _sahne_metinleri(model)
    turler = {t["kod"]: t for t in plan["turler"]}
    out = []
    for o in plan["ozeller"]:
        t = turler.get(o["kod"])
        if o.get("kaynak") != "isim" or not t:
            continue
        cift = (tek_satir(metin.get(t["ust"], "")), tek_satir(metin.get(t.get("alt") or "", "")))
        if cift[0] and cift not in out:
            out.append(cift)
    return out


def ornek_liste(plan: dict, model: dict) -> dict:
    """Sahnedeki ornek metinlerle ilk acilis icin kj_list.ornek.json."""
    metin = {}
    kisa = short_paths(model["containers"])
    for c in model["containers"]:
        if c.get("text"):
            metin[c["name_path"]] = c["text"]
            if kisa.get(c["name_path"]):
                metin.setdefault(kisa[c["name_path"]].lstrip("!"), c["text"])
    turler = {t["kod"]: t for t in plan["turler"]}
    kjler = []
    for b in plan["bantlar"]:
        for kod in dict.fromkeys([b["tek"], b["cift"]]):
            t = turler[kod]
            alt_yol = turler[b["alt_satir"]]["ust"] if b.get("alt_satir") else t.get("alt")
            kjler.append({"tur": kod, "kulakcik": "", "satir1": tek_satir(metin.get(t["ust"], t["etiket"])),
                          "satir2": tek_satir(metin.get(alt_yol, "")) if alt_yol else ""})
            if b.get("alt_satir"):   # bir de tek satirlik ornek
                kjler.append({"tur": kod, "kulakcik": "", "satir1": tek_satir(metin.get(turler[kod].get("yuvalar", [{}])[0].get("ust"), t["etiket"])), "satir2": ""})
    for o in plan["ozeller"]:
        if o.get("kaynak", "liste") != "liste":
            continue   # metni KJ listesinden gelmez
        t = turler[o["kod"]]
        kjler.append({"tur": o["kod"], "kulakcik": "", "satir1": tek_satir(metin.get(t["ust"], t["etiket"])), "satir2": ""})
    return {"bolumler": [{"baslik": "Örnek (sahneden)", "kjler": kjler}]}


# =========================================================================
#  KUMANDA PANELI (Main.Designer.cs)
# =========================================================================
URETILMIS = re.compile(r"^(btn_tek_ver|btn_cift_ver|btn_KjAl|lbl_Bant|lbl_Kulakcik|lbl_YayinTuru|cbx_bant_\w+|cbx_kul_\w+|btn_ozel_\w+|btn_oge_\w+"
                       r"|txt_ozel_\w+|lbl_ozel_\w+|cmb_oge_\w+|txt_oge_\w+|cbx_ogekj_\w+|cbx_ogeoto_\w+|lbl_Fon|cmb_Fon|dgv_Isimler|btn_IsimKaydet|btn_IsimSil)$")


def _cok_satir(s: str) -> str:
    """Cok satirli sahne metnini kutuda gosterilecek hale getirir: satir sonu yerine \\n yazilir (uygulama geri cevirir)."""
    return "\\n".join(x.strip() for x in str(s or "").splitlines() if x.strip())


def _slug(s: str, kullanilan: set) -> str:
    b = ident(s or "normal").lower().lstrip("@") or "x"
    a, i = b, 2
    while a in kullanilan:
        a, i = f"{b}{i}", i + 1
    kullanilan.add(a)
    return a


def kumanda_kontrolleri(plan: dict, model: dict | None = None) -> tuple[list, int]:
    """(kontroller, gereken_yukseklik). Kontrol: (ad, tur, ozellik satirlari)."""
    ctl = []

    def btn(ad, metin, x, y, w, h, renk=None, enabled=True, tag=None, olay=None, font="Candara\", 11.25F"):
        L = []
        if renk:
            L += [f"{ad}.BackColor = Color.{renk};", f"{ad}.FlatStyle = FlatStyle.Flat;"]
        if not enabled:
            L.append(f"{ad}.Enabled = false;")
        L += [f"{ad}.Font = new Font(\"{font}, FontStyle.Bold);", f"{ad}.Location = new Point({x}, {y});",
              f"{ad}.Name = \"{ad}\";", f"{ad}.Size = new Size({w}, {h});"]
        if tag is not None:
            L.append(f"{ad}.Tag = {_cs(tag)};")
        L += [f"{ad}.Text = {_cs(metin)};", f"{ad}.UseVisualStyleBackColor = {'false' if renk else 'true'};"]
        if olay:
            L.append(f"{ad}.Click += {olay};")
        ctl.append((ad, "Button", L))

    def etiket(ad, metin, x, y, w, h, size="9.75F", renk="Black"):
        ctl.append((ad, "Label", [f"{ad}.Font = new Font(\"Segoe UI\", {size}, FontStyle.Bold);",
                                  f"{ad}.ForeColor = Color.{renk};", f"{ad}.Location = new Point({x}, {y});",
                                  f"{ad}.Name = \"{ad}\";", f"{ad}.Size = new Size({w}, {h});",
                                  f"{ad}.Text = {_cs(metin)};", f"{ad}.TextAlign = ContentAlignment.MiddleLeft;"]))

    def secici(ad, metin, tag, x, y, w, h, secili):
        L = [f"{ad}.Appearance = Appearance.Button;"]
        if secili:
            L += [f"{ad}.Checked = true;", f"{ad}.CheckState = CheckState.Checked;"]
        L += [f"{ad}.FlatStyle = FlatStyle.Flat;", f"{ad}.Font = new Font(\"Segoe UI\", 9F, FontStyle.Bold);",
              f"{ad}.Location = new Point({x}, {y});", f"{ad}.Name = \"{ad}\";", f"{ad}.Size = new Size({w}, {h});",
              f"{ad}.Tag = {_cs(tag)};", f"{ad}.Text = {_cs(metin)};", f"{ad}.TextAlign = ContentAlignment.MiddleCenter;",
              f"{ad}.UseVisualStyleBackColor = true;", f"{ad}.CheckedChanged += Secici_CheckedChanged;"]
        ctl.append((ad, "CheckBox", L))

    y = 22
    btn("btn_tek_ver", "TEKLİ KJ VER", 12, y, 196, 64, "LimeGreen", olay="btn_tek_ver_Click", font="Candara\", 14.25F")
    btn("btn_cift_ver", "ÇİFTLİ KJ VER", 214, y, 196, 64, "LimeGreen", olay="btn_cift_ver_Click", font="Candara\", 14.25F")
    btn("btn_KjAl", "KJ AL (F7)", 416, y, 210, 64, enabled=False, olay="btn_KjAl_Click", font="Candara\", 14.25F")
    y += 74

    kul = set()
    bantlar = sorted(plan["bantlar"], key=lambda b: b["anahtar"] != "")   # NORMAL basta
    if len(bantlar) > 1:
        etiket("lbl_Bant", "BANT", 12, y, 74, 32)
        for i, b in enumerate(bantlar):
            r, c = divmod(i, 4)
            secici(f"cbx_bant_{_slug(b['anahtar'], kul)}", b["etiket"], b["anahtar"], 90 + c * 134, y + r * 36, 130, 32, b["anahtar"] == "")
        y += math.ceil(len(bantlar) / 4) * 36 + 6
    else:   # tek bant varsa secici gostermeye gerek yok; yine de gizli bir NORMAL secici koy
        secici("cbx_bant_normal", "NORMAL", "", 0, 0, 1, 1, True)
        ctl[-1][2].append("cbx_bant_normal.Visible = false;")

    if plan["kulakciklar"]:
        etiket("lbl_Kulakcik", "KULAKÇIK", 12, y, 78, 32)
        ogeler = [{"anahtar": "", "etiket": "YOK"}] + plan["kulakciklar"]
        kul2 = set()
        for i, k in enumerate(ogeler):
            r, c = divmod(i, 5)
            secici(f"cbx_kul_{_slug(k['anahtar'] or 'yok', kul2)}", k["etiket"], k["anahtar"], 90 + c * 107, y + r * 36, 103, 32, k["anahtar"] == "")
        y += math.ceil(len(ogeler) / 5) * 36 + 6

    def kutu(ad, metin, tag, x, y, w, h):
        ctl.append((ad, "TextBox", [f"{ad}.Font = new Font(\"Segoe UI\", 9.75F);", f"{ad}.Location = new Point({x}, {y});",
                                    f"{ad}.Name = \"{ad}\";", f"{ad}.Size = new Size({w}, {h});", f"{ad}.Tag = {_cs(tag)};",
                                    f"{ad}.Text = {_cs(metin)};"]))

    def acilir(ad, secenekler, metin, tag, x, y, w, h, yazilabilir):
        L = [f"{ad}.DropDownStyle = ComboBoxStyle.{'DropDown' if yazilabilir else 'DropDownList'};",
             f"{ad}.Font = new Font(\"Segoe UI\", 9.75F);", f"{ad}.FormattingEnabled = true;"]
        if secenekler:
            L.append(f"{ad}.Items.AddRange(new object[] {{ " + ", ".join(_cs(x) for x in secenekler) + " });")
        L += [f"{ad}.Location = new Point({x}, {y});", f"{ad}.Name = \"{ad}\";", f"{ad}.Size = new Size({w}, {h});"]
        if tag is not None:
            L.append(f"{ad}.Tag = {_cs(tag)};")
        if yazilabilir and metin:
            L.append(f"{ad}.Text = {_cs(metin)};")
        ctl.append((ad, "ComboBox", L))

    def isaret(ad, metin, tag, x, y, w, h, secili):
        L = [f"{ad}.Checked = true;", f"{ad}.CheckState = CheckState.Checked;"] if secili else []
        L += [f"{ad}.Font = new Font(\"Segoe UI\", 8.25F);", f"{ad}.Location = new Point({x}, {y});", f"{ad}.Name = \"{ad}\";",
              f"{ad}.Size = new Size({w}, {h});", f"{ad}.Tag = {_cs(tag)};", f"{ad}.Text = {_cs(metin)};",
              f"{ad}.UseVisualStyleBackColor = true;"]
        ctl.append((ad, "CheckBox", L))

    # FON secimi (varsa) yayin satirinin solunda durur
    if plan.get("fon"):
        etiket("lbl_Fon", "FON", 12, y, 44, 28)
        acilir("cmb_Fon", [], "", None, 58, y + 1, 170, 25, yazilabilir=False)
        etiket("lbl_YayinTuru", "YAYINDA: -", 238, y, 388, 28, size="11.25F", renk="DarkRed")
    else:
        etiket("lbl_YayinTuru", "YAYINDA: -", 12, y, 614, 28, size="11.25F", renk="DarkRed")
    y += 34

    turler = {t["kod"]: t for t in plan["turler"]}
    metinler = _sahne_metinleri(model)
    metinler_ham = metinler

    # ISIMLER listesi: metni buradan gelen ozel tur varsa (isim / telefon)
    if any(o.get("kaynak") == "isim" for o in plan["ozeller"]):
        ad = "dgv_Isimler"
        ctl.append((ad, "DataGridView", [
            f"{ad}.AllowUserToResizeRows = false;", f"{ad}.BackgroundColor = Color.White;",
            f"{ad}.ColumnHeadersHeightSizeMode = DataGridViewColumnHeadersHeightSizeMode.AutoSize;",
            f"{ad}.Location = new Point(12, {y});", f"{ad}.MultiSelect = false;", f"{ad}.Name = \"{ad}\";",
            f"{ad}.RowHeadersVisible = false;", f"{ad}.SelectionMode = DataGridViewSelectionMode.FullRowSelect;",
            f"{ad}.Size = new Size(520, 104);"]))
        btn("btn_IsimKaydet", "KAYDET", 538, y, 88, 30, olay="btn_IsimKaydet_Click", font="Segoe UI\", 9F")
        btn("btn_IsimSil", "SİL", 538, y + 36, 88, 30, olay="btn_IsimSil_Click", font="Segoe UI\", 9F")
        y += 110

    # Ozel turler ve ogeler akis halinde dizilir. Kalem: (genislik, ust satir var mi, ciz(x, y_ust, y_buton))
    VER_W, AL_W, UST_H = 132, 64, 30
    COK_SATIR = 16   # cok satirli yazi kutusu olan satira eklenen yukseklik
    kalemler = []
    kul3 = set()
    alanlar: dict[str, list[dict]] = {}
    for o in plan["ozeller"]:   # ayni alani paylasanlar yan yana durur ve tek AL kullanir
        t = turler.get(o["kod"], {})
        alanlar.setdefault(t.get("alan") or o["kod"].lower(), []).append(o)
    for alan, uyeler in alanlar.items():
        adlar = [_slug(o["kod"], kul3) for o in uyeler]
        ust_var = any(o.get("kaynak") == "kutu" or turler.get(o["kod"], {}).get("resim") for o in uyeler)
        al_tus = next((o["al_tus"] for o in uyeler if o.get("al_tus")), None)

        def ciz(x, yu, yb, uyeler=uyeler, adlar=adlar, alan=alan, al_tus=al_tus):
            for i, (o, s_) in enumerate(zip(uyeler, adlar)):
                xi = x + i * (VER_W + 4)
                t = turler.get(o["kod"], {})
                if o.get("kaynak") == "kutu":
                    kutu(f"txt_ozel_{s_}", tek_satir(metinler.get(t.get("ust"), "")), o["kod"], xi, yu + 2, VER_W, 25)
                elif t.get("resim"):
                    btn(f"btn_ozel_{s_}_gozat", "GÖZAT", xi, yu, 58, 27, tag=o["kod"], olay="btn_ozel_gozat_Click", font="Segoe UI\", 8.25F")
                    etiket(f"lbl_ozel_{s_}", "resim seçilmedi", xi + 62, yu, VER_W - 62 + (AL_W + 4 if len(uyeler) == 1 else 0), 27,
                           size="8.25F", renk="DimGray")
                    ctl[-1][2].insert(0, f"lbl_ozel_{s_}.AutoEllipsis = true;")
                    ctl[-1][2].append(f"lbl_ozel_{s_}.Tag = {_cs(o['kod'])};")
                metin = o["etiket"] + (f" ({o['tus']})" if o.get("tus") else "")
                btn(f"btn_ozel_{s_}_ver", metin, xi, yb, VER_W, 48, "LimeGreen", tag=o["kod"], olay="btn_ozel_ver_Click", font="Candara\", 9.75F")
            btn(f"btn_ozel_{adlar[0]}_al", "AL" + (f" ({al_tus})" if al_tus else ""), x + len(uyeler) * (VER_W + 4), yb, AL_W, 48,
                enabled=False, tag=alan, olay="btn_ozel_al_Click", font="Candara\", 9.75F")
        kalemler.append((len(uyeler) * (VER_W + 4) + AL_W, UST_H if ust_var else 0, ciz))

    kul4 = set()
    for o in plan["ogeler"]:
        s_ = _slug(o["anahtar"], kul4)
        ust_var = bool(o.get("metin") or o.get("oto_al_sn"))

        def ciz(x, yu, yb, o=o, s_=s_):
            if o.get("metin"):
                kj = o.get("kj_ile") is not None
                w = VER_W if kj else VER_W + 4 + AL_W
                if o["metin"].get("secenekler"):   # hazir secenekler: acilir liste (tek satir)
                    acilir(f"cmb_oge_{s_}", o["metin"]["secenekler"], o["metin"]["secenekler"][0], o["anahtar"], x, yu + 2, w, 25, yazilabilir=True)
                else:                              # serbest yazi: cok satirli kutu, satirlar sahnedeki gibi gorunur
                    ad = f"txt_oge_{s_}"
                    satirlar = [x_.strip() for x_ in str(metinler_ham.get(o["metin"]["container"], "")).splitlines() if x_.strip()]
                    ctl.append((ad, "TextBox", [
                        "{ad}.AcceptsReturn = true;", "{ad}.Font = new Font(\"Segoe UI\", 9F);",
                        "{ad}.Lines = new string[] { " + ", ".join(_cs(z) for z in satirlar) + " };",
                        f"{ad}.Location = new Point({x}, {yu});", "{ad}.Multiline = true;", "{ad}.Name = \"{ad}\";",
                        f"{ad}.Size = new Size({w}, {UST_H + 14});", f"{ad}.Tag = {_cs(o['anahtar'])};"]))
                    ctl[-1] = (ad, "TextBox", [z.replace("{ad}", ad) for z in ctl[-1][2]])
                if kj:
                    isaret(f"cbx_ogekj_{s_}", "KJ ile", o["anahtar"], x + VER_W + 4, yu + 3, AL_W, 22, bool(o["kj_ile"]))
            elif o.get("oto_al_sn"):
                isaret(f"cbx_ogeoto_{s_}", f"{int(o['oto_al_sn'])} sn sonra AL", o["anahtar"], x, yu + 3, VER_W + 4 + AL_W, 22, True)
            btn(f"btn_oge_{s_}_ver", o["etiket"], x, yb, VER_W, 48, "LimeGreen", tag=o["anahtar"], olay="btn_oge_ver_Click", font="Candara\", 9.75F")
            btn(f"btn_oge_{s_}_al", "AL", x + VER_W + 4, yb, AL_W, 48, enabled=False, tag=o["anahtar"], olay="btn_oge_al_Click", font="Candara\", 9.75F")
        serbest = bool(o.get("metin")) and not o["metin"].get("secenekler")
        kalemler.append((VER_W + 4 + AL_W, (UST_H + COK_SATIR if serbest else UST_H) if ust_var else 0, ciz))

    satir, x = [], 12
    def satiri_yaz():
        nonlocal y, satir
        if not satir:
            return
        ust = max([0] + [u for _, u, _, _ in satir])
        for xi, u, ciz, _ in satir:   # ust satiri kisa olan kalem butonunun hemen ustune hizalanir
            ciz(xi, y + ust - u, y + ust)
        y += ust + 54
        satir = []
    for w, ust_var, ciz in kalemler:
        if satir and x + w > 628:
            satiri_yaz()
            x = 12
        satir.append((x, ust_var, ciz, w))
        x += w + 8
    satiri_yaz()
    return ctl, y + 6


def designer_kumanda_yaz(designer: str, plan: dict, model: dict | None = None) -> tuple[str, list[str]]:
    """Designer'daki uretilmis kumanda kontrollerini siler, plana gore yeniden yazar, yerlesimi ayarlar."""
    d, notlar = designer, []
    mevcut = re.findall(r"grp_Kumanda\.Controls\.Add\((\w+)\);", d)
    elle = [a for a in mevcut if not URETILMIS.match(a)]
    if elle:
        notlar.append("Elle eklenmis kontroller korundu: " + ", ".join(elle))
    for ad in [a for a in mevcut if URETILMIS.match(a)]:
        d, n1 = re.subn(rf"^            {ad} = new [\w.]+\(\);\n", "", d, flags=re.M)
        d, n2 = re.subn(rf"^            grp_Kumanda\.Controls\.Add\({ad}\);\n", "", d, flags=re.M)
        m = re.search(rf"^            //\n            // {ad}\n            //\n", d, flags=re.M)
        if m:
            son = d.find("            //\n            // ", m.end())
            d = d[:m.start()] + d[son:]
        d, n3 = re.subn(rf"^        private [\w.]+ {ad};\n", "", d, flags=re.M)

    ctl, gerek = kumanda_kontrolleri(plan, model)
    anchors = ["            grp_Kumanda = new GroupBox();" + NL, "            grp_Kumanda.BackColor = Color.LightGray;" + NL,
               "            grp_Kumanda.Text = \"KUMANDA\";" + NL, "        private GroupBox grp_Kumanda;" + NL]
    for a in anchors:
        if a not in d:
            raise UretimHatasi("Main.Designer.cs beklenen yapida degil (grp_Kumanda bulunamadi): " + a.strip())
    d = d.replace(anchors[0], anchors[0] + "".join(f"            {a} = new {t}();{NL}" for a, t, _ in ctl), 1)
    d = d.replace(anchors[1], anchors[1] + "".join(f"            grp_Kumanda.Controls.Add({a});{NL}" for a, _, _ in ctl), 1)
    blok = "".join(f"            //{NL}            // {a}{NL}            //{NL}" + "".join(f"            {x}{NL}" for x in L + [f"{a}.TabIndex = {i};"])
                   for i, (a, _, L) in enumerate(ctl))
    d = d.replace(anchors[2], anchors[2] + blok, 1)
    d = d.replace(anchors[3], anchors[3] + "".join(f"        private {t} {a};{NL}" for a, t, _ in ctl), 1)

    # yerlesim (tasarim yuksekligi 681). Kumanda 427 px'e sigiyorsa: KJ listesi ustte boydan boya, kumanda sag altta.
    # Sigmiyorsa (ISIMLER listesi, FON, cok buton): canli uygulamalardaki gibi listeler solda, kumanda sagda boydan boya.
    A = "AnchorStyles."
    if gerek <= 427:
        yer = {"grp_Kumanda": ((818, 200), (638, 427), f"{A}Bottom | {A}Left | {A}Right"),
               "pnl_Degerler": ((312, 200), (500, 475), f"{A}Bottom | {A}Left"),
               "dgv_KjListesi": ((312, 34), (1144, 160), f"{A}Top | {A}Bottom | {A}Left | {A}Right"),
               "lbl_KjBaslik": ((312, 6), (1144, 24), f"{A}Top | {A}Left | {A}Right")}
    else:
        if gerek > 593:
            notlar.append(f"Kumanda paneli cok kalabalik ({gerek} px); bazi kontroller tasabilir, Designer'da duzenleyin.")
        yer = {"grp_Kumanda": ((818, 34), (638, 593), f"{A}Top | {A}Bottom | {A}Left | {A}Right"),
               "pnl_Degerler": ((312, 375), (500, 300), f"{A}Bottom | {A}Left"),
               "dgv_KjListesi": ((312, 34), (500, 335), f"{A}Top | {A}Bottom | {A}Left"),
               "lbl_KjBaslik": ((312, 6), (500, 24), f"{A}Top | {A}Left")}
    for ad, (konum, boyut, capa) in yer.items():
        for desen, yeni in [(rf"{ad}\.Location = new Point\(\d+, \d+\)", f"{ad}.Location = new Point({konum[0]}, {konum[1]})"),
                            (rf"{ad}\.Size = new Size\(\d+, \d+\)", f"{ad}.Size = new Size({boyut[0]}, {boyut[1]})"),
                            (rf"{ad}\.Anchor = [^;]+", f"{ad}.Anchor = {capa}")]:
            d, n = re.subn(desen, yeni, d)
            if n != 1:
                raise UretimHatasi("Main.Designer.cs yerlesim satiri bulunamadi: " + desen)
    return d, notlar


# =========================================================================
#  CLAUDE.md (uretilen uygulama icin)
# =========================================================================
def claude_md(plan: dict, viztools: str) -> str:
    ns, ad = plan["namespace"], plan["uygulama"]
    return f"""# {ad}

Viz reji uygulamasi (C# WinForms, .NET 8). **viztools ureticisiyle** kumanda planindan uretildi.
Sahne: `{plan['sahne']}`{('  ·  Kelebekler: `' + plan['kelebek_klasoru'] + '`') if plan.get('kelebek_klasoru') else ''}

## Kurallar
- Gelistirme ve test YALNIZCA 127.0.0.1 (ShowData/IpList.txt). Yayin motorlarina baglanma.
- Canli uygulamalara (NTR Show, NTR HT, NTR HTSPOR, MCR HTSPOR, TickerControl HTS) dokunma; DB'lere dokunma.
- Sahne adlari koda elle yazilmaz: hepsi `{ns}/KjTipleri.Sahne.cs` ve `{ns}/VizScenes/*.cs` (uretilmis) icinde.

## Dosyalar
| Dosya | Kim yazar |
|---|---|
| `kumanda.json` | Plan (reji kararlari). Degisiklik buradan yapilir. |
| `{ns}/KjTipleri.Sahne.cs`, `{ns}/VizScenes/*.cs` | Uretici. Elle duzenlenmez. |
| `{ns}/Main.Designer.cs` kumanda paneli | Uretici ilk kez yazar; Designer'da elle duzenlenebilir. `--arayuz` ile yeniden dizilir (elle eklenenler kalir). |
| `{ns}/Main.Kj.cs`, `Main.cs`, digerleri | Sablon kodu (sahneden bagimsiz). |

Kumanda: TEKLI / CIFTLI KJ VER + BANT secimi + KULAKCIK secimi; ozel turler kendi butonuyla
(Tag = tur kodu, olay `btn_ozel_ver_Click`); metinsiz ogeler VER/AL (Tag = oge anahtari, `btn_oge_ver_Click` / `btn_oge_al_Click`).
Elle buton eklerken ayni Tag + olay baglamak yeterli.

## Sahne degisince guncelleme
1. Artist'te sahneyi ac, Stage ve Tree dallarini ac, kaydet.
2. `python "{viztools}\\vizapp.py" --sahne {plan['sahne']} --hedef . --guncelle`
   Plan korunur, sahneye bagli dosyalar yenilenir, derlenir. Sahnede yeni cikanlar listelenir.
3. Sahne planla uyusmazsa uygulamaya dokunulmaz: ya `kumanda.json`'u duzelt ve
   `python "{viztools}\\vizuret.py" --plan kumanda.json --hedef . --guncelle --arayuz --derle`,
   ya da 2. adimi `--yeniden-planla` ile tekrarla (plan analizden yeniden kurulur, elle eklenenler kalir).
4. Kullanici isterse uygulamayi `/teshis` argumaniyla acip (gonderilen komutlar gorunur) 127.0.0.1'de dener.

Ayrinti: viztools deposundaki `vizrt-reji` skill'i.
"""


def sahne_yolunu_guncelle(proje: str, plan: dict) -> list[str]:
    """Guncellemede: uygulamanin calisirken okudugu sahne yolunu (ShowData/scenes.txt) plana esitler."""
    notlar = []
    sahne_dir, sahne_ad = plan["sahne"].rstrip("/").rsplit("/", 1)
    sp = os.path.join(proje, "ShowData", "scenes.txt")
    if os.path.exists(sp):
        s = open(sp, encoding="utf-8").read()
        yeni, n = re.subn(r"basepath[ \t]*=[^\n]*\n(\s*)KJ_Scenes[ \t]*=[^\n]*",
                          lambda m: f"basepath = {sahne_dir}/\n{m.group(1)}KJ_Scenes = {sahne_ad}", s, count=1)
        if n == 0:
            notlar.append("UYARI: ShowData/scenes.txt icinde 'basepath' + 'KJ_Scenes' satirlari bulunamadi; sahne yolunu elle duzeltin: "
                          + plan["sahne"])
        elif yeni != s:
            open(sp, "w", encoding="utf-8").write(yeni)
            notlar.append("Sahne yolu guncellendi (ShowData/scenes.txt): " + plan["sahne"])
    cp = os.path.join(proje, "CSceneDataController.cs")
    if os.path.exists(cp):
        s = open(cp, encoding="utf-8-sig").read()
        yeni = re.sub(r'(public string KJ_Scenes \{ get; set; \} = )"[^"]*";', r"\1KjTipleri.SahneYolu;", s, count=1)
        if yeni != s:
            open(cp, "w", encoding="utf-8-sig").write(yeni)
    return notlar


# =========================================================================
#  ANA AKIS
# =========================================================================
def uret(plan_yolu: str, hedef: str, guncelle: bool = False, arayuz: bool = False) -> list[str]:
    plan = plan_oku(plan_yolu)
    model = model_oku(plan, os.path.dirname(os.path.abspath(plan_yolu)))
    hatalar = dogrula(plan, model)
    if hatalar:
        raise UretimHatasi("Plan sahneyle uyusmuyor:\n  - " + "\n  - ".join(hatalar))

    ns = plan["namespace"]
    proje = os.path.join(hedef, ns)
    rapor = []

    if not guncelle:
        if os.path.exists(hedef) and os.listdir(hedef):
            raise UretimHatasi(f"Hedef klasor bos degil: {hedef} (mevcut uygulama icin --guncelle kullanin)")
        os.makedirs(proje, exist_ok=True)
        sahne_dir, sahne_ad = plan["sahne"].rstrip("/").rsplit("/", 1)
        scenes = f"basepath = {sahne_dir}/\nKJ_Scenes = {sahne_ad}\n"
        if plan.get("kelebek_klasoru"):
            scenes += f"\n// Kelebekler (GRAFIK-1, BACK_LAYER)\nbasepath = {plan['kelebek_klasoru'].rstrip('/')}/\n"
        for kok, _, dosyalar in os.walk(SABLON):
            for f in dosyalar:
                kaynak = os.path.join(kok, f)
                rel = os.path.relpath(kaynak, SABLON).replace("__NS__", ns)
                hedef_dosya = os.path.join(proje, rel)
                os.makedirs(os.path.dirname(hedef_dosya), exist_ok=True)
                s = open(kaynak, encoding="utf-8").read()
                s = (s.replace("__NS__", ns).replace("__BASLIK__", plan["uygulama"])
                      .replace("__SAHNE__", plan["sahne"]).replace("__SCENES__", scenes))
                open(hedef_dosya, "w", encoding="utf-8-sig" if f.endswith(".cs") else "utf-8").write(s)
        # csproj: ornek liste de cikti klasorune gitsin
        pj = os.path.join(proje, f"{ns}.csproj")
        s = open(pj, encoding="utf-8").read()
        if "kj_list.ornek.json" not in s:
            s = s.replace("ShowData\\DenyIPlist.txt\"", "ShowData\\DenyIPlist.txt;ShowData\\kj_list.ornek.json\"")
        open(pj, "w", encoding="utf-8").write(s)
        with open(os.path.join(proje, "ShowData", "kj_list.ornek.json"), "w", encoding="utf-8") as f:
            json.dump(ornek_liste(plan, model), f, ensure_ascii=False, indent=2)
        # Designer kumanda paneli
        dp = os.path.join(proje, "Main.Designer.cs")
        d, notlar = designer_kumanda_yaz(open(dp, encoding="utf-8-sig").read(), plan, model)
        open(dp, "w", encoding="utf-8-sig").write(d)
        rapor += notlar
        # depo dosyalari
        open(os.path.join(hedef, ".gitignore"), "w", encoding="utf-8").write("bin/\nobj/\n.vs/\n*.user\n")
        open(os.path.join(hedef, "CLAUDE.md"), "w", encoding="utf-8").write(claude_md(plan, KOK))
        r = subprocess.run(["dotnet", "new", "sln", "-n", ns, "-o", hedef, "--force"], capture_output=True, text=True)
        # SDK surumune gore .sln ya da .slnx olusur
        sln = next((os.path.join(hedef, f"{ns}{u}") for u in (".slnx", ".sln") if os.path.exists(os.path.join(hedef, f"{ns}{u}"))), None)
        if r.returncode != 0 or not sln:
            rapor.append("UYARI: cozum dosyasi olusturulamadi: " + (r.stderr or r.stdout).strip()[:200])
        else:
            r = subprocess.run(["dotnet", "sln", sln, "add", pj], capture_output=True, text=True)
            if r.returncode != 0:
                rapor.append("UYARI: proje cozume eklenemedi: " + (r.stderr or r.stdout).strip()[:200])
            else:
                rapor.append("Cozum: " + sln)
        if not os.path.exists(os.path.join(hedef, ".git")):
            subprocess.run(["git", "init", "-q", hedef], capture_output=True)
        rapor.append(f"Yeni uygulama: {hedef}")
    else:
        if not os.path.isdir(proje):
            raise UretimHatasi(f"Proje klasoru yok: {proje} (yeni uygulama icin --guncelle olmadan calistirin)")
        rapor += sahne_yolunu_guncelle(proje, plan)
        yenilendi = sablonu_yenile(proje, plan)
        if yenilendi:
            rapor += yenilendi
            arayuz = True   # yeni mantik panelde yeni kontroller bekler; panel yeniden dizilir
        eski_plan = os.path.join(hedef, "kumanda.json")
        if os.path.exists(eski_plan):
            eski = json.load(open(eski_plan, encoding="utf-8"))
            for alan, k in (("turler", "kod"), ("bantlar", "anahtar"), ("kulakciklar", "anahtar"), ("ozeller", "kod"), ("ogeler", "anahtar")):
                a = {x[k] for x in eski.get(alan, [])}
                b = {x[k] for x in plan.get(alan, [])}
                if a - b:
                    rapor.append(f"{alan}: kaldirildi -> {sorted(a - b)}")
                if b - a:
                    rapor.append(f"{alan}: eklendi -> {sorted(b - a)}")
        if arayuz:
            dp = os.path.join(proje, "Main.Designer.cs")
            d, notlar = designer_kumanda_yaz(open(dp, encoding="utf-8-sig").read(), plan, model)
            open(dp, "w", encoding="utf-8-sig").write(d)
            rapor += notlar + ["Kumanda paneli yeniden dizildi."]
        elif any(x.startswith(("bantlar:", "kulakciklar:", "ozeller:", "ogeler:")) for x in rapor):
            rapor.append("Panelde yeni/kalkan buton var: --arayuz ile yeniden dizin ya da Designer'da elle ekleyin/silin.")
        rapor.append(f"Guncellendi: {proje}")

    # her iki modda: sahneye bagli dosyalar
    with open(os.path.join(proje, "KjTipleri.Sahne.cs"), "w", encoding="utf-8-sig") as f:
        f.write(sahne_cs(plan, model))
    with open(os.path.join(proje, "KelebekTipleri.Sahne.cs"), "w", encoding="utf-8-sig") as f:
        f.write(_kelebek.sahne_cs(plan, _cs))
    vs = os.path.join(proje, "VizScenes")
    os.makedirs(vs, exist_ok=True)
    for eski in os.listdir(vs):
        if eski.endswith(".cs"):
            os.remove(os.path.join(vs, eski))
    with open(os.path.join(vs, f"{class_name(model['scene']['name'])}.cs"), "w", encoding="utf-8-sig") as f:
        f.write(render_csharp(model))
    kayit = dict(plan)
    if os.path.abspath(os.path.dirname(plan_yolu)) != os.path.abspath(hedef):
        kayit["tarama"] = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(plan_yolu)), plan["tarama"])) \
            if not os.path.isabs(plan["tarama"]) else plan["tarama"]
        with open(os.path.join(hedef, "kumanda.json"), "w", encoding="utf-8") as f:
            json.dump(kayit, f, ensure_ascii=False, indent=2)
    return rapor


def derle(hedef: str) -> tuple[bool, str]:
    r = subprocess.run(["dotnet", "build", hedef, "-nologo", "-v", "q"], capture_output=True, text=True)
    cikti = r.stdout + r.stderr
    hatalar = sorted({re.sub(r"\s*\[.*$", "", l.strip()) for l in cikti.splitlines() if " error " in l})
    return r.returncode == 0, "\n".join(hatalar) if hatalar else ("Build succeeded" if r.returncode == 0 else cikti[-800:])
