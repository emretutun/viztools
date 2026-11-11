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
            adaylar_grup.append((g["name"], g, g, kardes_anim or kardes_out,
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
            en_iyi = max(adaylar, key=lambda c: max([_benzerlik(grup_adi, p) for p in c["name_path"].split("$") if p] + [0]))
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
        diger = [d["name"] for d in cocuk if d not in (giris, cikis)]
        sinif = "oge" if not metinler else ("kulakcik" if gizli else "tur")
        if sinif == "kulakcik" and diger:
            sinif = "sayfali"   # gizli + yazili + ara animasyonlu: sayfa sayfa ilerleyen grafik (FLOT gibi)
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
    aileler: dict[str, list[tuple[int, dict]]] = {}
    for t in gruplar:
        m = re.match(r"^(.*?)_(\d+)$", t["kod"])
        if m:
            aileler.setdefault(m.group(1).upper(), []).append((int(m.group(2)), t))
    yuvali = []
    for taban, uyeler in aileler.items():
        if len(uyeler) < 2 or len({(t["sinif"], t["alt"] is None) for _, t in uyeler}) != 1:
            continue
        uyeler.sort(key=lambda x: x[0])
        ana = uyeler[0][1]
        ana["ad"] = taban
        ana["etiket"] = _etiket(taban)
        for _, t in uyeler[1:]:
            t["sinif"] = "yuva"
        yuvali.append(f"{taban} ({', '.join(t['kod'] for _, t in uyeler)})")
    if yuvali:
        sorular.append("Bu sahnede bazı grafikler iki yuvalı kurulmuş: " + "; ".join(yuvali) + ". "
                       "Uygulama yalnızca 1 numaralı yuvayı kullanır. Bir şey yapmanız gerekmez; "
                       "yayında metin değiştirirken 2. yuvaya geçiş istiyorsanız bunu ayrıca belirtin.")

    # ---- bant onerisi ----
    ad = lambda t: t.get("ad", t["kod"])
    turler = [t for t in gruplar if t["sinif"] == "tur"]
    gruplu: dict[str, list[dict]] = {}
    for t in turler:
        gruplu.setdefault(_anahtar(ad(t)), []).append(t)
    bantlar, ozeller, yalniz_ciftli = [], [], []
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
        if normal_yeri is None or t["ust_yol"] == normal_yeri:
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

    return {
        "sahne": model["scene"]["name"],
        "turler": [{"kod": t["kod"], "etiket": t["etiket"], "giris": t["giris"], "cikis": t["cikis"],
                    "ust": t["ust"], "alt": t["alt"]} for t in turler],
        "bantlar": bantlar,
        "kulakciklar": kulakciklar,
        "ozeller": ozeller,
        "ogeler": ogeler,
        "sorular": sorular,
        "_gruplar": gruplar,
    }


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
