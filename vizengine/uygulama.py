"""
Sahneden reji uygulamasi: ortak akis (vizapp.py komut satiri ve vizscan_web.py arayuzu kullanir).

  taslak_plan(model, an, ad, sahne, ...)  -> analizden yeni plan
  mevcut_uygulamalar()                    -> source\\repos altinda viztools ile uretilmis uygulamalar
  karsilastir(plan, an, model)            -> sahnede yeni olanlar + planin sahnede bulamadiklari
  uygula(plan, hedef, tarama, ...)        -> uret (+ derle); satir satir rapor
"""
import json
import os
import re

from .template import write_outputs
from .uretec import uret, derle, dogrula, UretimHatasi  # noqa: F401

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENES = os.path.join(KOK, "scenes")
REPOS = os.path.join(os.path.expanduser("~"), "source", "repos")
PLAN_ALANLARI = ("turler", "bantlar", "kulakciklar", "ozeller", "ogeler")


def namespace_yap(ad: str) -> str:
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    s = re.sub(r"[^A-Za-z0-9]+", "_", (ad or "").translate(tr)).strip("_")
    return ("_" + s) if s[:1].isdigit() else (s or "Reji_Uygulamasi")


def varsayilan_hedef(ad: str) -> str:
    return os.path.join(REPOS, namespace_yap(ad))


def tarama_yaz(model: dict) -> str:
    """Taramayi scenes\\<Sahne>\\ altina yazar, JSON yolunu dondurur."""
    jp, _ = write_outputs(model, SCENES)
    return jp


def taslak_plan(model: dict, an: dict, ad: str, sahne: str, kelebek: str = "", namespace: str = "", tarama: str = "") -> dict:
    plan = {"uygulama": ad, "namespace": namespace or namespace_yap(ad), "sahne": sahne,
            "kelebek_klasoru": kelebek or "", "tarama": tarama}
    for k in PLAN_ALANLARI:
        plan[k] = an.get(k, [])
    return plan


