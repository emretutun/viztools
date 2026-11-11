"""
TEK KOMUT: sahneden reji uygulamasina.

Artist'te sahneyi acin, Stage ve Scene Tree dallarini acip kaydedin, sonra:

  python vizapp.py --ad "NTR Yeni Program" --sahne /SHOW_TV_2025/REJI/YENI/KJ/KJ_TUM_V1 ^
                   --hedef C:\\Users\\<kullanici>\\source\\repos\\NTR_Yeni_Program

Yapilanlar:
  1. Sahne okunur (yalnizca 127.0.0.1, yalnizca GET komutlari; sahneye hicbir sey yazilmaz)
     - ya da engine kapaliysa: --via sahne.via [--scene AD]   /   onceki tarama: --model scenes\\X\\X.json
  2. Analiz: metinli turler, BANT (tekli/ciftli), KULAKCIK, ozel turler, metinsiz ogeler cikarilir
  3. <hedef>\\kumanda.json yazilir (plan), C# WinForms cozumu uretilir ve derlenir
  4. Analizin emin olamadigi noktalar 'SORULAR' olarak listelenir: rejiyle netlestirip kumanda.json'u
     duzeltin, sonra:  python vizuret.py --plan <hedef>\\kumanda.json --hedef <hedef> --guncelle --arayuz --derle

Sahne degisince (mevcut uygulama):
  python vizapp.py --sahne <ayni yol> --hedef <uygulama klasoru> --guncelle
  -> plan korunur (reji kararlari kaybolmaz); sahnede yeni cikan / kalkan grafikler raporlanir,
     sahneye bagli dosyalar yenilenir, derlenir. Plan sahneyle uyusmazsa uygulamaya dokunulmaz.
  Sahne cok degistiyse: ayni komut + --yeniden-planla  (plan yeni analizden kurulur, panel yeniden
     dizilir; uygulama adi, namespace, kj listesi ve elle eklenen kontroller korunur)
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
from vizengine import VizClient, VizCommandBlocked, VizError
from vizengine.template import build_scene_model, write_outputs
from vizengine.analiz import analiz_et, rapor
from vizengine.uygulama import (UretimHatasi, taslak_plan, plan_oku, karsilastir, uygula)


def sahneyi_oku(a) -> dict:
    if a.model:
        with open(a.model, encoding="utf-8") as f:
            return json.load(f)
    if a.via:
        from vizengine.via import read_via, list_scenes
        sahneler = list_scenes(a.via)
        if len(sahneler) > 1 and not a.scene:
            raise UretimHatasi(f"{a.via} icinde {len(sahneler)} sahne var; --scene ile birini secin: " + ", ".join(sahneler))
        return read_via(a.via, a.scene)
    with VizClient("127.0.0.1", 6100) as cli:
        return build_scene_model(cli, "MAIN_SCENE", details=True)


def main():
    ap = argparse.ArgumentParser(description="Sahneden Viz reji WinForms uygulamasi")
    ap.add_argument("--ad", help="uygulama adi (yeni uygulamada zorunlu), orn. \"NTR Bu Sabah\"")
    ap.add_argument("--sahne", required=True, help="KJ sahnesinin Graphic Hub yolu, orn. /SHOW_TV_2025/REJI/X/KJ/KJ_TUM_V1")
    ap.add_argument("--hedef", required=True, help="cozum klasoru (yeni: bos ya da olmayan)")
    ap.add_argument("--kelebek", help="kelebek sahnelerinin klasoru (ops.)")
    ap.add_argument("--namespace", help="C# namespace (verilmezse addan)")
    ap.add_argument("--via", help="engine yerine .via arsivinden oku")
    ap.add_argument("--scene", help=".via icindeki sahne adi")
    ap.add_argument("--model", help="daha once yazilmis tarama JSON'u")
    ap.add_argument("--guncelle", action="store_true", help="mevcut uygulamayi sahneye gore guncelle (plan korunur)")
    ap.add_argument("--yeniden-planla", action="store_true",
                    help="guncellemede plani yeni analizden kur (ad/namespace/kelebek korunur, panel yeniden dizilir, elle eklenen kontroller kalir)")
    ap.add_argument("--derleme", action="store_true", help="derlemeyi atla")
    a = ap.parse_args()
    hedef = os.path.abspath(a.hedef)
    plan_yolu = os.path.join(hedef, "kumanda.json")

    try:
        # 1) sahne
        model = sahneyi_oku(a)
        jp, mp = write_outputs(model, os.path.join(KOK, "scenes"))
        s = model["scene"]
        print(f"Sahne: {s['name']}  ({s['container_count']} container, {s['director_count']} director)")
        print("Tarama:", jp)

        # 2) analiz
        an = analiz_et(model)
        rapor_yolu = os.path.join(os.path.dirname(jp), f"{os.path.splitext(os.path.basename(jp))[0]}.analiz.md")
        with open(rapor_yolu, "w", encoding="utf-8") as f:
            f.write(rapor(an))
        print(f"Analiz: {len(an['bantlar'])} bant, {len(an['kulakciklar'])} kulakcik, {len(an['ozeller'])} ozel tur, "
              f"{len(an['ogeler'])} metinsiz oge  ->  {rapor_yolu}")

        # 3) plan
        if a.guncelle:
            eski = plan_oku(hedef)
            if not eski:
                raise UretimHatasi(f"{plan_yolu} yok: bu klasor viztools ile uretilmis bir uygulama degil")
            if a.yeniden_planla:
                plan = taslak_plan(model, an, eski["uygulama"], a.sahne, a.kelebek or eski.get("kelebek_klasoru", ""),
                                   eski["namespace"], jp)
            else:
                plan = dict(eski, sahne=a.sahne, tarama=jp)
            fark = karsilastir(plan, an, model)
            if fark["yeni"]:
                print("SAHNEDE YENI (plana eklenmedi, karar rejinin):", ", ".join(fark["yeni"]))
            if fark["hatalar"]:
                print("SAHNEDEN KALKAN / DEGISEN (plandan cikarilmasi ya da duzeltilmesi gerekir):")
                for h in fark["hatalar"]:
                    print("  -", h)
                raise UretimHatasi("Plan sahneyle uyusmuyor. Uygulamaya dokunulmadi. Ya kumanda.json'u duzeltip "
                                   "vizuret.py --guncelle calistirin, ya da bu komutu --yeniden-planla ile tekrarlayin.")
        else:
            if not a.ad:
                raise UretimHatasi("--ad zorunlu (yeni uygulama)")
            plan = taslak_plan(model, an, a.ad, a.sahne, a.kelebek or "", a.namespace or "", jp)

        # 4) uret (+ derle)
        ok, satirlar = uygula(plan, hedef, jp, guncelle=a.guncelle, arayuz=a.yeniden_planla, derle_=not a.derleme)
        for satir in satirlar:
            print(satir)
        print("Plan:", plan_yolu)
        if not ok:
            sys.exit(2)

        if an["sorular"] and (not a.guncelle or a.yeniden_planla):
            print("\nSORULAR (rejiyle netlestirin, kumanda.json'u duzeltin, sonra vizuret.py --guncelle --arayuz):")
            for i, q in enumerate(an["sorular"], 1):
                print(f"  {i}. {q}")
    except (UretimHatasi, VizCommandBlocked, VizError, OSError) as e:
        print("HATA:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
