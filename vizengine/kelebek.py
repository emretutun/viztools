"""
Kelebek sahnesi analizi (bolunmus ekran: 2'li, 3'lu, 4'lu ... pencere; her pencerenin altinda isim + unvan).

Canli uc uygulamanin (NTR Show, NTR HT, NTR HTSPOR) kelebek / grafik kodu okunarak cikarildi; ayrinti REJI_KALIPLARI.md.
Kelebek ayri bir sahnedir: Artist'te acilip taranir (scenes\\<ad>\\<ad>.json), sonra uygulamaya eklenir.

Tanima (yalnizca adlardan; .via taramasinda da calisir):
  pencere   : sonu numarali isim alani  ISIM1 / isim_text_1 / NAME_1 ...   -> numara = pencere
  unvan     : ayni numarali             TITLE1 / titre_text_1 / TITR_1 ...
  gizle     : isim bosken gizlenen grup isimlik_bg_1 / ISIM_TITRE_ALL_01 (adi ISIM iceren, ayni numarali, yazi olmayan)
  akis      : "director" IN director'u varsa (BASA_CEK, IN, ISIM_IN/OUT, ISIM_TITRI_IN/OUT: Haberturk, HT Spor)
              "duz"      IN yok, pencere var (yazilar gonderilir, sahne katmana konur: Show TV)
              "stage"    pencere yok, animasyon var (sahnenin tum animasyonu oynatilir: Magazin)
"""
from __future__ import annotations

import glob
import json
import os
import re

from .gen_csharp import short_paths

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENES = os.path.join(KOK, "scenes")

_ISIM = re.compile(r"^(ISIM|ISIM_TEXT|ISIMLIK|NAME|AD_SOYAD)[_\- ]?0*(\d+)$", re.I)
_TITR = re.compile(r"^(TITLE|TITLE_TEXT|TITRE?_TEXT|TITRE?|UNVAN)[_\- ]?0*(\d+)$", re.I)
_NUMARALI = re.compile(r"^(.*?)[_\- ]?0*(\d+)$")
_ADET = re.compile(r"(^|_)(\d)_?(LI|LU|Lİ|LÜ)(_|$)", re.I)
_TITR_IN = ("ISIM_TITRI_IN", "ISIM_TITRE_IN", "ISIM_TITR_IN", "TITR_IN", "TITRE_IN")
_TITR_OUT = ("ISIM_TITRI_OUT", "ISIM_TITRE_OUT", "ISIM_TITR_OUT", "TITR_OUT", "TITRE_OUT")


def kelebek_analiz(model: dict) -> dict | None:
    """Model bir kelebek sahnesiyse kalem (plan girdisi) dondurur, degilse None."""
    cons, ad = model["containers"], model["scene"]["name"]
    kisa = short_paths(cons)

    def yol(c):
        k = kisa.get(c["name_path"], "")
        return c["name_path"] if not k or k.startswith("!") else k

    isim, titr, gruplar = {}, {}, {}
    for c in cons:
        m = _ISIM.match(c["name"])
        if m:
            isim.setdefault(int(m.group(2)), c)
            continue
        m = _TITR.match(c["name"])
        if m:
            titr.setdefault(int(m.group(2)), c)
            continue
        m = _NUMARALI.match(c["name"])
        if m and re.search(r"ISIM", m.group(1), re.I) and "text" not in c:   # isimlik zemini / grubu: en ustteki
            n = int(m.group(2))
            if n not in gruplar or c["depth"] < gruplar[n]["depth"]:
                gruplar[n] = c

    dirs = {d["name"].upper(): d["name_path"] for d in model["directors"] if d["name_path"].count("$") == 1}
    giris = dirs.get("IN") or dirs.get("GIRIS")
    pencereler = []
    for n in sorted(isim):
        g = gruplar.get(n)
        # isim alani o grubun icindeyse grup gizlenir; degilse (isimlik_bg gibi kardes zemin) yine o gizlenir
        pencereler.append({"isim": yol(isim[n]), "titr": yol(titr[n]) if n in titr else None,
                           "gizle": yol(g) if g else None,
                           "titr_gizle": bool(n in titr and not giris and not (g and titr[n]["name_path"].startswith(g["name_path"] + "$")))})
    # KJ sahnelerinde de ISIM_1 gibi tek bir alan olabilir: kelebek en az iki pencerelidir ya da adinda KELEBEK gecer
    # Yazi alani olmayan kelebek (ANKARA_3LU gibi): adinda pencere sayisi var ve IN + BASA_CEK ile oynuyor
    yazisiz = bool(_ADET.search(ad) and giris and dirs.get("BASA_CEK"))
    if len(pencereler) < 2 and not yazisiz and not re.search(r"KELEBEK", ad, re.I):
        return None
    if re.search(r"(^|_)KJ(_|$)|TICKER", ad, re.I) and not re.search(r"KELEBEK", ad, re.I):
        return None   # KJ sahnesinde de ISIM_1, ISIM_2 olabilir; o kelebek degildir

    gercek = [d for d in model["directors"] if re.search(r"[0-9A-Za-z]", d["name"]) and d["name"].lower() != "default"]
    akis = "director" if giris else ("duz" if pencereler else ("stage" if gercek else "duz"))
    k = {"anahtar": ad, "etiket": etiket(ad), "sahne": str(model["scene"].get("path") or "").rstrip("/"),
         "akis": akis, "pencereler": pencereler}
    if akis == "director":
        k.update({"giris": giris, "basa_cek": dirs.get("BASA_CEK"), "isim_in": dirs.get("ISIM_IN"), "isim_out": dirs.get("ISIM_OUT"),
                  "titr_in": next((dirs[x] for x in _TITR_IN if x in dirs), None),
                  "titr_out": next((dirs[x] for x in _TITR_OUT if x in dirs), None)})
        ust_grup = next((c for c in cons if c["depth"] == 0 and c["name"].lower() == "group"), None)
        if ust_grup:
            k["gorunur"] = [ust_grup["name_path"]]
        klip = next((c for c in cons if c["name"].lower() == "softclip" and re.search(r"\$BG\$", c["name_path"], re.I)), None)
        if klip:
            k["klip"] = klip["name_path"]
    m = _ADET.search(ad)
    k["adet"] = len(pencereler) or (int(m.group(2)) if m else 0)
    return {a: b for a, b in k.items() if b is not None}


