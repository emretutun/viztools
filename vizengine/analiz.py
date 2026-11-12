"""
Sahne analizi: tarama modelinden (template.build_scene_model / via.read_via) reji uygulamasi icin
TASLAK kumanda plani cikarir. Karar vermez, oneri yapar; belirsizlikler 'sorular' listesine yazilir.

Yontem
  1. Grafik grubu: alt director'lari arasinda bir giris (IN / GIRIS / START) ve bir cikis (OUT / CIKIS)
     olan director. Ornek: $KJ$TEK_KJ  ->  $KJ$TEK_KJ$IN, $KJ$TEK_KJ$OUT
  2. Grubun metin alanlari: grubun alt agacindaki director'larin animasyon uyguladigi container'lardan
     metni olanlar (tarama --details ile alinmis olmali). Ayni adli birden fazla container varsa
     ad olarak gruba en cok benzeyen atasi olan secilir.
  3. Sinif:
       tur       : metin alani var ve gorunur (1 alan = tekli, 2+ = ciftli)
       kulakcik  : metin alanlari var ama kendisi ya da atasi gizli (Artist'te gozu kapali) -> bandin
                   ustune eklenen grafik; metin yazilmaz
       oge       : metin alani yok (logo, kapak, saat, metinsiz kulakcik ...) -> ayri VER/AL
  4. Bant onerisi: tur adlarindan TEK/CIFT/KJ ve sondaki rakamlar atilinca ayni kalan turler eslesir
     (TEK_KJ_YAS + CIFT_KJ_YAS -> YAS, AZ_SONRA_DSF2_TEKKJ + AZ_SONRA_DSF1_KJ -> AZ_SONRA_DSF).
     Tek basina kalan ciftli tur bant olur (tekli de ayni turu kullanir), tek basina kalan tekli tur
     kendi butonu olan 'ozel' tur olur (ISIMLIK, LOKASYON gibi).
"""
from __future__ import annotations

import json
import os
import re

from .gen_csharp import short_paths, _UNNAMED, tek_satir

GIRIS_ADLARI = {"IN", "GIRIS", "START", "VER"}
CIKIS_ADLARI = {"OUT", "CIKIS", "AL", "END"}
_TEMIZLE = {"TEK", "CIFT", "KJ", "TEKKJ", "CIFTKJ"}


def _anahtar(ad: str) -> str:
    """Tur adindan bant anahtari: TEK/CIFT/KJ ve rakam soneklerini at."""
    parcalar = []
    for p in ad.upper().split("_"):
        p = re.sub(r"(?<=[A-Z])\d+$", "", p)   # DSF1 -> DSF; tek basina sayi (4) kalir
        if p and p not in _TEMIZLE:
            parcalar.append(p)
    return "_".join(parcalar)


def _benzerlik(a: str, b: str) -> int:
    a, b = a.upper(), b.upper()
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    ortak = len(set(a.split("_")) & set(b.split("_")))
    return n + 10 * ortak


def _etiket(ad: str) -> str:
    tr = {"CIFT": "ÇİFT", "SAG": "SAĞ", "DAKIKA": "DAKİKA", "GELISME": "GELİŞME", "ISIMLIK": "İSİMLİK", "ISIM": "İSİM",
          "BAGLANTI": "BAĞLANTI", "GORUNTULU": "GÖRÜNTÜLÜ", "BAGLANTISI": "BAĞLANTISI"}
    return " ".join(tr.get(p, p) for p in ad.upper().split("_") if p and p != "KJ") or ad


def _isim_alanlari(cons: list, director_yolu: str, telefon: bool) -> list:
    """
    Isim / telefon grafiginin yazi alanlari adindan bulunur (director yazi alanina animasyon uygulamiyorsa):
    ISIMLIK_KJ + TITR_KJ, TEL_ISIMLIK_KJ + TEL_TITR_KJ gibi. Ayni ust grupta, gorunur, adi en sade olan secilir.
    """
    kok = "$" + director_yolu.split("$")[1] + "$"

    def sec(anahtar):
        aday = []
        for c in cons:
            p = [x for x in re.split(r"[_\-]+", c["name"].upper()) if x]
            if "text" not in c or c.get("active") is False or not c["name_path"].startswith(kok):
                continue
            if not any(x.startswith(anahtar) for x in p) or {"LINK", "FOTOLU", "FOTO", "HK", "TEK"} & set(p):
                continue
            if ("TEL" in p or "TELEFON" in p) != telefon:
                continue
            aday.append((len(p), cons.index(c), c))
        return min(aday)[2] if aday else None

    isim, titr = sec("ISIM"), sec("TITR")
    return [x for x in (isim, titr) if x] if isim else []


