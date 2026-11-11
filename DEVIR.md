# Devir: sahneden reji uygulamasi

Bu belge viztools'u ilk kez alan kisi icindir. Bu sohbet ya da ilk kuran kisi olmasa da
her sey bu klasorle calisir. Claude'un bilmesi gerekenler `skill\vizrt-reji\SKILL.md`'dedir.

## Ne yapar

Viz Artist'te acik bir KJ sahnesine (yalnizca okuyarak) bakar, icindeki director ve
container'lardan reji kumandasini cikarir ve C# WinForms (.NET 8) cozumunu yazip derler.
Sahne degisince ayni uygulamayi gunceller; rejinin kararlari ve elle yapilan eklemeler korunur.

## Kurulum (bir kez)

1. Gerekenler: Python 3.10+, .NET 8 SDK, git, Claude Code (kendi aboneliginiz).
2. viztools klasorunu bilgisayara kopyalayin (orn. Masaustu).
3. `kur.bat`'a cift tiklayin. Skill kullanicinin Claude klasorune kurulur.
   Claude'un engine'i dogrudan sorgulamasi da istenirse: `kur.bat --mcp`.

## Kullanim (uygulama ile, en kolayi)

1. Viz Artist'te sahneyi acin. Stage ve Scene Tree'de tum dallari acin (Expand All), kaydedin.
2. `viztools.bat`'a cift tiklayin. Tarayicida viztools acilir.
3. Soldan **Sahneyi tara** (engine acikken), ya da `.via` dosyasi / onceki tarama secin.
4. **Reji uygulamasi** sekmesine gecin.
   - Yeni: uygulama adini ve KJ sahnesinin Graphic Hub yolunu yazin.
   - Sagdaki listede panelde ne cikacagini secin: bantlar, kulakciklar, ozel butonlar, ogeler.
     Etiketi duzeltebilir, bir kalemi kulakcik / oge (ya da bant / ozel buton) olarak degistirebilirsiniz.
   - **Uygulamayi uret ve derle**. Bitince "Visual Studio'da ac".
5. Sahne degisince: sahneyi yeniden tarayin, **Mevcut uygulamayi guncelle**'yi secin.
   Planin mevcut kalemleri secili gelir; sahnede yeni cikanlar "sahnede yeni", kalkanlar "sahnede yok"
   diye isaretlenir. Istediklerinizi secip **Guncelle ve derle**. Elle eklenen kod ve butonlar korunur.

## Kullanim (Claude ile)

1. Viz Artist'te sahneyi acin. Stage ve Scene Tree'de tum dallari acin (Expand All), kaydedin.
2. Claude Code'a yazin, ornek:
   > /SHOW_TV_2025/REJI/YENI/KJ/KJ_TUM_V1 sahnesinin reji uygulamasini yap, adi NTR Yeni Program olsun
3. Claude sahneyi tarar, uygulamayi `source\repos\NTR_Yeni_Program`'a uretir ve derler.
   Analizin emin olamadigi noktalari (hangisi kulakcik, hangisi ayri buton...) size sorar.
4. Sahne degisince:
   > NTR Yeni Program'in sahnesi degisti, guncelle

## Kullanim (Claude olmadan)

```
python vizapp.py --ad "NTR Yeni Program" --sahne /YOL/KJ_SAHNESI --hedef C:\Users\<kullanici>\source\repos\NTR_Yeni_Program
python vizapp.py --sahne /YOL/KJ_SAHNESI --hedef <uygulama klasoru> --guncelle
```
Kararlar `<uygulama>\kumanda.json`'dadir. Elle duzeltip:
```
python vizuret.py --plan <uygulama>\kumanda.json --hedef <uygulama> --guncelle --arayuz --derle
```

## Kurallar

- Yalnizca 127.0.0.1. viztools sahneye, engine'e ve veritabanina yazmaz; yalnizca GET gonderir.
- Uretilen uygulama da gelistirmede yalnizca 127.0.0.1'e baglanir (`ShowData\IpList.txt`).
  Yayin bilgisayarlarinin IP'lerini ekleme karari rejinindir.
- Canli projelere (NTR Show, NTR HT, NTR HTSPOR, MCR HTSPOR, TickerControl HTS) dokunulmaz.

## Klasorler

| Yol | Ne |
|---|---|
| `viztools.bat` / `vizscan_web.py` | Arayuz: tarama + Reji uygulamasi sekmesi (uret / guncelle) |
| `vizapp.py` | Ayni isin tek komutlu hali |
| `vizuret.py` | Plandan (kumanda.json) uretim / guncelleme |
| `vizscan.py` | Sahne tarama (komut satiri) |
| `vizengine\uygulama.py` | Arayuz ve vizapp'in ortak uretim akisi |
| `vizengine\analiz.py` | Sahneden bant, kulakcik, ozel tur, oge cikarimi |
| `vizengine\uretec.py` | C# uretici |
| `sablon\winforms\` | Uygulama sablonu (sahneden bagimsiz kod) |
| `skill\vizrt-reji\` | Claude'un is akisi ve kurallari |
| `scenes\` | Taramalar ve analiz raporlari (makineye ozel) |

## Henuz yok

ROLL / sayfali akislar ve kelebek formlari ureticide yok; bu uygulamalara elle eklenir.
