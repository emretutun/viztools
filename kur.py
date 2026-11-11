"""
viztools kurulumu (her bilgisayarda bir kez):
  python kur.py            -> denetim + vizrt-reji skill'ini kullanicinin Claude klasorune kurar
  python kur.py --mcp      -> ek olarak Viz Engine MCP sunucusunu Claude Code'a ekler (claude CLI gerekir)

viztools klasoru tasinirsa kur.py'yi yeniden calistirin (skill bu klasorun yolunu tasir).
Hicbir Viz sahnesine, engine'e ya da veritabanina dokunmaz.
"""
import argparse
import os
import shutil
import subprocess
import sys

KOK = os.path.dirname(os.path.abspath(__file__))
SKILL_KAYNAK = os.path.join(KOK, "skill", "vizrt-reji", "SKILL.md")
SKILL_HEDEF = os.path.join(os.path.expanduser("~"), ".claude", "skills", "vizrt-reji")


def denetle(ad, komut):
    yol = shutil.which(komut)
    print(f"  {'tamam' if yol else 'YOK  '}  {ad}" + (f"  ({yol})" if yol else ""))
    return bool(yol)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mcp", action="store_true", help="vizengine MCP sunucusunu Claude Code'a kullanici duzeyinde ekle")
    a = ap.parse_args()

    print("Gereksinimler:")
    print(f"  tamam  Python {sys.version.split()[0]}")
    dotnet = denetle(".NET SDK (dotnet) - uretilen uygulamayi derlemek icin", "dotnet")
    denetle("git", "git")
    claude = denetle("Claude Code (claude)", "claude")
    if not dotnet:
        print("  -> .NET 8 SDK kurun: https://dotnet.microsoft.com/download/dotnet/8.0")

    # skill
    os.makedirs(SKILL_HEDEF, exist_ok=True)
    with open(SKILL_KAYNAK, encoding="utf-8") as f:
        metin = f.read().replace("__VIZTOOLS__", KOK)
    with open(os.path.join(SKILL_HEDEF, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(metin)
    print(f"\nSkill kuruldu: {SKILL_HEDEF}\\SKILL.md  (viztools: {KOK})")

    if a.mcp:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", os.path.join(KOK, "requirements.txt")])
        if claude:
            r = subprocess.run(["claude", "mcp", "add", "--scope", "user", "vizengine", "--",
                                sys.executable, os.path.join(KOK, "viz_mcp_server.py")], capture_output=True, text=True)
            print((r.stdout + r.stderr).strip() or "MCP sunucusu eklendi: vizengine")
        else:
            print("claude CLI bulunamadi; MCP icin mcp.example.json'u kullanin.")
    print("\nHazir. Claude Code'u acip ornegin sunu yazin:\n"
          '  "/SHOW_TV_2025/REJI/X/KJ/KJ_TUM_V1 sahnesinin reji uygulamasini yap, adi NTR X olsun"')


if __name__ == "__main__":
    main()
