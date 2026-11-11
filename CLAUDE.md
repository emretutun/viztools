# viztools

Viz Engine KJ sahnesinden C# WinForms reji kumanda uygulamasi ureten arac.
Is akisi, kavramlar ve kurallar: `skill/vizrt-reji/SKILL.md` (kur.bat bunu kullanicinin
Claude klasorune de kurar). Insan icin anlatim: `DEVIR.md`.

Kullanici "X sahnesinin reji uygulamasini yap" ya da "sahne degisti, guncelle" derse
SKILL.md'deki akisi izle. Skill kurulu degilse once `python kur.py` calistirmasini oner.

## Kurallar
- Yalnizca 127.0.0.1. Baska IP'ye baglanma; sahne scriptlerindeki yayin PC IP'lerine bir sey basma.
- Viz sahnelerine ve veritabanlarina (Graphic Hub dahil) yazma; viztools yalnizca GET gonderir, bunu gevsetme.
- Kullanicinin mevcut, canli projelerine dokunma; yalnizca viztools ile uretilmis (kumanda.json olan) uygulamalari guncelle.
- Uretilen uygulamayi kendiliginden calistirma; dogrulama `dotnet build` ile.
- Commit/push yalnizca kullanici isterse.
