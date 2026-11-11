"""
Komut satirindan sahne tarama (Claude olmadan da calisir).

  python vizscan.py                    -> MAIN_SCENE'i tarar, scenes/ altina .md + .json yazar
  python vizscan.py --details          -> her container'in GEOM*TEXT degerini de okur
  python vizscan.py --layer FRONT_SCENE
  python vizscan.py --send "MAIN_SCENE*STAGE*DIRECTOR GET"   -> tek komut (yalnizca GET)
  python vizscan.py --details --csharp --analiz              -> tara + C# sabitleri + reji uygulamasi taslak plani
  python vizscan.py --model scenes/X/X.json --analiz         -> engine'siz, kayitli taramadan analiz
"""
import argparse
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vizengine import VizClient, VizCommandBlocked, VizError
from vizengine.template import build_scene_model, write_outputs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=6100)
    ap.add_argument("--layer", default="MAIN_SCENE")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "scenes"))
    ap.add_argument("--details", action="store_true", help="container GEOM*TEXT degerlerini de oku")
    ap.add_argument("--send", help="tek bir salt-okunur komut gonder ve cik")
    ap.add_argument("--via", help="engine yerine bir .via arsiv dosyasindan oku")
    ap.add_argument("--scene", help=".via icindeki sahne adi (verilmezse sahneler listelenir)")
    ap.add_argument("--csharp", action="store_true", help="scenes/<Sahne>.cs C# sabit sinifini da uret")
    ap.add_argument("--namespace", default="VizScenes", help="C# namespace (varsayilan VizScenes)")
    ap.add_argument("--analiz", action="store_true",
                    help="reji uygulamasi icin taslak plan cikar: <Sahne>.analiz.md + <Sahne>.kumanda.taslak.json")
    ap.add_argument("--model", help="engine'e baglanmadan, daha once yazilmis tarama JSON'unu kullan (--analiz / --csharp icin)")
    a = ap.parse_args()

    def after_write(model):
        if a.csharp:
            from vizengine.gen_csharp import write_csharp
            print("Yazildi:", write_csharp(model, a.out, a.namespace))
        if a.analiz:
            import json
            from vizengine.analiz import analiz_et, rapor
            from vizengine.template import scene_dir, scene_base
            an = analiz_et(model)
            d, base = scene_dir(model, a.out), scene_base(model)
            with open(os.path.join(d, f"{base}.analiz.md"), "w", encoding="utf-8") as f:
                f.write(rapor(an))
            taslak = {k: v for k, v in an.items() if not k.startswith("_")}
            with open(os.path.join(d, f"{base}.kumanda.taslak.json"), "w", encoding="utf-8") as f:
                json.dump(taslak, f, ensure_ascii=False, indent=2)
            print(f"Analiz: {len(an['bantlar'])} bant, {len(an['kulakciklar'])} kulakcik, {len(an['ozeller'])} ozel, "
                  f"{len(an['ogeler'])} oge, {len(an['sorular'])} soru")
            print("Yazildi:", os.path.join(d, f"{base}.analiz.md"))
            print("Yazildi:", os.path.join(d, f"{base}.kumanda.taslak.json"))

    if a.model:
        import json
        with open(a.model, encoding="utf-8") as f:
            model = json.load(f)
        after_write(model)
        return
    if a.via:
        from vizengine.via import read_via, list_scenes, ViaError
        try:
            scenes = list_scenes(a.via)
            if len(scenes) > 1 and not a.scene:
                print(f"{a.via} icinde {len(scenes)} sahne var; --scene ile birini secin:")
                for s in scenes:
                    print("  ", s)
                return
            model = read_via(a.via, a.scene)
        except (ViaError, OSError) as e:
            print("HATA:", e, file=sys.stderr)
            sys.exit(1)
        jp, mp = write_outputs(model, a.out)
        s = model["scene"]
        print(f"Sahne: {s['name']}  ({s['container_count']} container, {s['director_count']} director)  [{s['source']}]")
        for w in model["warnings"]:
            print("NOT:", w)
        print("Yazildi:", mp)
        print("Yazildi:", jp)
        after_write(model)
        return
    try:
        with VizClient("127.0.0.1", a.port) as cli:
            if a.send:
                print(cli.send(a.send))
                return
            model = build_scene_model(cli, a.layer, a.details)
            jp, mp = write_outputs(model, a.out)
            s = model["scene"]
            print(f"Sahne: {s['name']}  ({s['container_count']} container, {s['director_count']} director)")
            for w in model["warnings"]:
                print("UYARI:", w)
            print("Yazildi:", mp)
            print("Yazildi:", jp)
            after_write(model)
    except (VizCommandBlocked, VizError, OSError) as e:
        print("HATA:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
