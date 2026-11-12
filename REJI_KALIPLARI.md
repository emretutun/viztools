# Reji kaliplari: canli uygulamalardan ogrenilenler

Bu belge, canlida calisan bes uygulamanin (NTR Show, NTR HT, NTR HTSPOR, MCR HTS, TickerControl HTS)
kodu yalnizca okunarak cikarildi. Amac: viztools'un urettigi uygulamanin sahneyi canli uygulamalarla
ayni bicimde surmesi. Uretici ve analiz bu kurallari uygular; burada "neden" yazilidir.
Canli uygulamalara dokunulmaz; bu belge onlarin yerine gecen bilgidir.

## Uretecin uyguladigi kurallar

| Kural | Canlidaki ornek | viztools'ta |
|---|---|---|
| KJ AL tek bir ortak cikis oynatir; yuva cikislari (`KJ_TEK_1_OUT`) kullanilmaz | HTSPOR `KJ_FULL_OUT`, HT `GENEL_KJ_OUT` | Analiz `FULL/GENEL/TUM/ALL ..._OUT` adli director'u ayni yerdeki turlerin `cikis`'i yapar |
| Cikisi ortak olan turler arasi gecis (tekli <-> ciftli) cikis yapmadan dogrudan olur | HTSPOR `KJ_TEK_x` <-> `KJ_CIFT_1` | Sablon: `Cikis` ayniysa dogrudan IN |
| Ayni tur yayindayken yeni yazi: grafik alinmaz, iki yuva arasinda gecilir | HTSPOR `KJ_TEK_1/2`, HT `UST_KJ_DEGIS_1/2` + `UST_KJ_01/02`, Show `TEXT1/TEXT2` | `turler[].yuvalar`; sablon siradaki yuvaya yazar, onun girisini oynatir |
| Farkli bant turu: once OUT, bekleme, sonra IN | Show 1500 ms, HT 800-1000 ms | Sablon 700 ms (`TurGecisBeklemeMs`) |
| Cikis icin `X_OUT` oynatilir; `X_OUT_ANIM` onun ic animasyonudur | HTSPOR `PROGRAM_LOGO_OUT`, `LOKASYON_OUT`, `KJ_ISIM_1_OUT` | Analiz `X_OUT`'u secer |
| Isim, telefon, lokasyon banttan bagimsizdir: KJ ekrandayken verilir, kendi AL'i vardir | Uc KJ uygulamasinin hepsi | `turler[].alan`; ozel butonlar VER + AL |
| Isim ile telefon ayni yeri paylasir: biri girerken digeri cikar (OUT, bekleme, IN) | HT ve HTSPOR 250 ms, Show 400 ms | Analiz ikisine `alan: "isimlik"` verir |
| Yuvali ozel turde AL her yuvanin cikisini oynatir | HTSPOR `KJ_ISIM_1_OUT` + `KJ_ISIM_2_OUT` | `yuvalar[].cikis`; sablon hepsini gonderir |
| Kulakcik degisimi: eski OUT, 400 ms, yeni IN | Show `HandleKoseAnimasyonlari` | Sablon `KulakcikGecisBeklemeMs` |
| Isim / telefon yazisi KJ listesinden degil, ayri ISIMLER listesinden (isim + unvan) gelir | HTSPOR ve HT `dgv_NewsTitrList` | `ozeller[].kaynak: "isim"`; panelde ISIMLER listesi (`isimler.json`) |
| Lokasyon gibi tek satirlik etiket kendi yazi kutusundan verilir | HTSPOR `tbx_Lokasyon` | `ozeller[].kaynak: "kutu"` |
| Isim ve telefon tek AL'i paylasir; F3 isim, F2 telefon, F4 AL | HTSPOR, HT | Ayni `alan` tek AL butonu; `ozeller[].tus`, `al_tus` (buton yazisindaki `(F3)` kisayoldur) |
| Unvan bossa isim ile unvan arasindaki ayirac gizlenir | HTSPOR `ISIM_TITR_TEXT_GROUP_1$ayirac` | `turler[].ayirac`, `yuvalar[].ayirac` (analiz bulur) |
| Ayni yazi yeniden verilirse bir sey gonderilmez | HTSPOR `currentText_*` | Sablon |
| CIFTLI'de alt satir bossa tekli verilir | HTSPOR `gnz_Ikili_Ver` | Sablon |
| Zemin / renk (FON): VER'den once resim klibi ve resim gonderilir | HTSPOR `SetKJBackMY`, `SetCornerBackMY` | `fon` (secenekler + ayarlar); panelde FON kutusu. Dosya yollari sahneden okunamaz, plana elle yazilir |
| Kose logosu yazilidir ve istenirse KJ ile birlikte girer | HTSPOR `logo_text`, "Corner Logo" kutusu | `ogeler[].metin`, `kj_ile` |
| Fotografli telefon: resim secilir, yazidan sonra 250 ms beklenir; dosya adinda bosluk olmaz | HTSPOR `FotoluTel_VER` | `turler[].resim`; panelde GOZAT |
| Urun yerlestirme: once bant alinir, 10 sn sonra kendiliginden cikar | HTSPOR `btn_urunyerlestirme_Ver` | `ogeler[].bandi_al`, `oto_al_sn` |
| Satir bazli bant: ust ve alt satir ayri animasyonla girer; ciftli = ust satir, 1000 ms, alt satir; yazi degisince yalnizca degisen satir kendi yuvalari arasinda doner; ciftliden tekliye: `ALT_KJ_OUT`, 1000 ms, ust satir | HT `TekliKJ_Ver`, `CiftliKJ_Ver`, `CiftliKJ_Degis`, `AltKJ_Al` | `bantlar[].alt_satir`, `alt_cikis`; sablon `SatirliVer`. Analiz ayni yerdeki `UST_x` / `ALT_x` ciftini bant yapar |
| Yuvasi olmayan isim / telefon yayindayken yeni yazi: OUT, bekleme, yazi, IN | HT `gnz_Isim_degis` 600 ms, `gnz_Telefon_Ver` 250 ms | Sablon `OzelDegisBeklemeMs` (600) |
| Isim / telefon yazi alani director'un animasyonunda gecmeyebilir; adindan bulunur | HT `ISIMLIK_KJ` + `TITR_KJ`, `TEL_ISIMLIK_KJ` + `TEL_TITR_KJ` | Analiz `_isim_alanlari` |
| AL butonlari duruma bakmadan gonderir (uygulama yeniden acilinca ekranda kalan grafik alinabilir); TUMUNU AL bandi, isim / telefonu ve logoyu her zaman alir | HT `KJ_AL`, `TumunuAL`; HTSPOR `TumunuAL_force` | Sablon: KJ AL ve ozel AL hep acik; kayitta yoksa secili bandin / alanin cikisini gonderir |
| Sahne her VER'de degil, yuklu degilse yuklenir | Hepsi (`SceneLoadCheck`) | Sablon `SahneyiHazirla` |
| VER'den sonra listede bir alt satira gecilir; F7 KJ AL, F8 TUMUNU AL | Hepsi | Sablonda var |

