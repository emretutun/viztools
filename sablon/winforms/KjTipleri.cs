namespace __NS__
{
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
        public string Alan { get; init; } = "altbant";

        public bool CiftSatir => Alt != null;
        public override string ToString() => Etiket;
    }

    /// <summary>
    /// Tur mantigi (sahneden bagimsiz). Sahneye ait veriler KjTipleri.Sahne.cs'tedir ve
    /// viztools ureticisi tarafindan kumanda.json'dan yazilir: Tumu, Varyantlar, Kulakciklar, Ozeller, Ogeler.
    /// </summary>
    public static partial class KjTipleri
    {
        /// <summary>BANT: secici anahtari ("" = NORMAL) + TEKLI/CIFTLI butonu -> verilecek tur kodu.</summary>
        public sealed record Varyant(string Anahtar, string Etiket, string Tek, string Cift);

        /// <summary>KULAKCIK: bandin ustune eklenen grafik; metin yazilmaz, yalnizca IN/OUT oynatilir.</summary>
        public sealed record Kulakcik(string Anahtar, string Etiket, string Giris, string Cikis);

        /// <summary>OZEL: kendi VER butonu olan tek satirli tur (ISIMLIK, LOKASYON gibi).</summary>
        public sealed record Ozel(string Kod, string Etiket);

        /// <summary>OGE: metinsiz grafik, ayri VER/AL (logo, kapak, saat gibi).</summary>
        public sealed record Oge(string Anahtar, string Etiket, string Giris, string Cikis);

        public static KjTipi? Bul(string? kod) =>
            Tumu.FirstOrDefault(t => string.Equals(t.Kod, kod?.Trim(), StringComparison.OrdinalIgnoreCase));

        public static Kulakcik? KulakcikBul(string? anahtar) =>
            Kulakciklar.FirstOrDefault(k => k.Anahtar == (anahtar ?? ""));

        public static Oge? OgeBul(string? anahtar) =>
            Ogeler.FirstOrDefault(o => o.Anahtar == (anahtar ?? ""));

        /// <summary>Listede ve "Yeni KJ" kutusunda secilebilen turler.</summary>
        public static IEnumerable<KjTipi> ListeTurleri() => Tumu;

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
