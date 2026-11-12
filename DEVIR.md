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
   - Yeni: uygulama adini yazin. Sahnenin Graphic Hub yolu engine'den kendiliginden okunur
     (yalnizca .via dosyasiyla calisirken elle yazilir).
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
| `vizengine\kelebek.py` | Kelebek sahnesi tanima, arsivden toplu ice alma |
| `REJI_KALIPLARI.md` | Canli uygulamalardan ogrenilen reji ve kelebek kurallari |
| `vizengine\uretec.py` | C# uretici |
| `sablon\winforms\` | Uygulama sablonu (sahneden bagimsiz kod) |
| `skill\vizrt-reji\` | Claude'un is akisi ve kurallari |
| `ogrenilen\` | Sahneye ozel, canli uygulamalardan ogrenilmis ayarlar (FON, logo yazisi); analiz kendiliginden uygular |
| `scenes\` | Taramalar ve analiz raporlari (makineye ozel) |

## Kelebek eklemek

Kelebekler KJ sahnesinden ayri sahnelerdir ve uygulamada KELEBEK penceresinden, ikinci motorla (GRAFIK-1) verilir.
viztools Graphic Hub klasorunun icini okuyamaz ("Kelebek klasoru" kutusu yalnizca sahne yolunu kurar); kelebekler
**Reji uygulamasi** sekmesinde, o kutunun altindan uc yoldan biriyle tanitilir:

1. **Arsivden topluca (10+ sahne icin):** Artist'te kelebek klasorunu tek bir `.via` olarak disa aktarin; Masaustu'ne,
   Indirilenler'e ya da `samples` klasorune koyun. Klasorun Graphic Hub yolunu kutuya yazin, arsivi secip
   **Arsivdeki kelebekleri topluca al** deyin. Yol taramayla birlikte kaydedilir.
2. **Tek tek:** kelebek sahnesini Artist'te acip **Sahneyi tara** deyin (yol engine'den okunur).
3. **Adiyla:** yalnizca Show TV adlandirmasini kullanan kelebekler icin (`ISIM1`, `TITLE1`, `isimlik_bg_1`; pencere sayisi
   addaki `2LI` / `3LU`'dan). Adlari yazip **Adiyla ekle** deyin. Sahne taranmaz; adlar farkliysa uygulama yanlis alana
   yazar ve engine "invalid container name" der. Emin degilseniz 1 ya da 2.

Sonra KJ sahnesi yukluyken listeden eklenecekleri isaretleyip uretin ya da guncelleyin.
- Ayni adli sahne (`3LU_SAG_DSF`) her programda ayri bir sahnedir. Listede her kelebegin tam yolu ve kaynagi yazar;
  kaynak suzgeciyle yalnizca o programin kelebeklerini gosterin.
- Bir kelebek sahnesi degisirse yeniden tarayin (ya da arsivi yeniden alin) ve uygulamayi guncelleyin.
- Komut satirinda: `python vizapp.py ... --kelebek /YOL/KELEBEK --kelebek-via dosya.via --kelebekler hepsi`.

## Guncellemede plan onarimi

Eski surumle uretilmis bir uygulama guncellenirken plan yeni kurallara tasinir: cikislar, yuvalar, isim listesi,
kisayollar analizden tamamlanir. Plan sahneyle celisiyorsa (satir bazli bandi iki ayri bant sanmis eski plan gibi)
kalemler analizden yeniden kurulur ve bu raporda yazar. Kumanda mantigi dosyalari (`Main.Kj.cs`, `KjTipleri.cs`,
`VizrtExt.cs`, `KelebekForm.cs`, `KelebekTipleri.cs`) sablon surumu degisince yenilenir; eskileri `.yedek` olarak kalir.

## Uygulama sahneyi nasil surer

Kurallar canli uygulamalarin (NTR Show, NTR HT, NTR HTSPOR, MCR HTS, TickerControl HTS) kodu okunarak
cikarildi: `REJI_KALIPLARI.md`. Ozet: KJ AL ortak cikisi oynatir, yazi degisince yuvalar arasinda gecilir,
isim/telefon/lokasyon banttan bagimsizdir ve kendi AL butonlari vardir. Isim ve telefon yazisi paneldeki
ISIMLER listesinden, lokasyon kendi kutusundan verilir. Zemin rengi (FON), yazili logo, fotografli telefon
ve kisayol tuslari `kumanda.json`'dan ayarlanir.

## Henuz yok

- ROLL / sayfali akislar.
- Kelebekte kayitli listeler ve ekran yerlesimi onizlemesi.
- Sari bant, yas modu gibi banda ozel klip secimleri.
- Yazi rengi ve gorunurluk gruplari; baska sahne ya da katman kullanan butonlar (separator, imaj, tanitim).
- Haber akisi (veritabani). KJ ve isim listeleri dosyadan gelir.
Bunlar uygulamaya elle eklenir; ayrintisi `REJI_KALIPLARI.md`'de.