## Sahneye ozel ogrenilmis ayarlar: `ogrenilen\<sahne adi>.json`

Sahneden okunamayan ama canli uygulamada bulunan ayarlar (FON dosya yollari, logo yazi alani, buton adlari,
hangi grafigin yazisiz verildigi) burada durur. Analiz, taranan sahnenin adiyla ayni adli dosya varsa onu
kendiliginden uygular; boylece sahne yeniden taranip sifirdan uygulama uretildiginde de ayni sonuc cikar.
Su an: `HT_SPOR_KJ_v5.json` (NTR HTSPOR'dan), `2026_HT_KJ_V02.json` (NTR HT'den).
Bicim `vizengine\analiz.py` icinde `ogrenileni_uygula` aciklamasinda. Sahnenin adi degisirse dosya da yeniden adlandirilir.

## Uretecin henuz yapmadigi, canlida olan davranislar

Bunlar sahneye ozeldir; istenirse uretilen uygulamanin `Main.cs` / `Main.Kj.cs` dosyasina elle eklenir.

- **Bant director'u + yazi director'u (NTR Show)**: once bant (`KJ_BANT`), sonra yazi (`TEXT1`) oynatilir.
- **Yazi rengi**: HT ve HTSPOR FON'a gore yazi rengini de gonderir (`*MATERIAL*EMISSION SET`); viztools gondermez.
- **Gorunurluk gruplari**: `...*ACTIVE SET 1|0` ile logo gruplari; MCR'de cikistan sonra 300-500 ms bekleyip gizleme.
  (Ayirac ve oge `gorunur` disinda uretilmez.)
- **Haber akisi**: canli uygulamalar haberleri, KJ ve isimleri haber veritabanindan okur. viztools veritabanina
  dokunmaz; KJ `kj_list.json`, isimler `isimler.json` dosyasindan gelir.
- **Baska sahne / katman kullanan butonlar** (HTSPOR: separator, ozel haber logosu, imaj, tanitim, drift): ayri
  sahneler ve BACK_LAYER; tek sahneden uretilemez.
- **Ortak alan cakismasi**: kose etiketi, sosyal medya, telefon, isimlik birbirini alir; bazilari cikinca
  onceki geri gelir (NTR Show "gizle ve geri getir").
- **Sari bant, son dakika dik, yas modu** (NTR HT): banda ozel klipler, gecisler ve beklemeler. Sari bant ayri bir
  BANT secenegi olarak uretilir (`KJ_SARI_ALL` altindaki satirlar) ama canlidaki klip secimi ve yan bant gonderilmez.
- **Guncellemede plan onarimi**: eski surum plan sahneyle celisiyorsa (satir bazli bandi ayri bantlar sanmis plan gibi) guncelleme plani analizden yeniden kurar (`plani_tazele`).

## Kelebek (bolunmus ekran: 2'li, 3'lu, 4'lu ... pencere)

