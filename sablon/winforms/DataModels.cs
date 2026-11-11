using System.Text.Json.Serialization;

namespace __NS__
{
    /// <summary>ShowData/kj_list.json kok nesnesi. Basit, DB'siz veri modeli.</summary>
    public class KjListesi
    {
        [JsonPropertyName("bolumler")]
        public List<KjBolumu> Bolumler { get; set; } = new List<KjBolumu>();
    }

    /// <summary>Program bolumu / konu (soldaki listede gorunur).</summary>
    public class KjBolumu
    {
        [JsonPropertyName("baslik")]
        public string Baslik { get; set; } = "";

        [JsonPropertyName("kjler")]
        public List<KjKaydi> Kjler { get; set; } = new List<KjKaydi>();
    }

    /// <summary>Tek KJ satiri. "tur", KjTipleri.Tumu icindeki bir Kod.</summary>
    public class KjKaydi
    {
        [JsonPropertyName("tur")]
        public string Tur { get; set; } = "";

        [JsonPropertyName("satir1")]
        public string Satir1 { get; set; } = "";

        [JsonPropertyName("satir2")]
        public string Satir2 { get; set; } = "";

        /// <summary>Bandin ustune eklenecek kulakcik anahtari ("" = yok); KjTipleri.Kulakciklar.</summary>
        [JsonPropertyName("kulakcik")]
        public string Kulakcik { get; set; } = "";

        [JsonIgnore]
        public KjTipi? Tipi => KjTipleri.Bul(Tur);
    }
}
