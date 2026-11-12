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

1. Kullanicidan al: uygulama adi (or. "NTR Bu Sabah"), varsa kelebek klasoru.
   Sahnenin Graphic Hub yolunu SORMA ve tahmin etme: canli taramada engine'den okunur
   (`MAIN_SCENE*LOCATION_PATH GET`). Yalnizca .via ya da eski tarama kullaniliyorsa `--sahne` ile iste.
   Hedef varsayilan: `%USERPROFILE%\source\repos\<Ad_alt_cizgili>`. Hedef bos olmali.
2. Kullaniciya hatirlat: sahne Viz Artist'te acik olmali; Stage ve Scene Tree'de tum dallar
   acilip (Expand All) sahne kaydedilmis olmali. Kapali dallar okunamaz.
   Engine yoksa sahnenin `.via` arsivi de olur.
3. Calistir:
   ```
   python "__VIZTOOLS__\vizapp.py" --ad "NTR Yeni Program" --hedef "%USERPROFILE%\source\repos\NTR_Yeni_Program" [--kelebek /YOL/KELEBEK]
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
python "__VIZTOOLS__\vizapp.py" --hedef "<uygulama klasoru>" --guncelle
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
- **OZEL TUR**: kendi VER ve AL butonu olan, banttan bagimsiz tur (ISIMLIK, TELEFON, LOKASYON).
  KJ ekrandayken verilir; KJ AL onu almaz, kendi AL'i ya da TUMUNU AL alir. Ayni `alan`i tasiyan ozel turler
  (isim ve telefon: "isimlik") birbirinin yerine girer: eski OUT, bekleme, yeni IN.
  Yazisi nereden gelir (`kaynak`): "isim" = paneldeki ISIMLER listesi (isim + unvan; ISIM, TELEFON),
  "kutu" = butonun ustundeki yazi kutusu (LOKASYON), "liste" = KJ listesi. Ayni alandakiler tek AL kullanir.
- **FON**: zemin / renk secimi. Dosya yollari sahneden okunamaz; kullanici ya da ornek alinan uygulama soyler,
  `kumanda.json`'daki `fon` alanina yazilir.
- **YUVA**: sahnede X_1 / X_2 diye iki kopyasi olan grafik. Ayni tur yayindayken yeni yazi verilince
  grafik alinmaz; siradaki yuvaya yazilip onun girisi oynatilir.
- **ORTAK CIKIS**: KJ_FULL_OUT, GENEL_KJ_OUT gibi. KJ AL bunu oynatir; cikisi ortak olan turler arasinda
  (tekli <-> ciftli) gecis cikis yapmadan olur.
- **OGE**: metinsiz grafik, ayri VER/AL (program logo, sosyal medya, az sonra kapak, saat).
- KJ AL (F7) bandi ve kulakcigi, TUMUNU AL (F8) her seyi alir. Bant turu degisince eski OUT, 700 ms, yeni IN.
- Bu kurallar canli uygulamalarin kodundan cikarildi: `__VIZTOOLS__\REJI_KALIPLARI.md`. Sahneye ozel bir
  davranis sorulursa (zemin rengi, fotograf, satir bazli bant...) once o belgeye bak.
- ROLL / sayfali akislar (DUA_ROLL gibi) su an ureticide yok; kullanici
  "ayri yapilacak" dedi. Analiz soruyorsa ozel tur ya da oge olarak birak ve kullaniciya not dus.

## kumanda.json alanlari

`uygulama`, `namespace`, `sahne`, `kelebek_klasoru`, `tarama` (tarama JSON yolu) ve:
- `turler`: `{kod, etiket, giris, cikis, ust, alt|null, alan?, yuvalar?}`; giris/cikis director yolu, ust/alt metin
  container yolu. `alan`: ozel turun ekran bolgesi (verilmezse kendi kodu; bant turlerinde yok sayilir).
  `yuvalar`: `[{giris, cikis, ust, alt}]` ek yuvalar (2. yuva yanlis calisiyorsa bu alani silmek yeter).
- Istege bagli alanlar (analiz bulabildigini kendisi yazar; gerisini sen ekle):
  `ozeller[]`: `kaynak` "liste"|"isim"|"kutu", `tus` "F3", `al_tus` "F4".
  `turler[]`: `ayirac` (unvan bosken gizlenen container), `resim: {container, varsayilan}` (fotografli grafik, GOZAT).
  `ogeler[]`: `metin: {container, secenekler[]}` (yazili logo), `kj_ile` (KJ ile birlikte ver kutusu),
  `oto_al_sn`, `bandi_al`, `gorunur[]`.
  `fon: {secenekler[], varsayilan, ayarlar[{hedef, tip, yol, degerler}]}`; `hedef` alan ("altbant"), tur kodu ya da
  oge anahtari; `tip` "imageclip" | "image" | "director" (deger START / REVERSE; "*" = diger secenekler).
- Kullanici "su uygulamaya benzesin" derse o uygulamanin kodunu YALNIZCA oku; FON tablosu, logo yazisi, kisayollar,
  sureli alma gibi sahneden okunamayan ayarlari oradan cikarip `kumanda.json`'a yaz, sonra `vizuret.py --guncelle --arayuz --derle`.
- KELEBEK (bolunmus ekran) ayri sahnelerdir ve ikinci motorda (GRAFIK-1) oynar. viztools Graphic Hub klasorunu okuyamaz;
  kelebek sahneleri once tanitilir:
  - topluca: kullanici kelebek klasorunu `.via` olarak disa aktarir ->
    `vizapp.py ... --kelebek /YOL/KELEBEK --kelebek-via dosya.via --kelebekler hepsi` (klasor zorunlu: yol taramaya yazilir);
  - tek tek: sahne Artist'te acikken `python "__VIZTOOLS__\vizscan.py" --details`, sonra `--kelebekler AD1 AD2`.
  Plan: `kelebekler[]` (`vizengine\kelebek.py` taramadan cikarir; alan adlarini tahminle yazma), `kelebek_klasoru`,
  `kelebek_ayar: {katman "BACK"|"MAIN", klip}`.
  Ayni adli sahne (3LU_SAG_DSF) her programda ayri sahnedir ve alan adlari farklidir (Haberturk `isim_text_1`, Show TV
  `ISIM1`): bir programin taramasini baska programin klasoruyle eslestirme. Tarama yoksa kullaniciya soyle; yalnizca
  kullanici Show TV adlandirmasini (`ISIM1` / `TITLE1` / `isimlik_bg_1`) dogrularsa arayuzdeki "Adiyla ekle" kullanilir.
- `surum`: plan surumu. Eski plan guncellenirken cikis/yuva/alan bir kez analizden tazelenir.
- `bantlar`: `{anahtar ("" = NORMAL), etiket, tek, cift}`; tek/cift = tur kodu.
- `kulakciklar`: `{anahtar, etiket, giris, cikis}`.
- `ozeller`: `{kod, etiket}` (kod turlerde olmali).
- `ogeler`: `{anahtar, etiket, giris, cikis}`.
Etiketler panelde gorunen yazidir; Turkce buyuk harf ve kullanicinin dedigi yazim (or. "YAS", "4.5G").
`vizuret.py` plani sahneye karsi dogrular: olmayan director/container varsa uretmez ve listeler.

## Bilinen tuzaklar

- Uygulama "invalid sublocation" / "invalid location SCENE" aliyorsa sahne yolu yanlistir (klasor yazilmis
  ya da arada olmayan bir klasor var). Sahne Artist'te acikken `vizapp.py --hedef <uygulama> --guncelle`
  calistir: yol engine'den okunur, `ShowData/scenes.txt` de duzeltilir.
- Ayni adli kardes container'lar (iki tane `TEXT` gibi): tarama her container'i numarasiyla (#id) okur,
  bu yuzden metin alanlari kaybolmaz. Ama uygulama yazarken adla yazar; metin alaninin ADI sahnede
  tekil olmali (analiz "birden fazla yerde geciyor" diye uyarir).
- Engine bos director icin -1, kapali dal icin 0 dondurur; yalnizca 0 "okunamadi" demektir.
- Cift yuvali sahneler (X_1 / X_2): uygulama yazi degisiminde yuvalar arasinda gecer. Canli HTSPOR uygulamasi
  ciftli KJ'de yalnizca 1. yuvayi kullaniyor; ciftlide 2. yuva sorun cikarirsa o turun `yuvalar`ini sil.
- Eski sablonla uretilmis uygulama guncellenince `Main.Kj.cs` ve `KjTipleri.cs` yenilenir, eskileri `.yedek`
  olarak kalir, panel yeniden dizilir. Kullanici bu dosyalara elle kod eklediyse yedekten tasimasi gerekir; soyle.
- Satir bazli bant (NTR HT sahnesi: UST_KJ_DEGIS / ALT_KJ_DEGIS): analiz ayni yerdeki UST_x / ALT_x ciftini tek bant
  yapar (`bantlar[].alt_satir`, `alt_cikis`). TEKLI ust satiri, CIFTLI ust + alt satiri verir.
- `__VIZTOOLS__\ogrenilen\<sahne adi>.json` varsa analiz onu kendiliginden uygular (FON, logo yazisi, buton adlari).
  Kullanici yeni bir sahne icin "su uygulamaya benzesin" derse ogrendiklerini `kumanda.json`'a yazmakla yetinme;
  ayni sahne yeniden taraninca da gelsin diye bu klasore de bir dosya ekle (ornek: mevcut dosyalar).
- Arac kodu degistikten sonra acik viztools penceresi eski kodla calisir; kapatip viztools.bat'i yeniden ac.

- Engine'den `SCENE LOAD` asenkrondur ve az once yazilan metinleri ezer: uygulama sahneyi Reji
  baglantisinda bir kez yukler (bu sablonda hazir; degistirme).
- Kapali director/container icerigi okunamaz: analiz "KAPALI" diye soruyorsa kullaniciya Artist'te
  acip kaydetmesini, sonra komutu tekrar calistirmasini soyle.
- Isimsiz (noname/group) seviyeler kisa yolda atlanir; ayni kisa yol iki yerde varsa sabit
  "TEKIL DEGIL" yorumuyla gelir, o yolu kullanmadan once rejiye sor.
- MSBuild ciktidaki kj_list.json'u silebilir; sablon `kj_list.ornek.json`'dan ilk calismada kopyalar.
- `dotnet new sln` .slnx uretebilir; uretici ikisini de taniyor.