def plan_oku(hedef: str) -> dict | None:
    p = os.path.join(hedef, "kumanda.json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def mevcut_uygulamalar() -> list[dict]:
    out = []
    if os.path.isdir(REPOS):
        for d in sorted(os.listdir(REPOS)):
            yol = os.path.join(REPOS, d)
            plan = plan_oku(yol) if os.path.isdir(yol) else None
            if plan:
                out.append({"hedef": yol, "uygulama": plan.get("uygulama", d), "sahne": plan.get("sahne", ""),
                            "sahne_adi": (plan.get("sahne", "").rstrip("/").split("/") or [""])[-1]})
    return out


def _anahtarlar(plan: dict) -> set:
    return ({t["kod"] for t in plan.get("turler", [])}
            | {k["giris"] for k in plan.get("kulakciklar", [])}
            | {o["giris"] for o in plan.get("ogeler", [])})


def karsilastir(plan: dict, an: dict, model: dict) -> dict:
    """Mevcut plan ile yeni sahne: sahnede yeni cikanlar ve planda olup sahnede bulunmayanlar."""
    mevcut = _anahtarlar(plan)
    yeni = [t["kod"] for t in an["turler"] if t["kod"] not in mevcut] + \
           [x["giris"] for x in an["kulakciklar"] + an["ogeler"] if x["giris"] not in mevcut]
    return {"yeni": yeni, "hatalar": dogrula(plan, model)}


def kontrol_farki(eski: dict | None, yeni: dict) -> bool:
    """Paneldeki buton kumesi degisti mi (bant/kulakcik/ozel/oge eklendi, kalkti ya da etiketi degisti)."""
    if not eski:
        return True
    imza = lambda p: json.dumps([[(x.get("anahtar", x.get("kod")), x.get("etiket")) for x in p.get(k, [])]
                                 for k in ("bantlar", "kulakciklar", "ozeller", "ogeler")], ensure_ascii=False)
    return imza(eski) != imza(yeni)


def uygula(plan: dict, hedef: str, tarama: str, guncelle: bool, arayuz: bool, derle_: bool = True) -> tuple[bool, list[str]]:
    """Plani tarama klasorune yazar, uretir (uret() hedefteki kumanda.json'u kaydeder), istenirse derler."""
    plan = dict(plan, tarama=tarama)
    gecici = os.path.join(os.path.dirname(tarama), "kumanda.uretim.json")
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    rapor = list(uret(gecici, hedef, guncelle=guncelle, arayuz=arayuz))
    if not derle_:
        return True, rapor
    ok, cikti = derle(hedef)
    rapor += cikti.splitlines()
    return ok, rapor


def cozum_dosyasi(hedef: str) -> str | None:
    for uz in (".slnx", ".sln"):
        for f in os.listdir(hedef) if os.path.isdir(hedef) else []:
            if f.endswith(uz):
                return os.path.join(hedef, f)
    return None


# -------------------------------------------------------------------------
#  Duzenleyici icin kalem listesi (arayuz)
# -------------------------------------------------------------------------
GRUP_ALAN = {"bant": "bantlar", "kulakcik": "kulakciklar", "ozel": "ozeller", "oge": "ogeler"}


def _yollar(model):
    from .gen_csharp import short_paths
    dirs = {d["name_path"] for d in model["directors"]}
    cons = {v.lstrip("!") for v in short_paths(model["containers"]).values() if v} | {c["name_path"] for c in model["containers"]}
    return dirs, cons


def _tur_var(t, dirs, cons):
    return t["giris"] in dirs and t["cikis"] in dirs and t["ust"] in cons and (not t.get("alt") or t["alt"] in cons)


def kalemler(model: dict, an: dict, eski: dict | None = None) -> dict:
    """
    Duzenleyicinin gosterecegi liste. Yeni uygulamada: analizin hepsi secili.
    Guncellemede: mevcut plan secili (sahnede bulunamayanlar 'yok' ve secimsiz),
    analizde olup planda olmayanlar 'yeni' ve secimsiz (karar rejinin).
    """
    dirs, cons = _yollar(model)
    havuz = {t["kod"]: t for t in an["turler"]}
    if eski:
        for t in eski.get("turler", []):
            havuz.setdefault(t["kod"], t)
    gecerli = {k for k, t in havuz.items() if _tur_var(t, dirs, cons)}

    def durum_kontrol(grup, v):
        if grup == "bant":
            return v["tek"] in gecerli and v["cift"] in gecerli
        if grup == "ozel":
            return v["kod"] in gecerli
        return v["giris"] in dirs and v["cikis"] in dirs

    out = []
    if eski:
        for grup, alan in GRUP_ALAN.items():
            for v in eski.get(alan, []):
                ok = durum_kontrol(grup, v)
                out.append({"grup": grup, "veri": v, "secili": ok, "durum": "mevcut" if ok else "yok"})
    var_olan = [x for x in out if x["durum"] == "mevcut"]
    kapsanan_kod = {k for x in var_olan for k in ((x["veri"]["tek"], x["veri"]["cift"]) if x["grup"] == "bant"
                                            else (x["veri"]["kod"],) if x["grup"] == "ozel" else ())}
    kapsanan_dir = {x["veri"]["giris"] for x in var_olan if x["grup"] in ("kulakcik", "oge")}
    kapsanan_bant = {x["veri"]["anahtar"] for x in var_olan if x["grup"] == "bant"}
    for grup, alan in GRUP_ALAN.items():
        for v in an.get(alan, []):
            if eski:
                if grup == "bant" and (v["anahtar"] in kapsanan_bant or {v["tek"], v["cift"]} <= kapsanan_kod):
                    continue
                if grup == "ozel" and v["kod"] in kapsanan_kod:
                    continue
                if grup in ("kulakcik", "oge") and v["giris"] in kapsanan_dir:
                    continue
            out.append({"grup": grup, "veri": v, "secili": not eski, "durum": "yeni" if eski else ""})
    return {"turler": [dict(t, _gecerli=(k in gecerli)) for k, t in havuz.items()], "kalemler": out}


__all__ = ["namespace_yap", "varsayilan_hedef", "tarama_yaz", "taslak_plan", "plan_oku", "mevcut_uygulamalar",
           "karsilastir", "kontrol_farki", "uygula", "cozum_dosyasi", "dogrula", "kalemler", "UretimHatasi", "PLAN_ALANLARI", "REPOS"]
