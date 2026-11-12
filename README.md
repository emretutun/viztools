# viztools

Viz Engine sahnesinden **C# WinForms reji kumanda uygulaması** üreten araç.

Viz Artist'te açık bir KJ sahnesine bakar, içindeki grafiklerden (bantlar, kulakçıklar,
isimlik, logo vb.) reji panelini çıkarır ve çalışır bir Visual Studio çözümü yazıp derler.
Sahne değişince aynı uygulamayı günceller; elle eklenen kod ve butonlar korunur.
Kelebek (bölünmüş ekran) sahneleri de taranıp uygulamaya KELEBEK penceresi olarak eklenir.

Uygulamanın sahneyi nasıl sürdüğü (hangi animasyon ne zaman oynar, AL ne gönderir, isim ve
telefon nasıl değişir) canlıda çalışan reji uygulamalarının kodu okunarak çıkarıldı:
[REJI_KALIPLARI.md](REJI_KALIPLARI.md).

Sahneye, engine'e ve veritabanına **hiçbir şey yazmaz**; yalnızca okur ve yalnızca
bu bilgisayardaki engine'e (127.0.0.1) bağlanır.

## Kurulum

Gerekenler:

- Windows 10 / 11
- [Python 3.10+](https://www.python.org/downloads/) (kurulumda "Add python.exe to PATH" işaretli olsun)
- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)
- Viz Artist / Viz Engine (sahneyi taramak için; yalnızca `.via` dosyasıyla çalışacaksanız gerekmez)
- İsteğe bağlı: [Claude Code](https://claude.com/claude-code) (uygulamayı Claude'a yazarak ürettirmek için)

Adımlar:

1. Bu depoyu indirin: **Code > Download ZIP** ile indirip açın, ya da:
   ```
   git clone <depo adresi>
   ```
2. Klasördeki **`kur.bat`** dosyasına çift tıklayın. Gereksinimleri denetler ve Claude için
   iş akışını (skill) kullanıcı klasörünüze kurar. Bir kez yapılır; klasörü taşırsanız yeniden çalıştırın.

Ek paket kurmak gerekmez.

## Kullanım

1. Viz Artist'te sahneyi açın. Stage ve Scene Tree'de **tüm dalları açın** (Expand All) ve
   sahneyi **kaydedin**. Kapalı dallar okunamaz.
2. **`viztools.bat`** dosyasına çift tıklayın. Tarayıcıda viztools açılır.
3. Soldan **Sahneyi tara** düğmesine basın. (Engine kapalıysa bir `.via` dosyası da açılabilir.)
4. **Reji uygulaması** sekmesine geçin:
   - Uygulama adını yazın. Sahnenin Graphic Hub yolu engine'den kendiliğinden okunur
     (yalnızca `.via` dosyasıyla çalışırken elle yazılır).
   - Sağdaki listeden panelde çıkacakları seçin, etiketleri düzeltin.
   - **Uygulamayı üret ve derle** düğmesine basın.
5. Bitince **Visual Studio'da aç**. Uygulama `C:\Users\<kullanıcı>\source\repos\` altındadır.

### Sahne değişince

Sahneyi yeniden tarayın, **Reji uygulaması** sekmesinde **Mevcut uygulamayı güncelle**'yi seçin.
Sahnede yeni çıkanlar "sahnede yeni", kalkanlar "sahnede yok" diye işaretlenir.
İstediklerinizi seçip **Güncelle ve derle** düğmesine basın.

### Kelebek eklemek

Kelebekler KJ sahnesinden ayrı sahnelerdir; uygulamada **KELEBEK** penceresinden, ikinci motorla
(GRAFİK-1) verilir. viztools Graphic Hub klasörünün içini okuyamaz; kelebekler şu üç yoldan
biriyle tanıtılır (**Reji uygulaması** sekmesi, "Kelebek klasörü" kutusunun altı):

1. **Arşivden topluca:** Artist'te kelebek klasörünü tek bir `.via` olarak dışa aktarın
   (Masaüstü, İndirilenler ya da `samples` klasörüne koyun). Klasörün Graphic Hub yolunu
   kutuya yazın, arşivi seçip **Arşivdeki kelebekleri topluca al** deyin.
2. **Tek tek:** kelebek sahnesini Artist'te açıp **Sahneyi tara** deyin.
3. **Adıyla:** yalnızca Show TV adlandırmasını kullanan kelebekler için (`ISIM1`, `TITLE1`,
   `isimlik_bg_1`; pencere sayısı addaki `2LI` / `3LU`'dan). Adları yazıp **Adıyla ekle** deyin.
   Sahne taranmadığı için adlar farklıysa uygulama yanlış alana yazar; emin değilseniz 1 ya da 2.

Sonra listeden eklenecekleri işaretleyip üretin ya da güncelleyin. Aynı adlı sahne (ör.
`3LU_SAG_DSF`) her programda ayrı bir sahnedir; listede her kelebeğin tam yolu yazar, kaynak
süzgeciyle yalnızca o programın kelebeklerini gösterebilirsiniz.

### Claude ile

`kur.bat` çalıştırıldıysa Claude Code'da bu klasörü açıp şöyle yazmak yeterlidir:

> /SHOW_TV_2025/REJI/PROGRAM/KJ/KJ_SAHNESI sahnesinin reji uygulamasını yap, adı NTR Program olsun

> NTR Program'ın sahnesi değişti, güncelle

### Komut satırından

```
python vizapp.py --ad "NTR Program" --sahne /YOL/KJ_SAHNESI --hedef C:\Users\<kullanıcı>\source\repos\NTR_Program
python vizapp.py --sahne /YOL/KJ_SAHNESI --hedef <uygulama klasörü> --guncelle
python vizapp.py ... --kelebek /YOL/KELEBEK --kelebek-via kelebekler.via --kelebekler hepsi
```

## Panelde ne olur

| Bölüm | Açıklama |
|---|---|
| TEKLİ / ÇİFTLİ KJ VER, KJ AL (F7) | Ana butonlar. Yayındayken yeni yazı verilince grafik alınmadan değişir; çiftlide alt satır boşsa tekli verilir |
| BANT | Tek seçimli: NORMAL, YAS, SON DAKİKA, AZ SONRA ... Satır satır kurulmuş bantlar (üst ve alt satır ayrı animasyon) da desteklenir |
| KULAKÇIK | Bandın üstüne eklenen grafik: 4.5G, SKYPE, TELEFON ... |
| FON | Zemin / renk seçimi (dosya yolları sahneden okunamaz; `ogrenilen` klasöründen ya da plandan gelir) |
| İSİMLER listesi | İsim + ünvan; İSİM VER (F3), TELEFON VER (F2), AL (F4) buradan okur |
| Özel butonlar | İSİM, TELEFON, LOKASYON ... Banttan bağımsızdır, kendi AL'ı vardır; lokasyon gibi etiketlerin kendi yazı kutusu olur |
| Öğeler | Ayrı VER / AL: logo (yazılı olabilir, "KJ ile" verilebilir), kapak, ürün yerleştirme (süreli) ... |
| TÜMÜNÜ AL (F8) | Her şeyi alır; bandı, isim / telefonu ve logoyu duruma bakmadan gönderir |
| KELEBEK | Ayrı pencere: kelebek listesi, pencere başına isim + ünvan, VER / AL / GÜNCELLE |

AL butonları duruma bakmadan gönderir: uygulama yeniden açıldığında ekranda kalan grafik de alınabilir.
Buton yazısının sonundaki `(F3)` gibi tuş o butonun kısayoludur; Designer'da yazıyı değiştirmek yeter.

## Kurallar

- Yalnızca `127.0.0.1`. Araç başka adrese bağlanmaz; yazma komutları (SET, START, LOAD, SAVE ...) gönderilmeden reddedilir.
- Üretilen uygulama da geliştirmede yalnızca `127.0.0.1`'e bağlanır (`ShowData\IpList.txt`).
- Araç yalnızca kendi ürettiği uygulamaları (klasöründe `kumanda.json` olanları) günceller.
- viztools açıkken engine'e tek bir bağlantı tutar, kapanınca kapatır.

## Sahneye özel öğrenilmiş ayarlar

FON dosya yolları, logonun yazı alanı, buton adları gibi sahneden okunamayan bilgiler
`ogrenilen\<sahne adı>.json` dosyasında durur. Taranan sahnenin adı bu dosyalardan biriyle aynıysa
analiz onu kendiliğinden uygular; sahne yeniden taranıp sıfırdan üretildiğinde de aynı sonuç çıkar.
Şu an: `HT_SPOR_KJ_v5.json`, `2026_HT_KJ_V02.json`. Sahnenin adı değişirse dosya da yeniden adlandırılır.

## Henüz yok

- ROLL / sayfalı akışlar.
- Kelebekte kayıtlı listeler ve ekran yerleşimi önizlemesi.
- Sarı bant, yas modu gibi banda özel klip seçimleri.
- Yazı rengi ve görünürlük grupları; başka sahne ya da katman kullanan butonlar (separatör, imaj, tanıtım).
- Haber akışı (veritabanı). KJ ve isim listeleri dosyadan gelir.

Bunlar uygulamaya elle eklenir. Uygulamanın sahneyi nasıl sürdüğü ve canlı uygulamalardan
öğrenilen kurallar: `REJI_KALIPLARI.md`.

## Diğer belgeler

- [DEVIR.md](DEVIR.md): aracı ilk kez alan kişi için adım adım anlatım, klasör yapısı
- [skill/vizrt-reji/SKILL.md](skill/vizrt-reji/SKILL.md): Claude'un izlediği iş akışı
- Teknik ayrıntılar (tarama arayüzü, engine komutları, MCP) aşağıdadır.

---

# viztools: Viz Engine salt okunur tarama + sahne şablonu + MCP

Yerel Viz Engine'i (127.0.0.1:6100) **yalnızca okuyarak** tarar, sahnenin tree ve stage
yapısından insan için okunabilir bir şablon (.md) ve kod üretimi için JSON üretir.
Claude Code'a MCP sunucusu olarak bağlanınca Claude bu sorguları doğrudan yapar.

## Sahneden reji uygulaması

En kolayı: `viztools.bat` → sahneyi tara → **Reji uygulaması** sekmesi → seç, düzelt, **Üret ve derle**.
Sahne değişince aynı sekmede **Mevcut uygulamayı güncelle**. Komut satırından aynı iş:

```
python vizapp.py --ad "NTR Yeni Program" --sahne /YOL/KJ_SAHNESI --hedef C:\Users\<kullanici>\source\repos\NTR_Yeni_Program
python vizapp.py --sahne /YOL/KJ_SAHNESI --hedef <uygulama klasoru> --guncelle [--yeniden-planla]
```
Kurulum ve devir: `DEVIR.md`. Claude için iş akışı: `skill\vizrt-reji\SKILL.md` (`kur.bat` kurar).

## Güvenlik (kodla zorlanır)

- Yalnızca `127.0.0.1` / `localhost` / `::1` adresine bağlanır; başka host reddedilir.
- Yalnızca fiili `GET`, `GET_*`, `IS_*` olan komutlar gönderilir. `SET`, `START`, `STOP`,
  `LOAD`, `SAVE`, `DELETE`, `SET_OBJECT` vb. hepsi gönderilmeden reddedilir.
- Graphic Hub'dan yol ile sahne çekme (`SCENE*/HT/...*TREE GET`) kapalıdır; yalnızca
  Artist'te / katmanda zaten yüklü sahne okunur. Veritabanına hiç dokunulmaz.

## Kurulum

```
python -m pip install "mcp>=2"
```

## Başlatma

Çift tıklayın: `viztools.bat` (yerel sunucuyu açar ve tarayıcıda arayüzü gösterir).
Ya da:

```
python vizscan_web.py
```

Arayüz http://127.0.0.1:8765 adresinde açılır; yalnızca bu bilgisayardan erişilir.
Solda kaynak kartları (canlı engine / .via), ortada aranabilir director ve container
ağacı, sağda seçilen öğenin komutları (tıklayınca panoya kopyalanır). Çıktılar
kartındaki düğmeler şablonu, C# dosyasını ve JSON'u açar. Eski Tkinter arayüzü
(`vizscan_ui.py`) de duruyor.

## Adım adım kullanım (arayüz ile)

1. Viz Artist'i açın, sahneyi yükleyin. Stage panelinde ve Scene Tree'de **tüm dalları açın**
   (sağ tık > Expand All), sahneyi **kaydedin**. Kapalı dallar engine'den okunamaz.
2. Arayüzü başlatın:

   ```
   python vizscan_ui.py
   ```

3. **Durum** düğmesi: engine'e bağlanıyor mu, hangi katmanda hangi sahne yüklü.
4. **Sahneyi Tara**: birkaç saniye sonra solda director'lar, sağda container ağacı dolar.
   Üstteki durum satırı kapalı director sayısını söyler; varsa Artist'te açıp kaydedin, tekrar tarayın.
5. **Ara** kutusuna isim yazın (örneğin `KJ_TEK_1`); iki tablo da filtrelenir.
6. Bir director'a tıklayın: altta START / CONTINUE / STOP komutları ve VizScript karşılığı
   görünür. Bir container'a tıklayın: TEXT SET / ACTIVE SET / POSITION SET komutları ve
   VizScript karşılığı görünür. **Çift tık** komut yolunu panoya kopyalar.
7. **Komut** kutusu: elle GET komutu yazıp **Gönder** ile cevabı görürsünüz. SET/START gibi
   yazma komutları gönderilmeden reddedilir; bu araç sahneyi hiçbir zaman değiştirmez.
8. **Şablonu Aç (.md)**: taramanın tam dokümanı (director tablosu, komutlar, container ağacı,
   VizScript iskeleti). Ekibe vereceğiniz dosya budur; `scenes/` klasöründe durur.

Arayüzde ayrıca: **Son açılanlar** menüsü (son 8 .via/sahne), sağ tık menüsü (yol, START,
TEXT SET, VizScript satırını kopyala), çift tık yolu kopyalar, **Tümünü aç / Kapat**,
Ctrl+F arama, **Kapalı director'ları kopyala** (Artist'te açılacak listeyi verir),
**VizScript kopyala** (iskeleti panoya), **C# sabitleri üret**. Pencere boyutu, katman ve
son klasör hatırlanır (`.viztools_ui.json`).

## C# sabitleri (uygulama kodu için)

Taramadan `scenes/<Sahne>.cs` üretilir: `Directors.KJ_IN`, `Containers.KJ_TEK_1_TEXT` gibi
yol sabitleri ve `DirectorStart(...)`, `SetText(...)`, `SetActive(...)` gibi komut metni
üreten yardımcılar. Dosyayı projeye ekleyip elle yazılmış `"...*STAGE*DIRECTOR*$X START"`
string'leri yerine sabitleri kullanırsınız; sahne değişince yeniden üretirsiniz, derleyici
kaybolan director'ı hemen gösterir. Aynı isimli öğeler tam yoldan adlandırılır, dosya
`dotnet build` ile doğrulandı.

```
python vizscan.py --details --csharp                      # canlı engine'den
python vizscan.py --via ht2026.via --scene 2026_HT_KJ_dev2 --csharp --namespace HT.Viz
```

Claude'da: `viz_scene_csharp` (canlı ya da via_path ile).

## .via dosyasından okuma (engine kapalıyken)

Artist'te Archive ile dışa aktarılmış `.via` dosyası engine olmadan okunur. Bir arşivde
onlarca sahne olabilir (ht2026.via: 52 sahne, 159 resim, 27 font); arayüz açınca sahne
listesi çıkar, filtreleyip birini seçersiniz. Komut satırında:

```
python vizscan.py --via C:\yol\ht2026.via                 # sahneleri listeler
python vizscan.py --via C:\yol\ht2026.via --scene 2026_HT_KJ_dev2
```

Claude'da `viz_via_scenes` ve `viz_via_dump`. Dosyadan **container ağacı, geometri/plugin
adları ve director hiyerarşisi** çıkar; 700 container'lık sahne 2 saniyede okunur.
Director'ların hangi kanalı oynattığı, aktiflik ve text değerleri .via biçiminden
çıkarılamaz; bunlar için canlı tarama gerekir.

Biçim resmi olarak belgelenmediği için okuyucu `samples/` altındaki örneklerden
çıkarıldı (`vizengine/via.py` başındaki açıklama): nesne verisi 51200 baytlık dilimlere
bölünür (her dilim `u16 sıra + u32 uzunluk` başlığı taşır), dilimler soyulunca ortaya
çıkan veri `u32 sıkıştırılmış + u32 açık uzunluk + zlib` parçalarından oluşur ve her
parça adler32 sağlamasıyla doğrulanır. HT_SPOR_KJ_v5 sahnesinde .via okuması canlı
taramayla **birebir** aynı sonucu verdi (316 container aynı sıra ve yollarla, 63 director).

## Komut satırından kullanım

Artist'te sahneyi açın, Scene Tree ve Stage panellerinde tüm dalları açıp (expand)
sahneyi kaydedin. Sonra:

```
python vizscan.py                 # MAIN_SCENE'i tarar -> scenes/<sahne>.md + .json
python vizscan.py --details       # her container'ın GEOM*TEXT değerini de okur
python vizscan.py --layer FRONT_SCENE
python vizscan.py --send "MAIN_SCENE*STAGE*DIRECTOR GET"
```

Kapalı (expand edilmemiş) director dalları engine cevabında görünmez; tarayıcı bunları
`UYARI:` satırıyla bildirir. Uyarı görürseniz Artist'te o dalı açıp kaydedin, tekrar tarayın.

## Engine çıktı formatı (gerçek engine'de doğrulandı)

- `TREE GET`: `{yol id isim [bayrak]}` düz liste. Sondaki sayı Artist ağacında dalın
  **açık/kapalı** olmasıdır, aktiflik DEĞİLDİR; yapraklarda yoktur. Aktiflik `*ACTIVE GET` ile okunur.
- `STAGE GET`: düz liste, hiyerarşi yoldan kurulur (`6`, `6/4`, `6/4/0`). Director ve
  CONTAINER satırlarında isimden sonraki ilk sayı **açık (1) / kapalı (0) / boş (-1)**; kapalıysa
  altındaki satırlar hiç gelmez. `-1` altı boş director'dır (açılacak bir şey yok), kapalı sayılmaz. Kapalı dallar şablonda "KAPALI (okunamadı)" olarak işaretlenir.
- Engine UTF-8 gönderir; Türkçe karakterler doğru çözülür.

## Şablon (.md) içinde ne var

- Director tablosu: isim, komut yolu (`$ust$alt`), hangi container/kanalları oynattığı
- Her director için hazır `START / CONTINUE / STOP / GOTO_TRIO` komutları
- Container ağacı: girintili, yanında `$isim$yolu`, #id, aktif/pasif, (details ile) text
- Her container için hazır `GEOM*TEXT SET` satırı
- VizScript iskeleti: tüm container ve director referansları `OnInit` içinde hazır

## Claude Code'a MCP olarak bağlama

Kalıcı bir klasöre taşıdıktan sonra (bu klasör silinirse sunucu da gider), kullanıcı
seviyesinde kaydedin ki her projede görünsün:

```
claude mcp add --scope user vizengine -- python "C:\TAM\YOL\viztools\viz_mcp_server.py"
```

Ya da proje köküne `.mcp.json` koyun (örnek: `mcp.example.json`). Ortam değişkenleri:
`VIZ_PORT` (varsayılan 6100), `VIZ_SCENES_DIR` (şablonların yazılacağı klasör).

Claude'un göreceği araçlar:

| Araç | Ne yapar |
|---|---|
| `viz_status` | Engine erişilebilir mi, on-air mi, katmanlarda ne yüklü |
| `viz_send` | Ham komut (yalnızca GET) |
| `viz_tree` | Container ağacı, `$isim$yolu` ve id'lerle |
| `viz_stage` | Director'lar, alt director'lar, animasyonlu container/kanallar, kapalı dal uyarısı |
| `viz_container` | Tek container'ın NAME / ACTIVE / TEXT / POSITION / ALPHA / IMAGE değerleri |
| `viz_scene_dump` | Tam tarama; .md şablonu ve .json'u yazar, şablonu döndürür |
| `viz_scene_json` | Sahne modelini JSON olarak verir (C# sabit üretimi vb. için) |

## Dosyalar

- `vizengine/analiz.py`: sahneden bant, kulakçık, özel tür, öğe çıkarımı
- `vizengine/kelebek.py`: kelebek sahnesi tanıma, arşivden toplu içe alma
- `vizengine/uretec.py`: C# üretici; `vizengine/uygulama.py`: üretim akışı ve plan onarımı
- `vizapp.py`, `vizuret.py`: sahneden / plandan üretim (komut satırı)
- `sablon/winforms/`: uygulama şablonu (sahneden bağımsız kod)
- `ogrenilen/`: sahneye özel, canlı uygulamalardan öğrenilmiş ayarlar
- `REJI_KALIPLARI.md`: canlı uygulamalardan öğrenilen reji ve kelebek kuralları
- `vizengine/client.py`: TCP istemci ve salt okunur komut filtresi
- `vizengine/parse.py`: `TREE GET` ve `STAGE GET` çözümleyicileri
- `vizengine/template.py`: sahne modeli, Markdown şablon, dosya yazma
- `vizscan.py`: komut satırı aracı
- `viztools.bat`: çift tıkla başlat (web arayüzü)
- `vizscan_web.py` + `web/`: web arayüzü (yerel sunucu, 127.0.0.1:8765)
- `vizscan_ui.py`: eski tek pencereli arayüz (Tkinter)
- `vizengine/via.py`: .via arşiv okuyucu
- `vizengine/gen_csharp.py`: C# sabit sınıfı üretici
- `samples/`: örnek .via dosyaları
- `viz_mcp_server.py`: MCP sunucusu (stdio)
- `scenes/<Sahne>/`: her sahnenin çıktıları kendi klasöründe: `<Sahne>.md` (şablon),
  `<Sahne>.json` (model), `<Sahne>.cs` (C# sabitleri)
