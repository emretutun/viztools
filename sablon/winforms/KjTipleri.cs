namespace __NS__
{
    /// <summary>
    /// Ayni grafigin ek yuvasi (X_2 gibi): kendi giris director'u ve metin alanlari. Grafik yayindayken yeni metin
    /// verilince grafik alinmaz; siradaki yuvaya yazilip onun girisi oynatilir.
    /// </summary>
    public sealed record KjYuva(string Giris, string Ust, string? Alt, string Cikis, string? Ayirac = null);

    /// <summary>Metinli KJ turu: giris/cikis director'u ve ust/alt metin container'i (tam yollar).</summary>
    public sealed class KjTipi
    {
        public string Kod { get; init; } = "";
        public string Etiket { get; init; } = "";
        public string Giris { get; init; } = "";
        public string Cikis { get; init; } = "";
        public string Ust { get; init; } = "";
        public string? Alt { get; init; }
        /// <summary>Ayni ekran bolgesini paylasan turler ayni alani tasir (biri girerken digeri cikar).</summary>
        public string Alan { get; init; } = KjTipleri.BantAlani;
        /// <summary>Ek yuvalar (1. yuva turun kendisidir). Bos ise metin degisiminde ayni giris yeniden oynatilir.</summary>
        public IReadOnlyList<KjYuva> Yuvalar { get; init; } = Array.Empty<KjYuva>();
        /// <summary>Alt satir bosken gizlenen ayirac container'i (isim / unvan arasindaki cizgi gibi).</summary>
        public string? Ayirac { get; init; }
        /// <summary>Fotografli grafikte resmin yazildigi container; ResimVarsayilan: dosya secilmediginde gonderilen yol.</summary>
        public string? Resim { get; init; }
        public string? ResimVarsayilan { get; init; }
        /// <summary>Ozel turun metin kaynagi: "liste" (KJ listesi), "isim" (ISIMLER listesi), "kutu" (butonun ustundeki kutu).</summary>
        public string Kaynak { get; init; } = "liste";
        /// <summary>
        /// Satir bazli bant: bu tur UST satirdir; alt satir ayri bir turdur (AltTur = kodu) ve AltCikis ile alinir.
        /// CIFTLI = ust satir + alt satir. Yazi degisince yalnizca degisen satir kendi yuvalari arasinda doner.
        /// </summary>
        public string? AltTur { get; init; }
        public string? AltCikis { get; init; }

        /// <summary>AL'da oynatilacak cikislar: turun cikisi ve (farkliysa) yuvalarin kendi cikislari.</summary>
        public IEnumerable<string> Cikislar => new[] { Cikis }.Concat(Yuvalar.Select(y => y.Cikis)).Distinct();

        /// <summary>Yuva numarasina (0 = turun kendisi) gore giris ve metin alanlari.</summary>
        public (string Giris, string Ust, string? Alt, string? Ayirac) Yuva(int no) =>
            no <= 0 || no > Yuvalar.Count ? (Giris, Ust, Alt, Ayirac)
                : (Yuvalar[no - 1].Giris, Yuvalar[no - 1].Ust, Yuvalar[no - 1].Alt, Yuvalar[no - 1].Ayirac);

        public bool CiftSatir => Alt != null || AltTur != null;
        public override string ToString() => Etiket;
    }

    /// <summary>ISIMLER listesinin satiri (ShowData/isimler.json): isim + unvan.</summary>
    public sealed class IsimKaydi
    {
        [System.Text.Json.Serialization.JsonPropertyName("isim")] public string Isim { get; set; } = "";
        [System.Text.Json.Serialization.JsonPropertyName("titr")] public string Titr { get; set; } = "";
    }

    /// <summary>
    /// Tur mantigi (sahneden bagimsiz). Sahneye ait veriler KjTipleri.Sahne.cs'tedir ve
    /// viztools ureticisi tarafindan kumanda.json'dan yazilir: Tumu, Varyantlar, Kulakciklar, Ozeller, Ogeler, FonSecenekleri, FonAyarlari.
    /// </summary>
    public static partial class KjTipleri
    {
        /// <summary>Bant turlerinin ortak alani. Ozel turler kendi alanindadir (banttan bagimsiz verilir/alinir).</summary>
        public const string BantAlani = "altbant";

        /// <summary>BANT: secici anahtari ("" = NORMAL) + TEKLI/CIFTLI butonu -> verilecek tur kodu.</summary>
        public sealed record Varyant(string Anahtar, string Etiket, string Tek, string Cift);

        /// <summary>KULAKCIK: bandin ustune eklenen grafik; metin yazilmaz, yalnizca IN/OUT oynatilir.</summary>
        public sealed record Kulakcik(string Anahtar, string Etiket, string Giris, string Cikis);

        /// <summary>OZEL: kendi VER/AL butonu olan, banttan bagimsiz tur (ISIMLIK, TELEFON, LOKASYON gibi).</summary>
        public sealed record Ozel(string Kod, string Etiket);

        /// <summary>OGE: metinsiz grafik, ayri VER/AL (logo, kapak, saat gibi).</summary>
        public sealed record Oge(string Anahtar, string Etiket, string Giris, string Cikis)
        {
            /// <summary>Ogenin yazi alani (yazili logo gibi); null ise metinsizdir.</summary>
            public string? Metin { get; init; }
            /// <summary>VER'den once gorunur yapilan container'lar.</summary>
            public IReadOnlyList<string> Gorunur { get; init; } = Array.Empty<string>();
            /// <summary>0'dan buyukse VER'den bu kadar saniye sonra kendiliginden alinir (kutusu isaretliyse).</summary>
            public int OtoAlSn { get; init; }
            /// <summary>VER'den once ekrandaki bandi alir (bantla ayni yeri kullanan grafik).</summary>
            public bool BandiAl { get; init; }
        }

        /// <summary>
        /// FON (zemin / renk) ayari. Hedef: ayarin uygulanacagi alan, tur kodu ya da oge anahtari.
        /// Tip: "imageclip", "image" (Yol = container) ya da "director" (Yol = director, deger START | REVERSE).
        /// Degerler: FON secenegi -> deger; "*" diger secenekler icin.
        /// </summary>
        public sealed record FonAyari(string Hedef, string Tip, string Yol, IReadOnlyDictionary<string, string> Degerler);

        public static KjTipi? Bul(string? kod) =>
            Tumu.FirstOrDefault(t => string.Equals(t.Kod, kod?.Trim(), StringComparison.OrdinalIgnoreCase));

        public static Kulakcik? KulakcikBul(string? anahtar) =>
            Kulakciklar.FirstOrDefault(k => k.Anahtar == (anahtar ?? ""));

        public static Oge? OgeBul(string? anahtar) =>
            Ogeler.FirstOrDefault(o => o.Anahtar == (anahtar ?? ""));

        /// <summary>Listede ve "Yeni KJ" kutusunda secilebilen turler.</summary>
        public static IEnumerable<KjTipi> ListeTurleri() =>
            Tumu.Where(t => (t.Alan == BantAlani || t.Kaynak == "liste") && !Tumu.Any(x => x.AltTur == t.Kod));

        /// <summary>Tek bant var ve KJ listesinden baska tur verilmiyor: listede TUR sutununa gerek yok.</summary>
        public static bool TekBant => Varyantlar.Count == 1 && ListeTurleri().All(t => t.Alan == BantAlani);

        /// <summary>Kayit bu surumde taninmayan bir tur tasiyorsa (sahne degismis) dokunma; arayuz uyarir.</summary>
        public static void Duzelt(KjKaydi kj) { }

        /// <summary>Bant anahtari + basilan buton -> verilecek tur.</summary>
        public static KjTipi? Coz(string? anahtar, bool cift)
        {
            var v = Varyantlar.FirstOrDefault(x => x.Anahtar == (anahtar ?? "")) ?? Varyantlar.FirstOrDefault();
            return v == null ? null : Bul(cift ? v.Cift : v.Tek);
        }

        /// <summary>
        /// Satirin tur kodundan bant anahtarini ve tekli/ciftli bilgisini cikarir.
        /// Cift == null: tur tek bicimli (tekli ve ciftli ayni tur). Bant degilse (ozel tur) null.
        /// </summary>
        public static (string Anahtar, bool? Cift)? Ayristir(string? kod)
        {
            foreach (var v in Varyantlar)
            {
                bool tek = string.Equals(v.Tek, kod, StringComparison.OrdinalIgnoreCase);
                bool cift = string.Equals(v.Cift, kod, StringComparison.OrdinalIgnoreCase);
                if (tek && cift) return (v.Anahtar, null);
                if (tek) return (v.Anahtar, false);
                if (cift) return (v.Anahtar, true);
            }
            return null;
        }
    }
}