Uc canli uygulamanin kelebek kodu okunarak cikarildi. Show TV'de ayri bir KELEBEK penceresi, Haberturk ve HT Spor'da
GRAFIK formunun Kelebek sekmesi. Ortak olanlar: ikinci motor (GRAFIK-1), arka katman, pencere basina yalnizca
isim + unvan, KJ motoruna dokunulmaz, kelebek sahneleri KJ sahnesinden ayri sahnelerdir.

| | Show TV (YeniSayfa, GeceHatti) | Show TV Magazin | Haberturk, HT Spor |
|---|---|---|---|
| Yazi alanlari | `ISIM<n>`, `TITLE<n>` | yok | `isim_text_<n>`, `titre_text_<n>` |
| Isim bosken gizlenen | `isimlik_bg_<n>`; unvan bossa `TITLE<n>` | - | `ISIM_TITRE_ALL_0<n>` |
| VER | yazilar + gorunurluk, sonra `RENDERER*BACK_LAYER SET_OBJECT SCENE*<yol>` | katmana koy, `BACK_SCENE*STAGE TO_START`, `STAGE START` | `BASA_CEK`, katmana koy, (`BG$softclip` klibi), `group` gorunur, 300 ms, `IN` |
| AL | `RENDERER*BACK_LAYER SET_OBJECT` (kesme) | `STAGE TO_START`, katmani bosalt | `BASA_CEK` (sahne yuklu kalir, OUT yok) |
| Isimler | VER ile birlikte | - | VER yazi gondermez; `ISIM_IN` / `ISIM_OUT`, `ISIM_TITRI_IN` / `ISIM_TITRI_OUT` (arada 700 ms) |
| Canlida degisiklik | ISIM / TITLE GUNCELLE: yazilar animasyonsuz yeniden | - | Isim/Titr GUNCELLE: ayni |
| Katman | BACK | BACK | HT: BACK; HT Spor: MAIN (`ArkaKatmanAnaKatmanda`) |
| Pencere sayisi | sahne adindan (`2LI`, `3LU`...) | sahne adindan | elle yazilmis yerlesim kodundan |

viztools'ta: `vizengine\kelebek.py` taranmis kelebek sahnesini adlardan tanir (numarali isim / unvan alanlari, `IN`,
`BASA_CEK`, `ISIM_IN`...) ve uc akistan birini secer (`duz`, `stage`, `director`). Plan: `kelebekler[]`, `kelebek_ayar`
(`katman`, `klip`). Sablon: `KelebekForm.cs` (liste, pencere basina isim + unvan, VER / AL / GUNCELLE / ISIM VER /
ISIM + UNVAN VER). Isim listesi KJ panelindeki ISIMLER ile ortaktir (`isimler.json`).
Kelebegin kimligi sahne yoludur: ayni adli sahne (`3LU_SAG_DSF`) her programda ayri sahnedir ve alan adlari farklidir
(Haberturk `isim_text_1`, Show TV `ISIM1`). Arsivden (`.via`) toplu alinan kelebeklere klasor yolu taramayla birlikte
yazilir; boylece baska bir programin klasoruyle eslesemez. Taranmamis kelebek yalnizca Show TV adlandirmasiyla
("Adiyla ekle") kurulabilir; bu bir varsayimdir, sahne farkliysa engine "invalid container name" doner.
Sinama durumu: Haberturk'un 41 kelebegi `ht2026.via`'dan tanindi (38'i yazili, 3'u yazisiz `ANKARA_*`); Show TV ve
HT Spor kelebekleri gercek taramayla sinanmadi.
Uretilmeyenler: kayitli kelebek listeleri (canlida veritabaninda), ekran yerlesimi onizlemesi, fon rengine gore klip
secimi (tek klip `kelebek_ayar.klip`), HT Spor GFX kanali, HT'de ikinci grafik motoru (sag taraf).

## Reji disi (sonra)

- **ROLL / akan yazi**: NTR Show'da anahtar kare (`*ANIMATION*KEY*$ad*XYZ SET`, `*TIME SET`) ve satir sayisina
  gore hesap; Magazin'de sure ayari. Sahneye gore degisen sabitler var.
- **Ticker**: yazi komutuyla degil VizTicker servisiyle beslenir (grup ekleme, `SCROLLER_EMPTY` olayi,
  doldurmadan once `softInit INVOKE`). Ayri bir mekanizmadir.
- **MCR**: tek sahnede ~30 bagimsiz oge; director + gorunurluk, kose cakismalari, sureli otomatik alma.

## Komut bicimleri (hepsinde ortak)

```
SCENE*<yol>*STAGE*DIRECTOR*<dir> START            (ters: START REVERSE)
SCENE*<yol>*TREE*$<container>*GEOM*TEXT SET <yazi>
SCENE*<yol>*TREE*$<container>*ACTIVE SET 1|0
SCENE LOAD <yol>   +   RENDERER SET_OBJECT SCENE*<yol>
```
Komutlar `-1 <komut>\0` olarak, tek engine'e, sirayla gonderilir.
