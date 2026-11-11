"""
Reji uygulamasi ureticisi (komut satiri).

  Yeni uygulama:
    python vizuret.py --plan C:\\...\\kumanda.json --hedef C:\\Users\\...\\source\\repos\\NTR_Yeni --derle
  Mevcut uygulamayi sahneye gore guncelle (elle duzenlemeler korunur):
    python vizuret.py --plan kumanda.json --hedef . --guncelle [--arayuz] --derle

kumanda.json: vizscan.py --analiz ile cikan <Sahne>.kumanda.taslak.json, rejiyle netlestirilip
'uygulama', 'namespace', 'sahne', 'tarama' alanlari doldurulmus hali.
"""
import argparse
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vizengine.uretec import uret, derle, UretimHatasi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True, help="kumanda.json")
    ap.add_argument("--hedef", required=True, help="cozum klasoru (yeni: bos ya da olmayan klasor)")
    ap.add_argument("--guncelle", action="store_true", help="mevcut uygulamada yalnizca sahneye bagli dosyalari yenile")
    ap.add_argument("--arayuz", action="store_true", help="guncellemede kumanda panelini de yeniden diz")
    ap.add_argument("--derle", action="store_true", help="sonunda dotnet build calistir")
    a = ap.parse_args()
    try:
        for satir in uret(a.plan, os.path.abspath(a.hedef), a.guncelle, a.arayuz):
            print(satir)
    except UretimHatasi as e:
        print("HATA:", e, file=sys.stderr)
        sys.exit(1)
    if a.derle:
        ok, cikti = derle(os.path.abspath(a.hedef))
        print(cikti)
        sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