def analiz_et(model: dict) -> dict:
    dirs = [d for d in model["directors"] if re.search(r"[0-9A-Za-z]", d["name"])]
    cons = model["containers"]
    kisa = short_paths(cons)
    con_by_name: dict[str, list[dict]] = {}
    for c in cons:
        con_by_name.setdefault(c["name"], []).append(c)
    by_path = {c["name_path"]: c for c in cons}
    detay_var = any("text" in c or c.get("active") is not None for c in cons)

    # Iki desen: (a) X$IN + X$OUT alt director'lari, (b) kardes director'lar X + X_OUT (HT_SPOR tipi)
    adaylar_grup = []
    yol = {d["name_path"]: d for d in dirs}
    for g in dirs:
        alt = [d for d in dirs if d["name_path"].startswith(g["name_path"] + "$")]
        cocuk = [d for d in alt if d["name_path"].count("$") == g["name_path"].count("$") + 1]
        giris = next((d for d in cocuk if d["name"].upper() in GIRIS_ADLARI), None)
        cikis = next((d for d in cocuk if d["name"].upper() in CIKIS_ADLARI), None)
        if giris and cikis:
            adaylar_grup.append((g["name"], g, giris, cikis, [g] + alt, cocuk))
            continue
        # (c) kardes director'lar X_IN + X_OUT (TELEFON_FOTOLU_IN / TELEFON_FOTOLU_OUT gibi)
        mi = re.match(r"^(.+)_(IN|GIRIS)$", g["name"], re.I)
        if mi:
            ust_yol = g["name_path"].rsplit("$", 1)[0]
            ko = yol.get(f"{ust_yol}${mi.group(1)}_OUT") or yol.get(f"{ust_yol}${mi.group(1)}_CIKIS")
            if ko:
                ara = [d for d in dirs if d["name_path"].rsplit("$", 1)[0] == ust_yol
                       and d["name"].upper().startswith(mi.group(1).upper() + "_") and d not in (g, ko)]
                adaylar_grup.append((mi.group(1), g, g, ko, [g] + alt + [ko], ara))
                continue
        if g["name"].upper().endswith(("_OUT", "_CIKIS", "_OUT_ANIM", "_IN", "_GIRIS")) or g["name"].upper() in GIRIS_ADLARI | CIKIS_ADLARI:
            continue
        ust_yol = g["name_path"].rsplit("$", 1)[0]
        kardes_out = yol.get(f"{ust_yol}${g['name']}_OUT") or yol.get(f"{ust_yol}${g['name']}_CIKIS")
        if kardes_out:
            kardes_anim = yol.get(f"{ust_yol}${g['name']}_OUT_ANIM")
            adaylar_grup.append((g["name"], g, g, kardes_out,
                                 [g] + alt + [kardes_out] + ([kardes_anim] if kardes_anim else []), []))

    gruplar, sorular = [], []
    for grup_adi, g, giris, cikis, kapsam, cocuk in adaylar_grup:
        # grubun animasyon uyguladigi container adlari
        anim_adlari = []
        for d in kapsam:
            for a in d.get("animated", []):
                if a.get("container") and a["container"] not in anim_adlari:
                    anim_adlari.append(a["container"])
        metinler = []
        for ad in anim_adlari:
            adaylar = [c for c in con_by_name.get(ad, []) if "text" in c]
            if not adaylar:
                continue
            kok = "$" + g["name_path"].split("$")[1] + "$"
            en_iyi = max(adaylar, key=lambda c: (c["name_path"].startswith(kok),
                                                 max([_benzerlik(grup_adi, p) for p in c["name_path"].split("$") if p] + [0])))
            metinler.append(en_iyi)
        # Adi metin alani gibi olanlar (TEXT, YAZI, SATIR, ISIM, TITLE...) varsa, digerleri sabit etikettir
        # (orn. "AZ SONRA" yazan Gotham-Bold); onlari disarida birak.
        anlamli = [c for c in metinler if re.search(r"TEXT|YAZI|SATIR|ISIM|TITLE|TITR|BASLIK|METIN", c["name"].upper())]
        if anlamli:
            metinler = anlamli
        # ust / alt sirasi: adinda UST/ALT gecene gore, yoksa agac sirasi
        metinler.sort(key=lambda c: (0 if "UST" in c["name"].upper() else 2 if "ALT" in c["name"].upper() else 1, cons.index(c)))
        gizli = False
        for c in metinler:
            parcalar = c["name_path"].split("$")[1:]
            for i in range(1, len(parcalar)):
                ata = by_path.get("$" + "$".join(parcalar[:i]))
                if ata is not None and ata.get("active") is False and ata["name"] not in _UNNAMED:
                    gizli = True
        if not metinler and re.search(r"ISIM|TELEFON|(^|_)TEL(_|$)", grup_adi.upper()) and not re.search(r"FOTO|SONDK", grup_adi.upper()):
            metinler = _isim_alanlari(cons, g["name_path"], telefon=not re.search(r"ISIM", grup_adi.upper()))
        if re.search(r"URUN_YERLESTIRME", grup_adi.upper()):
            metinler = []   # yazisi sabit etiket: canli uygulamalar yazi gondermeden oynatir
        diger = [d["name"] for d in cocuk if d not in (giris, cikis)]
        sinif = "oge" if not metinler else ("kulakcik" if gizli else "tur")
        if sinif == "kulakcik" and diger:
            sinif = "sayfali"   # gizli + yazili + ara animasyonlu: sayfa sayfa ilerleyen grafik (FLOT gibi)
        if any(x["kod"] == grup_adi for x in gruplar):
            ust_ad = g["name_path"].rsplit("$", 1)[0].rsplit("$", 1)[-1]
            on_ek = re.sub(r"^KJ_|_ALL$|_GROUP$", "", ust_ad.upper()) or ust_ad.upper()
            grup_adi = f"{on_ek}_{grup_adi}"
        gruplar.append({
            "kod": grup_adi, "etiket": _etiket(grup_adi), "sinif": sinif,
            "ust_yol": g["name_path"].rsplit("$", 1)[0],
            "giris": giris["name_path"], "cikis": cikis["name_path"],
            "ust": kisa.get(metinler[0]["name_path"], "").lstrip("!") if metinler else None,
            "alt": kisa.get(metinler[1]["name_path"], "").lstrip("!") if len(metinler) > 1 else None,
            "metin_sayisi": len(metinler),
            "ornek_metin": [tek_satir(m.get("text", ""))[:40] for m in metinler],
            "diger_alt_director": diger,
        })
        if len(metinler) > 2:
            sorular.append(f"{grup_adi}: {len(metinler)} yazı alanı var ({', '.join(m['name'] for m in metinler)}). "
                           "Uygulama yalnızca ilk ikisine yazar. Sayfalı bir grafikse (ROLL, DUA, FLOT gibi) üretici bunu "
                           "henüz desteklemiyor; listeden işaretini kaldırıp sonradan elle ekleyin.")
        if sinif == "sayfali":
            sorular.append(f"{grup_adi}: sayfa sayfa ilerleyen bir grafik gibi görünüyor ({', '.join(diger)} animasyonu var). "
                           "Üretici bunu henüz desteklemiyor; uygulamaya alınmadı, sonradan elle eklenir.")
        elif diger:
            sorular.append(f"{grup_adi}: giriş ve çıkış dışında başka animasyonlar da var ({', '.join(diger)}). "
                           "Uygulama bunları oynatmaz. Ayrı buton gerekiyorsa sonradan elle eklenir.")
        if any(kisa.get(m["name_path"], "").startswith("!") for m in metinler):
            sorular.append(f"{grup_adi}: yazı alanının adı sahnede birden fazla yerde geçiyor; uygulama ilk bulduğuna yazar. "
                           "Yanlış yere yazarsa sahnede o container'a tekil bir ad verin.")

    # ---- cift yuvali grafikler: X_1 / X_2 ayni grafigin iki yuvasidir (metin degisirken biri cikar digeri girer).
    #      Uygulama tek yuva kullanir: en kucuk numarali kalir, digerleri plana alinmaz.
    aileler: dict[tuple[str, str], list[tuple[int, dict]]] = {}
    for t in gruplar:
        m = re.match(r"^(.*?)_(\d+)$", t["kod"])
        if m:   # ayni yerde (ayni ust director altinda) duranlar ayni ailedir
            aileler.setdefault((t["ust_yol"], m.group(1).upper()), []).append((int(m.group(2)), t))
    yuvali = []
    for (_, taban), uyeler in aileler.items():
        if len(uyeler) < 2 or len({(t["sinif"], t["alt"] is None) for _, t in uyeler}) != 1:
            continue
        uyeler.sort(key=lambda x: x[0])
        ana = uyeler[0][1]
        ana["ad"] = taban
        ana["etiket"] = _etiket(taban)
        ana["_yuvalar"] = [t for _, t in uyeler[1:] if t["ust"]]
        for _, t in uyeler[1:]:
            t["sinif"] = "yuva"
        yuvali.append(f"{taban} ({', '.join(t['kod'] for _, t in uyeler)})")
    if yuvali:
        sorular.append("Bu sahnede bazı grafikler iki yuvalı kurulmuş: " + "; ".join(yuvali) + ". "
                       "Grafik yayındayken yeni yazı verilince uygulama grafiği almadan öbür yuvaya geçer. "
                       "Bir şey yapmanız gerekmez.")

    # ---- ortak cikis: ayni yerde duran turlerin hepsini birden alan director (KJ_FULL_OUT, GENEL_KJ_OUT gibi).
    #      Canli uygulamalar KJ AL'da yuva cikislarini degil bunu oynatir; ayni cikisi paylasan turler arasinda
    #      (tekli <-> ciftli) gecis de cikis yapmadan dogrudan olur.
    ortaklar = []
    for d in dirs:
        if re.search(r"(^|_)(FULL|GENEL|TUM|HEPSI|ALL)(_KJ)?_(OUT|CIKIS)$", d["name"].upper()):
            ust_yol = d["name_path"].rsplit("$", 1)[0]
            # isim / telefon bandin yaninda durur ama kendi cikisiyla alinir; ortak cikis yalnizca bant satirlarinindir
            uyeler = [t for t in gruplar if t["ust_yol"] == ust_yol and t["sinif"] in ("tur", "yuva") and t["cikis"] != d["name_path"]
                      and not re.search(r"ISIM|TELEFON|(^|_)TEL(_|$)", t["kod"].upper())]
            if uyeler:
                for t in uyeler:
                    t["cikis"] = d["name_path"]
                ortaklar.append(f"{d['name']} ({', '.join(t.get('ad', t['kod']) for t in uyeler if t['sinif'] == 'tur')})")
    if ortaklar:
        sorular.append("Ortak çıkış bulundu: " + "; ".join(ortaklar) + ". KJ AL bu animasyonu oynatır. Bir şey yapmanız gerekmez.")

    # ---- bant onerisi ----
    ad = lambda t: t.get("ad", t["kod"])
    turler = [t for t in gruplar if t["sinif"] == "tur"]
    gruplu: dict[str, list[dict]] = {}
    for t in turler:
        gruplu.setdefault(_anahtar(ad(t)), []).append(t)
    bantlar, ozeller, yalniz_ciftli = [], [], []

    # Satir bazli bant (NTR HT sahnesi): ust ve alt satir ayri director'la girer (UST_KJ_DEGIS / ALT_KJ_DEGIS),
    # alt satir ayri alinir (ALT_KJ_OUT), ciftli = tekli + alt satir. Ayni yerdeki UST_x / ALT_x cifti tek banttir.
    satirli = set()
    for u in turler:
        if not re.search(r"(^|_)UST_", ad(u)) or u["alt"] is not None:
            continue
        alt_ad = re.sub(r"(^|_)UST_", r"\1ALT_", ad(u), count=1)
        a = next((t for t in turler if ad(t) == alt_ad and t["ust_yol"] == u["ust_yol"] and t["alt"] is None), None)
        if not a:
            continue
        cikislar = sorted((d for d in dirs if d["name_path"].rsplit("$", 1)[0] == u["ust_yol"]
                           and re.fullmatch(r"ALT_(\w+_)?(OUT|CIKIS)", d["name"].upper()) and "DEGIS" not in d["name"].upper()),
                          key=lambda d: len(d["name"]))
        if not cikislar:
            continue
        ilk = not bantlar
        yer = re.sub(r"^KJ_|_ALL$|_GROUP$", "", u["ust_yol"].rsplit("$", 1)[-1].upper())
        bantlar.append({"anahtar": "" if ilk else yer, "etiket": "NORMAL" if ilk else _etiket(yer), "tek": u["kod"], "cift": u["kod"],
                        "alt_satir": a["kod"], "alt_cikis": cikislar[0]["name_path"]})
        satirli |= {u["kod"], a["kod"]}
        u["etiket"], a["etiket"] = ("ÜST SATIR", "ALT SATIR") if ilk else (_etiket(yer) + " ÜST", _etiket(yer) + " ALT")
    if satirli:
        sorular.append("Bu sahnede alt bant satır satır kurulmuş: üst ve alt satır ayrı animasyonla giriyor. Uygulama TEKLİ'de üst "
                       "satırı, ÇİFTLİ'de üst satırın ardından alt satırı verir; yazı değişince yalnızca değişen satır döner. "
                       "Bir şey yapmanız gerekmez.")
        # bandin kendi parcalari (UST_KJ, ALT_KJ gibi yazisiz director'lar) ayri buton olmaz
        yerler = {t["ust_yol"] for t in turler if t["kod"] in satirli}
        for o in gruplar:
            if o["sinif"] == "oge" and o["ust_yol"] in yerler and re.fullmatch(r"(UST|ALT)_KJ|KJ", o["kod"].upper()):
                o["sinif"] = "bant_parcasi"
    for t in turler:
        if t["kod"] in satirli:
            gruplu[_anahtar(ad(t))] = [x for x in gruplu.get(_anahtar(ad(t)), []) if x["kod"] not in satirli]

    for anahtar, liste in gruplu.items():
        tekli = [t for t in liste if t["alt"] is None]
        ciftli = [t for t in liste if t["alt"] is not None]
        if tekli and ciftli:
            bantlar.append({"anahtar": anahtar, "etiket": _etiket(anahtar) if anahtar else "NORMAL",
                            "tek": tekli[0]["kod"], "cift": ciftli[0]["kod"]})
            for fazla in tekli[1:] + ciftli[1:]:
                sorular.append(f"{fazla['kod']}: '{anahtar or 'NORMAL'}' bandinda birden fazla aday var; hangisi kullanilacak?")
        elif ciftli:
            yalniz_ciftli += ciftli
        else:
            for t in tekli:
                ozeller.append({"kod": t["kod"], "etiket": t["etiket"] + " VER"})
    # Tek basina kalan iki satirli tur: ana bantla ayni yerde duruyorsa banttir (SAG DSF, UZUN gibi),
    # baska yerde duruyorsa kendi butonu olan ayri grafiktir (isim + unvan, telefon gibi).
    normal = next((b for b in bantlar if b["anahtar"] == ""), None)
    normal_yeri = next((t["ust_yol"] for t in turler if normal and t["kod"] == normal["tek"]), None)
    for t in yalniz_ciftli:
        isim_gibi = re.search(r"ISIM|TELEFON|(^|_)TEL(_|$)|KONUK", t["kod"].upper())   # isim + unvan: bant degil
        if not isim_gibi and (normal_yeri is None or t["ust_yol"] == normal_yeri):
            bantlar.append({"anahtar": _anahtar(ad(t)) or t["kod"], "etiket": t["etiket"], "tek": t["kod"], "cift": t["kod"]})
        else:
            ozeller.append({"kod": t["kod"], "etiket": t["etiket"] + " VER"})
    # NORMAL bant basa
    bantlar.sort(key=lambda b: (b["anahtar"] != "", b["etiket"]))
    if not any(b["anahtar"] == "" for b in bantlar):
        sorular.append("Ana KJ bandını bulamadım. Sağdaki listede BANT bölümünde, her zaman kullandığınız "
                       "normal bandın satırındaki \"ana bant\" seçeneğini işaretleyin.")

    kulakciklar = [{"anahtar": _anahtar(k["kod"]) or k["kod"], "etiket": _etiket(_anahtar(k["kod"]) or k["kod"]).replace("4 5G", "4.5G"),
                    "giris": k["giris"], "cikis": k["cikis"]}
                   for k in gruplar if k["sinif"] == "kulakcik"]
    ogeler = [{"anahtar": o["kod"].lower(), "etiket": o["etiket"], "giris": o["giris"], "cikis": o["cikis"]}
              for o in gruplar if o["sinif"] == "oge"]
    if ogeler:
        sorular.append("Yazısı olmayan grafikler (" + ", ".join(o["etiket"] for o in ogeler) + ") için ayrı VER ve AL butonu konuyor. "
                       "Böyle kalabilir. Bunlardan biri KJ ile birlikte girip çıkıyorsa (4.5G, SKYPE gibi bir kulakçıksa) "
                       "listede sağındaki seçimi \"kulakçık\" yapın.")
    if not detay_var:
        sorular.insert(0, "Tarama --details olmadan yapilmis: metin ve gorunurluk bilgisi yok, siniflandirma eksik olur. "
                          "vizscan.py --details ile yeniden tarayin.")
    kapali = [d["name_path"] for d in model["directors"] if d.get("open") is False and re.search(r"[0-9A-Za-z]", d["name"])]
    if kapali:
        sorular.insert(0, f"{len(kapali)} director Artist'te kapalı olduğu için içi okunamadı: " + ", ".join(kapali[:12])
                       + ("..." if len(kapali) > 12 else "") + ". Artist'te Stage panelinde bu dalları açıp sahneyi kaydedin, sonra yeniden tarayın.")

    # Ozel butonlar banttan bagimsizdir (KJ ekrandayken verilir, kendi AL'i vardir). Isim ve telefon ayni yeri
    # paylasir: biri girerken digeri cikar. Digerleri kendi alanindadir.
    ozel_kodlar = {o["kod"] for o in ozeller}

    def alan(t):
        if t["kod"] not in ozel_kodlar:
            return None
        k = t["kod"].upper()
        return "isimlik" if re.search(r"ISIM|TELEFON|(^|_)TEL(_|$)", k) and "FOTO" not in k else t["kod"].lower()

    # ---- canli uygulamalardan ogrenilen ayrintilar (REJI_KALIPLARI.md) ----
    tam_yol = {v.lstrip("!"): k for k, v in kisa.items() if v}

    def ayirac_bul(alt_yol):
        """Alt satirin yanindaki ayirac (isim / unvan arasindaki cizgi): alt satir bosken gizlenir."""
        if not alt_yol:
            return None
        tam = tam_yol.get(alt_yol, alt_yol)
        aday = [c for c in cons if re.fullmatch(r"AY[IR]R?A[CÇ]|AYRAC|AYIRICI|SEPARATOR|SEPERATOR|CIZGI", c["name"].upper())
                and c["name_path"].count("$") > 1 and tam.startswith(c["name_path"].rsplit("$", 1)[0] + "$")]
        return max(aday, key=lambda c: len(c["name_path"]))["name_path"] if aday else None

    def resim_bul(t):
        """Fotografli grafigin resim container'i (adindan): ..._IMAGE_SEC, FOTO, RESIM."""
        if not re.search(r"FOTO|RESIM", t["kod"].upper()) or not t["ust"]:
            return None
        kok = "$" + tam_yol.get(t["ust"], t["ust"]).split("$")[1] + "$"
        aday = [c for c in cons if c["name_path"].startswith(kok) and "text" not in c
                and re.search(r"(FOTO|IMAGE|IMG|RESIM)\w*_(SEC|SELECT)$|^(FOTO|RESIM|IMAGE)$", c["name"].upper())]
        return (kisa.get(aday[0]["name_path"], "").lstrip("!") or aday[0]["name_path"]) if len(aday) == 1 else None

    def tur_kaydi(t):
        k = {"kod": t["kod"], "etiket": t["etiket"], "giris": t["giris"], "cikis": t["cikis"], "ust": t["ust"], "alt": t["alt"]}
        if t.get("_yuvalar"):   # her yuvanin kendi cikisi da tutulur: AL'da hepsi oynatilir (hangi yuva ekrandaysa o cikar)
            k["yuvalar"] = [{"giris": y["giris"], "cikis": y["cikis"], "ust": y["ust"], "alt": y["alt"]} for y in t["_yuvalar"]]
            for y in k["yuvalar"]:
                if ayirac_bul(y["alt"]):
                    y["ayirac"] = ayirac_bul(y["alt"])
        if alan(t):
            k["alan"] = alan(t)
        if ayirac_bul(t["alt"]):
            k["ayirac"] = ayirac_bul(t["alt"])
        if resim_bul(t):
            k["resim"] = {"container": resim_bul(t)}
        return k

    # Ozel turun metin kaynagi ve kisayolu. Canli uygulamalarda isim / telefon ayri bir ISIMLER listesinden
    # (isim + unvan), lokasyon gibi tek satirlik etiketler kendi kutusundan verilir; F3 isim, F2 telefon, F4 AL.
    tur_by_kod = {t["kod"]: t for t in turler}
    bos_tuslar = {"ISIM": "F3", "TEL": "F2"}
    for o in ozeller:
        k = o["kod"].upper()
        isim_gibi = bool(re.search(r"ISIM|TELEFON|(^|_)TEL(_|$)|KONUK|TITR", k))
        if isim_gibi:
            o["kaynak"] = "isim"
        elif tur_by_kod[o["kod"]]["alt"] is None and re.search(r"LOKASYON|KONUM|SEHIR|CANLI|ETIKET", k):
            o["kaynak"] = "kutu"
        if isim_gibi and "FOTO" not in k:
            for parca, tus in list(bos_tuslar.items()):
                if parca in k:
                    o["tus"] = tus
                    del bos_tuslar[parca]
                    if "F4" not in [x.get("al_tus") for x in ozeller]:
                        o["al_tus"] = "F4"
                    break
    if any(o.get("kaynak") == "isim" for o in ozeller):
        sorular.append("İsim / telefon gibi grafiklerin yazısı ayrı bir İSİMLER listesinden (isim + ünvan) verilir; "
                       "lokasyon gibi tek satırlık etiketlerin kendi yazı kutusu olur. Bir şey yapmanız gerekmez.")

    # Yazili oge: adini tasiyan container'in altinda tek bir yazi alani varsa (yazili logo gibi) VER'de o da yazilir.
    for o in ogeler:
        kod = next((g["kod"] for g in gruplar if g["giris"] == o["giris"]), "")
        yazilar = [c for kap in con_by_name.get(kod, []) for c in cons
                   if "text" in c and c["name_path"].startswith(kap["name_path"] + "$")]
        # Yalnizca logo / etiket gibi adlarda; yazi alani da adindan secilir (logo_text; golge ve parlama kopyalari degil).
        adli = sorted([c for c in yazilar if re.search(r"TEXT|YAZI|METIN", c["name"].upper())
                       and re.search(r"LOGO|ETIKET|BASLIK", c["name"].upper())], key=lambda c: len(c["name"]))
        if not adli and re.search(r"LOGO|CORNER", kod.upper()):   # logo yazisi baska grupta: ayni ust grupta LOGO..TEXT adli alan
            kok = "$" + o["giris"].split("$")[1] + "$"
            adli = sorted([c for c in cons if "text" in c and c["name_path"].startswith(kok) and c.get("active") is not False
                           and {"LOGO", "TEXT"} <= set(c["name"].upper().split("_"))],
                          key=lambda c: (not c.get("text"), len(c["name"])))
        if adli and re.search(r"LOGO|ETIKET|BASLIK|CORNER", kod.upper()):
            o["metin"] = {"container": kisa.get(adli[0]["name_path"], "").lstrip("!") or adli[0]["name_path"]}
            o["kj_ile"] = False   # "KJ ile" kutusu gorunur, isaretsiz baslar

    sonuc = {
        "sahne": model["scene"]["name"],
        "turler": [tur_kaydi(t) for t in turler],
        "bantlar": bantlar,
        "kulakciklar": kulakciklar,
        "ozeller": ozeller,
        "ogeler": ogeler,
        "sorular": sorular,
        "_gruplar": gruplar,
    }
    ogrenileni_uygula(sonuc)
    return sonuc


