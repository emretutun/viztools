namespace __NS__
{
    /// <summary>
    /// Kelebek penceresi: isim ve unvan yazi alani. Gizle: isim bosken gizlenen container (isimlik zemini / grubu).
    /// TitrGizle: unvan bosken unvan alaninin kendisi gizlenir.
    /// </summary>
    public sealed record KelebekPencere(string Isim, string? Titr, string? Gizle, bool TitrGizle);

    /// <summary>
    /// Kelebek sahnesi (bolunmus ekran: 2'li, 3'lu, 4'lu ... pencere). Ikinci motorda (GRAFIK-1), arka katmanda oynar.
    /// Akis:
    ///   "duz"      : yazilar gonderilir, sahne katmana konur; AL katmani bosaltir (Show TV kelebekleri)
    ///   "stage"    : sahne katmana konur, sahnenin tum animasyonu bastan oynatilir; yazi yok
    ///   "director" : BASA_CEK, sahne katmana konur, IN oynar; isimler ISIM_IN / ISIM_TITRI_IN ile ayrica girer,
    ///                AL = BASA_CEK (Haberturk / HT Spor kelebekleri)
    /// </summary>
    public sealed class KelebekTipi
    {
        public string Anahtar { get; init; } = "";
        public string Etiket { get; init; } = "";
        public string Sahne { get; init; } = "";
        public string Akis { get; init; } = "duz";
        public IReadOnlyList<KelebekPencere> Pencereler { get; init; } = Array.Empty<KelebekPencere>();
        public string? Giris { get; init; }
        public string? BasaCek { get; init; }
        public string? IsimIn { get; init; }
        public string? IsimOut { get; init; }
        public string? TitrIn { get; init; }
        public string? TitrOut { get; init; }
        /// <summary>Giristen once gorunur yapilan container'lar.</summary>
        public IReadOnlyList<string> Gorunur { get; init; } = Array.Empty<string>();
        /// <summary>Arka plan klibinin (SoftClip) container'i; KelebekTipleri.KlipDosya doluysa giristen once gonderilir.</summary>
        public string? Klip { get; init; }

        public bool IsimAnimasyonlu => IsimIn != null && IsimOut != null;
        public bool TitrAnimasyonlu => IsimAnimasyonlu && TitrIn != null && TitrOut != null;
        public override string ToString() => Etiket;
    }

    /// <summary>Sahneye ait veriler KelebekTipleri.Sahne.cs'tedir (uretici yazar): Tumu, Katman, KlipDosya.</summary>
    public static partial class KelebekTipleri
    {
        /// <summary>Katman adi: "BACK" ya da "MAIN" -> RENDERER*BACK_LAYER / BACK_SCENE.</summary>
        public static string KatmanAdi => string.Equals(Katman, "MAIN", StringComparison.OrdinalIgnoreCase) ? "MAIN" : "BACK";
    }
}
