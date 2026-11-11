---
name: vizrt-reji
description: Viz Engine sahnesinden (KJ / alt bant sahnesi) C# WinForms reji kumanda uygulamasi uretir ya da daha once uretilmis bir uygulamayi sahne degisince gunceller. Kullanici bir Viz sahnesi yolu verip "bunun reji programini yap", "uygulamasini cikar", "sahne degisti guncelle", "NTR ... uygulamasi" dediginde, ya da kumanda.json olan bir klasorde calisildiginda kullanilir.
---

# Vizrt reji uygulamasi: sahneden WinForms'a

Araclar `__VIZTOOLS__` klasorundedir (viztools). Her sey tek komutla yapilir: `vizapp.py`.
Sen sahneyi elle okuyup kod yazmazsin; komutu calistirir, analizin sorularini rejiyle
netlestirir, plani (`kumanda.json`) duzeltir ve yeniden uretirsin.

## Guvenlik kurallari (pazarliksiz)

- Yalnizca `127.0.0.1` ile calis. Baska hicbir IP'ye baglanma, komut gonderme. Sahnelerin
  scriptlerinde yayin PC'lerinin IP'leri olabilir; onlara asla bir sey basma.
- Viz veritabanina (Graphic Hub) ve uygulama veritabanlarina dokunma. Sahneyi degistirme,
  kaydetme, silme. viztools yalnizca GET komutu gonderir; bu kurali asacak kod yazma.
- Canli projeler salt okunurdur: NTR Show, NTR HT, NTR HTSPOR, MCR HTSPOR, TickerControl HTS
  ve kullanicinin mevcut diger projeleri. Onlari ornek olarak okuyabilirsin, degistiremezsin.
  Mevcut bir projede calisma istenirse (viztools ile uretilmemis), once sor.
- Uretilen uygulamayi ya da engine'e komut gonderen bir seyi kendiliginden calistirma.
  Dogrulama `dotnet build` ile yapilir. Kullanici isterse kendisi calistirir.
- Commit, push yapma; kullanici isterse yap.

## Arayuz

Ayni is `__VIZTOOLS__\viztools.bat` arayuzunun **Reji uygulamasi** sekmesinden de yapilir
(sahneyi tara, sekmede sec/duzelt, Uret ve derle; sahne degisince Mevcut uygulamayi guncelle).
Kullanici arayuzu kullaniyorsa ona sekmeyi tarif et; komutlari sen calistiriyorsan asagidaki
akislari kullan. Ikisi ayni plani (`kumanda.json`) ve ayni ureticiyi kullanir.

## Akis 1: yeni uygulama

1. Kullanicidan al: uygulama adi (or. "NTR Bu Sabah"), KJ sahnesinin yolu
   (or. `/SHOW_TV_2025/REJI/BU_SABAH/KJ/KJ_TUM_V13`), varsa kelebek klasoru.
   Hedef varsayilan: `%USERPROFILE%\source\repos\<Ad_alt_cizgili>`. Hedef bos olmali.
2. Kullaniciya hatirlat: sahne Viz Artist'te acik olmali; Stage ve Scene Tree'de tum dallar
   acilip (Expand All) sahne kaydedilmis olmali. Kapali dallar okunamaz.
   Engine yoksa sahnenin `.via` arsivi de olur.
3. Calistir:
   ```
   python "__VIZTOOLS__\vizapp.py" --ad "NTR Yeni Program" --sahne /YOL/KJ_SAHNESI --hedef "%USERPROFILE%\source\repos\NTR_Yeni_Program" [--kelebek /YOL/KELEBEK]
   ```
   Engine yerine: `--via dosya.via [--scene AD]`; onceki tarama: `--model "__VIZTOOLS__\scenes\X\X.json"`.
4. Ciktidaki ozeti (kac bant, kulakcik, ozel tur, oge) ve SORULAR'i kullaniciya Turkce,
   kisa anlat. Analiz raporu: `__VIZTOOLS__\scenes\<Sahne>\<Sahne>.analiz.md`.
5. Rejinin cevaplarina gore `<hedef>\kumanda.json`'u duzelt (asagidaki alanlar), sonra:
   ```
   python "__VIZTOOLS__\vizuret.py" --plan "<hedef>\kumanda.json" --hedef "<hedef>" --guncelle --arayuz --derle
   ```
6. Build basarili olunca bitir: cozum yolunu, paneldeki butonlari ve acik kalan sorulari soyle.

## Akis 2: sahne degisti, mevcut uygulamayi guncelle