OGRENILEN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ogrenilen")


def ogrenileni_uygula(an: dict) -> None:
    """
    Sahneden okunamayan, canli uygulamadan ogrenilmis ayarlari analize isler: ogrenilen/<sahne adi>.json.
    Bicim: {"fon": {...}, "turler" | "ozeller" | "ogeler" | "bantlar": {anahtar: {alan: deger | null (sil)}},
            "cikar": {grup: [anahtar]}, "ekle": {grup: [kalem]}}
    """
    yol = os.path.join(OGRENILEN, an["sahne"] + ".json")
    if not os.path.exists(yol):
        return
    with open(yol, encoding="utf-8") as f:
        o = json.load(f)
    for grup, anahtar in (("turler", "kod"), ("ozeller", "kod"), ("ogeler", "anahtar"), ("bantlar", "anahtar")):
        cikar = set(o.get("cikar", {}).get(grup, []))
        an[grup] = [x for x in an[grup] if x[anahtar] not in cikar]
        for x in an[grup]:
            for k, v in (o.get(grup, {}).get(x[anahtar]) or {}).items():
                if v is None:
                    x.pop(k, None)
                else:
                    x[k] = v
        mevcut = {x[anahtar] for x in an[grup]}
        an[grup] += [x for x in o.get("ekle", {}).get(grup, []) if x[anahtar] not in mevcut]
    if o.get("fon"):
        an["fon"] = o["fon"]
    if o.get("kelebek_ayar"):   # kelebeklerin katmani / arka plan klibi (ayni programin kelebek sahneleri icin)
        an["kelebek_ayar"] = o["kelebek_ayar"]
    an["sorular"].append(f"Bu sahne için canlı uygulamadan öğrenilmiş ayarlar uygulandı (ogrenilen\\{an['sahne']}.json): "
                         "zemin (FON) seçenekleri, logo yazısı, buton adları. Bir şey yapmanız gerekmez.")