def etiket(ad: str) -> str:
    """4_LU_KELEBEK_V3 -> 4'lü KELEBEK V3; 2LI_DSF_SAG -> 2'li DSF SAĞ."""
    s = re.sub(r"(^|_)(\d)_?(LI|LU)(?=_|$)", lambda m: f"{m.group(1)}{m.group(2)}'{ {'LI': 'li', 'LU': 'lü'}[m.group(3).upper()] }", ad, flags=re.I)
    tr = {"SAG": "SAĞ", "ESIT": "EŞİT", "DIK": "DİK"}
    return " ".join(tr.get(p, p) for p in s.replace("_", " ").split())


def adaylar(klasor: str = "") -> list[dict]:
    """
    scenes\\ altindaki taramalardan kelebek olanlar: [{..kalem.., "tarama": json yolu}].
    Sahne yolu taramada yoksa (.via) ve klasor verildiyse klasor + ad kullanilir.
    """
    out = []
    for jp in sorted(glob.glob(os.path.join(SCENES, "*", "*.json"))):
        if os.path.basename(jp).startswith("kumanda"):
            continue
        try:
            with open(jp, encoding="utf-8") as f:
                model = json.load(f)
            k = kelebek_analiz(model) if "containers" in model and "scene" in model else None
        except (OSError, ValueError, KeyError):
            continue
        if not k:
            continue
        k["tarama"] = os.path.abspath(jp)
        kaynak = str(model["scene"].get("source") or "")
        k["kaynak"] = kaynak.split(":", 1)[1].strip() if kaynak.lower().startswith("via") and ":" in kaynak else "canlı engine"
        out.append(k)
    return out


def via_ice_al(via_yolu: str, klasor: str = "") -> tuple[list[str], list[str]]:
    """
    Bir .via arsivindeki BUTUN kelebek sahnelerini topluca tarar ve scenes\\ altina yazar (engine gerekmez; tek tek
    Artist'te acmaya gerek kalmaz). Kelebek olmayan sahneler atlanir. Donus: (alinanlar, okunamayanlar).
    """
    from .via import read_via, list_scenes, ViaError
    from .template import write_outputs
    alinan, hatali = [], []
    for ad in list_scenes(via_yolu):
        try:
            model = read_via(via_yolu, ad)
        except (ViaError, ValueError, KeyError, IndexError) as e:
            hatali.append(f"{ad}: {e}")
            continue
        if kelebek_analiz(model):
            # Arsiv sahnenin Graphic Hub yolunu tasimaz: yol arsivin klasorunden kurulur ve taramaya yazilir. Boylece
            # ayni adli sahne baska bir programin klasoruyle eslestirilemez (3LU_SAG_DSF her programda ayri sahnedir).
            if klasor:
                model["scene"]["path"] = klasor.rstrip("/") + "/" + model["scene"]["name"]
            write_outputs(model, SCENES)
            alinan.append(model["scene"]["name"])
    return alinan, hatali