Hedefte `kumanda.json` varsa uygulama viztools ile uretilmistir; o klasordeki `CLAUDE.md`'yi oku.
```
python "__VIZTOOLS__\vizapp.py" --sahne /YOL/KJ_SAHNESI --hedef "<uygulama klasoru>" --guncelle
```
- Plan korunur. Sahneye bagli dosyalar (`KjTipleri.Sahne.cs`, `VizScenes\*.cs`) yenilenir, derlenir.
- "SAHNEDE YENI" satirlari: sahnede olup planda olmayan grafikler. Rejiye sor, eklenecekse
  `kumanda.json`'a ekle, `vizuret.py ... --guncelle --arayuz --derle`.
- "SAHNEDEN KALKAN / DEGISEN" ile durursa uygulamaya dokunulmamistir. Ya plandan cikar/duzelt
  ya da sahne cok degistiyse ayni komutu `--yeniden-planla` ile calistir (plan analizden yeniden
  kurulur; ad, namespace, kj listesi ve Designer'da elle eklenen kontroller korunur).
  Yeniden planlamadan once kullaniciya ne kalkip ne eklenecegini soyle.
- Kod degisikligi istenirse: uretilen dosyalara degil, `Main.Kj.cs` / `Main.cs`'e elle yaz.
  `KjTipleri.Sahne.cs` ve `VizScenes\` her guncellemede yeniden yazilir.

## Reji kavramlari (analiz bunlari cikarir; sen dogrularsin)

- **BANT**: KJ'nin govdesi. Ayni anda bir tane secilir (NORMAL, YAS, SON DAKIKA, AZ SONRA, DSF...).
  Her bandin TEKLI ve CIFTLI hali olabilir; panelde iki ana buton vardir: TEKLI KJ VER, CIFTLI KJ VER.
  Yalniz tek bicimi olan bant iki butonda da ayni turu verir. NORMAL bant zorunludur.
- **KULAKCIK**: bandin ustune eklenen kucuk grafik (4.5G, SKYPE, TELEFON, SM...). Metin yazilmaz,
  bant gizli kalir ("gozleri kapali"), yalnizca IN/OUT oynatilir. Secili bant + kulakcik birlikte verilir.
  Sahnede gizli (hidden) bir ust container altinda duran metinli turler genelde kulakciktir.
- **OZEL TUR**: kendi VER butonu olan tek satirli tur (ISIMLIK, LOKASYON). Kulakcik eklenmez.
- **OGE**: metinsiz grafik, ayri VER/AL (program logo, sosyal medya, az sonra kapak, saat).
- KJ AL (F7) KJ'yi, TUMUNU AL (F8) her seyi alir. Tur degisince eski tur OUT, 700 ms, yeni IN.
- ROLL / sayfali akislar (DUA_ROLL gibi) ve kelebek formlari su an ureticide yok; kullanici
  "ayri yapilacak" dedi. Analiz soruyorsa ozel tur ya da oge olarak birak ve kullaniciya not dus.

## kumanda.json alanlari

`uygulama`, `namespace`, `sahne`, `kelebek_klasoru`, `tarama` (tarama JSON yolu) ve:
- `turler`: `{kod, etiket, giris, cikis, ust, alt|null, alan}`; giris/cikis director yolu, ust/alt metin container yolu.
- `bantlar`: `{anahtar ("" = NORMAL), etiket, tek, cift}`; tek/cift = tur kodu.
- `kulakciklar`: `{anahtar, etiket, giris, cikis}`.
- `ozeller`: `{kod, etiket}` (kod turlerde olmali).
- `ogeler`: `{anahtar, etiket, giris, cikis}`.
Etiketler panelde gorunen yazidir; Turkce buyuk harf ve kullanicinin dedigi yazim (or. "YAS", "4.5G").
`vizuret.py` plani sahneye karsi dogrular: olmayan director/container varsa uretmez ve listeler.

## Bilinen tuzaklar

- Engine'den `SCENE LOAD` asenkrondur ve az once yazilan metinleri ezer: uygulama sahneyi Reji
  baglantisinda bir kez yukler (bu sablonda hazir; degistirme).
- Kapali director/container icerigi okunamaz: analiz "KAPALI" diye soruyorsa kullaniciya Artist'te
  acip kaydetmesini, sonra komutu tekrar calistirmasini soyle.
- Isimsiz (noname/group) seviyeler kisa yolda atlanir; ayni kisa yol iki yerde varsa sabit
  "TEKIL DEGIL" yorumuyla gelir, o yolu kullanmadan once rejiye sor.
- MSBuild ciktidaki kj_list.json'u silebilir; sablon `kj_list.ornek.json`'dan ilk calismada kopyalar.
- `dotnet new sln` .slnx uretebilir; uretici ikisini de taniyor.
