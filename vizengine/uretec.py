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
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess

from .gen_csharp import ident, render_csharp, short_paths, class_name, tek_satir

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
    for b in plan["bantlar"]:
        for k in (b["tek"], b["cift"]):
            if k not in kodlar:
                hatalar.append(f"bant {b['etiket']}: tur '{k}' turler listesinde yok")
    if not any(b["anahtar"] == "" for b in plan["bantlar"]):
        hatalar.append("bantlar: NORMAL (anahtar \"\") bant yok")
    for o in plan["ozeller"]:
        if o["kod"] not in kodlar:
            hatalar.append(f"ozel {o['etiket']}: tur '{o['kod']}' turler listesinde yok")
    for k in plan["kulakciklar"]:
        dir_var(k["giris"], "kulakcik " + k["etiket"]); dir_var(k["cikis"], "kulakcik " + k["etiket"])
    for o in plan["ogeler"]:
        dir_var(o["giris"], "oge " + o["etiket"]); dir_var(o["cikis"], "oge " + o["etiket"])
    anahtarlar = [b["anahtar"] for b in plan["bantlar"]]
    if len(set(anahtarlar)) != len(anahtarlar):
        hatalar.append("bantlar: ayni anahtar birden fazla")
    return hatalar


# =========================================================================
#  URETILEN C# DOSYALARI
# =========================================================================
def _cs(s: str | None) -> str:
    if s is None:
        return "null"
    return '"' + tek_satir(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def sahne_cs(plan: dict) -> str:
    ns = plan["namespace"]
    L = ["// <auto-generated>",
         f"//   viztools ureticisi tarafindan kumanda.json'dan yazildi. Elle duzenlemeyin;",
         f"//   sahne degisince: vizuret.py --plan kumanda.json --hedef . --guncelle",
         "// </auto-generated>", "", f"namespace {ns}", "{",
         "    public static partial class KjTipleri", "    {",
         f"        public const string SahneYolu = {_cs(plan['sahne'])};", "",
         "        public static readonly IReadOnlyList<KjTipi> Tumu = new List<KjTipi>", "        {"]
    for t in plan["turler"]:
        L.append(f"            new() {{ Kod = {_cs(t['kod'])}, Etiket = {_cs(t['etiket'])}, Giris = {_cs(t['giris'])}, "
                 f"Cikis = {_cs(t['cikis'])}, Ust = {_cs(t['ust'])}, Alt = {_cs(t.get('alt'))} }},")
    L += ["        };", "", "        public static readonly IReadOnlyList<Varyant> Varyantlar = new List<Varyant>", "        {"]
    L += [f"            new({_cs(b['anahtar'])}, {_cs(b['etiket'])}, {_cs(b['tek'])}, {_cs(b['cift'])})," for b in plan["bantlar"]]
    L += ["        };", "", "        public static readonly IReadOnlyList<Kulakcik> Kulakciklar = new List<Kulakcik>", "        {"]
    L += [f"            new({_cs(k['anahtar'])}, {_cs(k['etiket'])}, {_cs(k['giris'])}, {_cs(k['cikis'])})," for k in plan["kulakciklar"]]
    L += ["        };", "", "        public static readonly IReadOnlyList<Ozel> Ozeller = new List<Ozel>", "        {"]
    L += [f"            new({_cs(o['kod'])}, {_cs(o['etiket'])})," for o in plan["ozeller"]]
    L += ["        };", "", "        public static readonly IReadOnlyList<Oge> Ogeler = new List<Oge>", "        {"]
    L += [f"            new({_cs(o['anahtar'])}, {_cs(o['etiket'])}, {_cs(o['giris'])}, {_cs(o['cikis'])})," for o in plan["ogeler"]]
    L += ["        };", "    }", "}", ""]
    return NL.join(L)


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
            kjler.append({"tur": kod, "kulakcik": "", "satir1": tek_satir(metin.get(t["ust"], t["etiket"])),
                          "satir2": tek_satir(metin.get(t["alt"], "")) if t.get("alt") else ""})
    for o in plan["ozeller"]:
        t = turler[o["kod"]]
        kjler.append({"tur": o["kod"], "kulakcik": "", "satir1": tek_satir(metin.get(t["ust"], t["etiket"])), "satir2": ""})
    return {"bolumler": [{"baslik": "Örnek (sahneden)", "kjler": kjler}]}


# =========================================================================
#  KUMANDA PANELI (Main.Designer.cs)
# =========================================================================
URETILMIS = re.compile(r"^(btn_tek_ver|btn_cift_ver|btn_KjAl|lbl_Bant|lbl_Kulakcik|lbl_YayinTuru|cbx_bant_\w+|cbx_kul_\w+|btn_ozel_\w+|btn_oge_\w+)$")


def _slug(s: str, kullanilan: set) -> str:
    b = ident(s or "normal").lower().lstrip("@") or "x"
    a, i = b, 2
    while a in kullanilan:
        a, i = f"{b}{i}", i + 1
    kullanilan.add(a)
    return a


def kumanda_kontrolleri(plan: dict) -> tuple[list, int]:
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

    etiket("lbl_YayinTuru", "YAYINDA: -", 12, y, 614, 28, size="11.25F", renk="DarkRed")
    y += 34

    kul3 = set()
    for i, o in enumerate(plan["ozeller"]):
        r, c = divmod(i, 3)
        btn(f"btn_ozel_{_slug(o['kod'], kul3)}_ver", o["etiket"], 12 + c * 202, y + r * 54, 196, 48, "LimeGreen",
            tag=o["kod"], olay="btn_ozel_ver_Click")
    if plan["ozeller"]:
        y += math.ceil(len(plan["ozeller"]) / 3) * 54

    kul4 = set()
    for i, o in enumerate(plan["ogeler"]):
        r, c = divmod(i, 3)
        x = 12 + c * 208
        s = _slug(o["anahtar"], kul4)
        btn(f"btn_oge_{s}_ver", o["etiket"], x, y + r * 54, 140, 48, "LimeGreen", tag=o["anahtar"],
            olay="btn_oge_ver_Click", font="Candara\", 9.75F")
        btn(f"btn_oge_{s}_al", "AL", x + 144, y + r * 54, 56, 48, enabled=False, tag=o["anahtar"],
            olay="btn_oge_al_Click", font="Candara\", 9.75F")
    if plan["ogeler"]:
        y += math.ceil(len(plan["ogeler"]) / 3) * 54
    return ctl, y + 6


def designer_kumanda_yaz(designer: str, plan: dict) -> tuple[str, list[str]]:
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

    ctl, gerek = kumanda_kontrolleri(plan)
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

    # yerlesim: kumanda grubu 200..627 (tasarim yuksekligi 681); sigmazsa yukari uzar, KJ listesi kisalir
    ust = 200
    if gerek > 427:
        ust = max(120, 627 - gerek)
        if 627 - ust < gerek:
            notlar.append(f"Kumanda paneli cok kalabalik ({gerek} px); bazi kontroller tasabilir, Designer'da duzenleyin.")
    yuk = 627 - ust
    for desen, yeni in [(r"grp_Kumanda\.Location = new Point\(818, \d+\)", f"grp_Kumanda.Location = new Point(818, {ust})"),
                        (r"grp_Kumanda\.Size = new Size\(638, \d+\)", f"grp_Kumanda.Size = new Size(638, {yuk})"),
                        (r"pnl_Degerler\.Location = new Point\(312, \d+\)", f"pnl_Degerler.Location = new Point(312, {ust})"),
                        (r"pnl_Degerler\.Size = new Size\(500, \d+\)", f"pnl_Degerler.Size = new Size(500, {675 - ust})"),
                        (r"dgv_KjListesi\.Size = new Size\(1144, \d+\)", f"dgv_KjListesi.Size = new Size(1144, {ust - 40})")]:
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
        d, notlar = designer_kumanda_yaz(open(dp, encoding="utf-8-sig").read(), plan)
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
            d, notlar = designer_kumanda_yaz(open(dp, encoding="utf-8-sig").read(), plan)
            open(dp, "w", encoding="utf-8-sig").write(d)
            rapor += notlar + ["Kumanda paneli yeniden dizildi."]
        elif any(x.startswith(("bantlar:", "kulakciklar:", "ozeller:", "ogeler:")) for x in rapor):
            rapor.append("Panelde yeni/kalkan buton var: --arayuz ile yeniden dizin ya da Designer'da elle ekleyin/silin.")
        rapor.append(f"Guncellendi: {proje}")

    # her iki modda: sahneye bagli dosyalar
    with open(os.path.join(proje, "KjTipleri.Sahne.cs"), "w", encoding="utf-8-sig") as f:
        f.write(sahne_cs(plan))
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
