using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Unicode;

namespace __NS__
{
    /// <summary>
    /// Veri ve ayarlar (DB yok). Calisma dizini ShowData'dir:
    ///   scenes.txt   basepath + sahne yollari (KJ_Scenes, kelebekler)
    ///   setting      "General Delay:40" gibi ayarlar
    ///   kj_list.json bolumler ve KJ satirlari
    /// </summary>
    public class CSceneDataController
    {
        public const string KjDosyasi = "kj_list.json";
        public const string OrnekDosya = "kj_list.ornek.json";   // ilk acilista kj_list.json buradan olusturulur

        /// <summary>Her komuttan sonra bekleme (ms). CClientSession kullanir.</summary>
        public int GeneralDelay { get; set; } = 40;
        public bool FasterSend { get; set; } = false;

        public string KJ_Scenes { get; set; } = KjTipleri.SahneYolu;
        public Dictionary<string, string> Kelebekler { get; } = new Dictionary<string, string>();

        public KjListesi Kj { get; private set; } = new KjListesi();

        private static readonly JsonSerializerOptions JsonAyar = new JsonSerializerOptions
        {
            WriteIndented = true,
            Encoder = JavaScriptEncoder.Create(UnicodeRanges.All),
            PropertyNameCaseInsensitive = true,
        };

        public CSceneDataController()
        {
            AyarlariOku();
            SahneleriOku();
            KjYukle();
        }

        // ------------------------------------------------------------ KJ JSON --
        public void KjYukle()
        {
            KjOku();
            // Eski bicimde kulakcik turu bant gibi yazilmissa duzelt (normal bant + kulakcik)
            foreach (var b in Kj.Bolumler)
                foreach (var kj in b.Kjler)
                    KjTipleri.Duzelt(kj);
        }

        private void KjOku()
        {
            if (File.Exists(KjDosyasi))
            {
                Kj = JsonSerializer.Deserialize<KjListesi>(File.ReadAllText(KjDosyasi), JsonAyar) ?? new KjListesi();
            }
            else if (File.Exists(OrnekDosya))
            {
                File.Copy(OrnekDosya, KjDosyasi);
                Kj = JsonSerializer.Deserialize<KjListesi>(File.ReadAllText(KjDosyasi), JsonAyar) ?? new KjListesi();
            }
            else
            {
                Kj = new KjListesi();
                Kj.Bolumler.Add(new KjBolumu { Baslik = "Genel" });
                KjKaydet();
            }
        }

        public void KjKaydet()
        {
            string tmp = KjDosyasi + ".tmp";
            File.WriteAllText(tmp, JsonSerializer.Serialize(Kj, JsonAyar));
            File.Copy(tmp, KjDosyasi, true);
            File.Delete(tmp);
        }

        // ---------------------------------------------------------- dosyalar --
        private void AyarlariOku()
        {
            if (!File.Exists("setting")) return;
            foreach (var satir in File.ReadAllLines("setting"))
            {
                int i = satir.IndexOf(':');
                if (i < 0) continue;
                string anahtar = satir[..i].Trim(), deger = satir[(i + 1)..].Trim();
                if (anahtar.Equals("General Delay", StringComparison.OrdinalIgnoreCase) && int.TryParse(deger, out int ms))
                    GeneralDelay = Math.Max(0, ms);
            }
        }

        private void SahneleriOku()
        {
            if (!File.Exists("scenes.txt")) return;
            string basepath = "";
            foreach (string ham in File.ReadAllLines("scenes.txt"))
            {
                string satir = ham.Trim();
                if (satir.Length == 0 || satir.StartsWith("//") || satir.StartsWith("#")) continue;
                int i = satir.IndexOf('=');
                if (i < 0) continue;
                string anahtar = satir[..i].Trim(), deger = satir[(i + 1)..].Trim();

                if (anahtar.Equals("basepath", StringComparison.OrdinalIgnoreCase)) basepath = deger;
                else if (anahtar.Equals("KJ_Scenes", StringComparison.OrdinalIgnoreCase)) KJ_Scenes = Yol(basepath + deger);
                else Kelebekler[anahtar] = Yol(basepath + deger);
            }
        }

        private static string Yol(string y) => y.StartsWith("/") ? y : "/" + y;
    }
}