def rapor(a: dict) -> str:
    L = [f"# Sahne analizi: {a['sahne']}", ""]
    L.append(f"{len(a['turler'])} metinli tür, {len(a['bantlar'])} bant, {len(a['kulakciklar'])} kulakçık, "
             f"{len(a['ozeller'])} özel tür, {len(a['ogeler'])} metinsiz grafik.")
    L += ["", "## Bantlar (TEKLİ / ÇİFTLİ)", "", "| Bant | Tekli | Çiftli |", "|---|---|---|"]
    L += [f"| {b['etiket']} | {b['tek']} | {b['cift']} |" for b in a["bantlar"]]
    L += ["", "## Kulakçıklar (bandın üstüne eklenir, metin yazılmaz)", ""]
    L += [f"- {k['etiket']}: `{k['giris']}`" for k in a["kulakciklar"]] or ["- yok"]
    L += ["", "## Özel türler (kendi VER butonu, tek satır)", ""]
    L += [f"- {o['etiket']} ({o['kod']})" for o in a["ozeller"]] or ["- yok"]
    L += ["", "## Metinsiz grafikler (ayrı VER/AL)", ""]
    L += [f"- {o['etiket']}: `{o['giris']}`" for o in a["ogeler"]] or ["- yok"]
    L += ["", "## Gruplar (ham)", "", "| Grup | Sınıf | Üst | Alt | Örnek metin |", "|---|---|---|---|---|"]
    L += [f"| {g['kod']} | {g['sinif']} | `{g['ust'] or '-'}` | `{g['alt'] or '-'}` | {' / '.join(g['ornek_metin'])} |" for g in a["_gruplar"]]
    L += ["", "## Sorular (rejiye sorulacak)", ""]
    L += [f"{i}. {s}" for i, s in enumerate(a["sorular"], 1)] or ["- yok"]
    return "\n".join(L) + "\n"