def tazele(plan: dict) -> list[str]:
    """Plandaki kelebekleri kendi taramalarindan yeniler (sahne degismisse); etiket ve sahne yolu korunur."""
    notlar = []
    for i, eski in enumerate(plan.get("kelebekler", [])):
        jp = eski.get("tarama")
        if not jp or not os.path.exists(jp):
            notlar.append(f"kelebek {eski['etiket']}: taramasi bulunamadi, oldugu gibi birakildi")
            continue
        with open(jp, encoding="utf-8") as f:
            yeni = kelebek_analiz(json.load(f))
        if not yeni:
            notlar.append(f"kelebek {eski['etiket']}: tarama artik kelebek gibi gorunmuyor, oldugu gibi birakildi")
            continue
        yeni.update({"etiket": eski["etiket"], "tarama": jp, "sahne": yeni["sahne"] or eski.get("sahne", "")})
        if {k: v for k, v in yeni.items()} != eski:
            notlar.append(f"kelebek {eski['etiket']}: taramadan yenilendi ({yeni['adet']} pencere)")
        plan["kelebekler"][i] = yeni
    return notlar


def dogrula(plan: dict) -> list[str]:
    hatalar, gorulen = [], set()
    for k in plan.get("kelebekler", []):
        ne = "kelebek " + str(k.get("etiket") or k.get("anahtar"))
        if not str(k.get("sahne", "")).startswith("/"):
            hatalar.append(f"{ne}: sahne yolu yok. Kelebek klasorunu yazin ya da sahneyi engine'den (Artist acikken) tarayin.")
        if k.get("akis") not in ("duz", "stage", "director"):
            hatalar.append(f"{ne}: akis 'duz', 'stage' ya da 'director' olmali")
        if k.get("akis") == "director" and not k.get("giris"):
            hatalar.append(f"{ne}: director akisinda giris (IN) gerekli")
        if k.get("anahtar") in gorulen:
            hatalar.append(f"{ne}: ayni kelebek iki kez")
        gorulen.add(k.get("anahtar"))
    if plan.get("kelebek_ayar", {}).get("katman", "BACK") not in ("BACK", "MAIN"):
        hatalar.append("kelebek_ayar.katman 'BACK' ya da 'MAIN' olmali")
    return hatalar


def sahne_cs(plan: dict, cs) -> str:
    """KelebekTipleri.Sahne.cs. cs: C# string yazici (uretec._cs)."""
    ayar = plan.get("kelebek_ayar") or {}
    L = ["// <auto-generated>", "//   viztools ureticisi tarafindan kumanda.json'dan (kelebekler) yazildi. Elle duzenlemeyin.",
         "// </auto-generated>", "", f"namespace {plan['namespace']}", "{", "    public static partial class KelebekTipleri", "    {",
         f"        public const string Katman = {cs(ayar.get('katman') or 'BACK')};",
         "        /// <summary>Arka plan klibi (SoftClip) dosyasi; bos ise gonderilmez.</summary>",
         f"        public const string KlipDosya = {cs(ayar.get('klip') or '')};", "",
         "        public static readonly IReadOnlyList<KelebekTipi> Tumu = new List<KelebekTipi>", "        {"]
    for k in plan.get("kelebekler", []):
        pen = ", ".join(f"new({cs(p['isim'])}, {cs(p.get('titr'))}, {cs(p.get('gizle'))}, {'true' if p.get('titr_gizle') else 'false'})"
                        for p in k.get("pencereler", []))
        ek = "".join(f", {ad} = {cs(k[alan])}" for ad, alan in (("Giris", "giris"), ("BasaCek", "basa_cek"), ("IsimIn", "isim_in"),
                                                              ("IsimOut", "isim_out"), ("TitrIn", "titr_in"), ("TitrOut", "titr_out"),
                                                              ("Klip", "klip")) if k.get(alan))
        if k.get("gorunur"):
            ek += ", Gorunur = new[] { " + ", ".join(cs(g) for g in k["gorunur"]) + " }"
        L.append(f"            new() {{ Anahtar = {cs(k['anahtar'])}, Etiket = {cs(k['etiket'])}, Sahne = {cs(k['sahne'])}, Akis = {cs(k['akis'])}, "
                 f"Pencereler = new KelebekPencere[] {{ {pen} }}{ek} }},")
    L += ["        };", "    }", "}", ""]
    return "\n".join(L)
