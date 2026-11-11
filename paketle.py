"""
Baskasina vermek icin viztools'u zip'ler (Masaustu\\viztools_devir.zip).
Disarida kalanlar: taramalar (scenes), ornek .via arsivleri, son-acilanlar dosyalari, onbellekler.
"""
import os
import zipfile

KOK = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(os.path.expanduser("~"), "Desktop", "viztools_devir.zip")
DISLA_KLASOR = {"scenes", "__pycache__", ".git"}
DISLA_DOSYA = {".viztools_ui.json", ".viztools_web.json", "viztools_devir.zip"}


def main():
    n = 0
    with zipfile.ZipFile(HEDEF, "w", zipfile.ZIP_DEFLATED) as z:
        for kok, klasorler, dosyalar in os.walk(KOK):
            klasorler[:] = [k for k in klasorler if k not in DISLA_KLASOR]
            for f in dosyalar:
                tam = os.path.join(kok, f)
                rel = os.path.relpath(tam, KOK)
                if f in DISLA_DOSYA or f.endswith((".pyc", ".via")):
                    continue
                z.write(tam, os.path.join("viztools", rel))
                n += 1
    print(f"{n} dosya -> {HEDEF}  ({os.path.getsize(HEDEF) / 1048576:.1f} MB)")


if __name__ == "__main__":
    main()
