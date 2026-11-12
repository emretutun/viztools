using System.Text.Json;

namespace __NS__
{
    /// <summary>
    /// KELEBEK penceresi (sahneden bagimsiz; sahneler KelebekTipleri.Sahne.cs'te). Canli uygulamalardaki akis:
    ///   VER      : "duz" -> yazilar + gorunurluk, sonra sahne katmana; "stage" -> katmana, STAGE bastan oynar;
    ///              "director" -> BASA_CEK, katmana, gorunur, 300 ms, IN (isimler ayrica verilir)
    ///   AL       : "director" -> BASA_CEK; digerleri -> katman bosaltilir (kesme)
    ///   ISIM VER / ISIM TITR VER : ISIM_IN / ISIM_TITRI_IN animasyonlari (0 = yok, 1 = isim, 2 = isim + unvan), arada 700 ms
    ///   GUNCELLE : yazilari animasyonsuz yeniden gonderir
    /// Isim listesi KJ panelindeki ISIMLER ile ortaktir (isimler.json); son girilenler kelebek_data.json'da saklanir.
    /// Kelebek KJ motoruna dokunmaz; yalnizca GRAFIK-1 motoruna gonderir.
    /// </summary>
    public sealed class KelebekForm : Form
    {
        private const int GirisBeklemeMs = 300;      // katmana koyduktan sonra IN oncesi
        private const int IsimTitrBeklemeMs = 700;   // isim ile unvan animasyonu arasi
        private const int TiklamaEngeliMs = 1000;
        private const string VeriDosyasi = "kelebek_data.json";
        private const string IsimDosyasi = "isimler.json";

        private readonly Vizrt viz;
        private readonly Action<string, string> log;

        private readonly ListBox lst = new();
        private readonly Label lblYayin = new();
        private readonly Label lblBilgi = new();
        private readonly List<(Label No, ComboBox Isim, TextBox Titr, Button Temizle)> satirlar = new();
        private readonly Button btnVer = new(), btnAl = new(), btnGuncelle = new(), btnIsim = new(), btnIsimTitr = new(), btnTemizle = new();

        private KelebekTipi? yayinda;
        private int isimDurum;                 // 0 = isim yok, 1 = isim, 2 = isim + unvan
        private bool mesgul;
        private DateTime sonTik = DateTime.MinValue;
        private Dictionary<string, string> isimler = new(StringComparer.CurrentCultureIgnoreCase);

        private sealed class Satir { public string Isim { get; set; } = ""; public string Titr { get; set; } = ""; }

        public KelebekForm(Vizrt grafikMotoru, Action<string, string> logla)
        {
            viz = grafikMotoru;
            log = logla;
            Text = "KELEBEK";
            StartPosition = FormStartPosition.CenterParent;
            Font = new Font("Segoe UI", 9.75F);
            BackColor = Color.LightCyan;
            int adet = Math.Max(2, KelebekTipleri.Tumu.Select(k => k.Pencereler.Count).DefaultIfEmpty(0).Max());
            ClientSize = new Size(1010, Math.Max(430, 96 + adet * 46 + 150));
            MinimumSize = Size;

            var baslik = new Label { Text = "KELEBEKLER", Location = new Point(12, 10), Size = new Size(260, 22), Font = new Font("Segoe UI", 10F, FontStyle.Bold) };
            lst.Location = new Point(12, 36);
            lst.Size = new Size(260, ClientSize.Height - 48);
            lst.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left;
            lst.Font = new Font("Segoe UI", 11F, FontStyle.Bold);
            lst.IntegralHeight = false;
            foreach (var k in KelebekTipleri.Tumu) lst.Items.Add(k);
            lst.SelectedIndexChanged += (s, e) => SecimDegisti();

            lblYayin.Location = new Point(288, 10);
            lblYayin.Size = new Size(700, 24);
            lblYayin.Font = new Font("Segoe UI", 11F, FontStyle.Bold);
            lblYayin.ForeColor = Color.DarkRed;
            lblBilgi.Location = new Point(288, 36);
            lblBilgi.Size = new Size(700, 20);
            lblBilgi.ForeColor = Color.DimGray;

            Controls.AddRange(new Control[] { baslik, lst, lblYayin, lblBilgi });

            for (int i = 0; i < adet; i++)
            {
                int y = 66 + i * 46;
                var no = new Label { Text = (i + 1) + ".", Location = new Point(288, y + 6), Size = new Size(28, 24), Font = new Font("Segoe UI", 12F, FontStyle.Bold) };
                var isim = new ComboBox { Location = new Point(320, y), Size = new Size(270, 28), DropDownStyle = ComboBoxStyle.DropDown, Font = new Font("Segoe UI", 11F) };
                var titr = new TextBox { Location = new Point(598, y), Size = new Size(320, 28), Font = new Font("Segoe UI", 11F) };
                var sil = new Button { Text = "SİL", Location = new Point(926, y), Size = new Size(64, 30) };
                isim.SelectedIndexChanged += (s, e) => { if (isimler.TryGetValue(isim.Text, out var t)) titr.Text = t; };
                sil.Click += (s, e) => { isim.Text = ""; titr.Text = ""; };
                satirlar.Add((no, isim, titr, sil));
                Controls.AddRange(new Control[] { no, isim, titr, sil });
            }

            int by = 66 + adet * 46 + 14;
            Buton(btnVer, "VER", 320, by, 150, 60, Color.LimeGreen, async (s, e) => await VerAsync());
            Buton(btnAl, "AL", 478, by, 110, 60, null, (s, e) => Al("AL"));
            Buton(btnGuncelle, "İSİM / ÜNVAN GÜNCELLE", 598, by, 200, 60, null, (s, e) => Guncelle());
            Buton(btnTemizle, "TÜMÜNÜ SİL", 806, by, 184, 60, null, (s, e) => { foreach (var r in satirlar) { r.Isim.Text = ""; r.Titr.Text = ""; } });
            Buton(btnIsim, "İSİM VER", 320, by + 68, 268, 48, Color.Khaki, async (s, e) => await IsimVerAsync());
            Buton(btnIsimTitr, "İSİM + ÜNVAN VER", 598, by + 68, 268, 48, Color.Khaki, async (s, e) => await IsimTitrVerAsync());

            Load += (s, e) => { IsimleriOku(); VerileriOku(); if (lst.Items.Count > 0 && lst.SelectedIndex < 0) lst.SelectedIndex = 0; DurumuYaz(); };
            Activated += (s, e) => IsimleriOku();
            FormClosing += (s, e) =>
            {
                VerileriYaz();
                if (e.CloseReason == CloseReason.UserClosing) { e.Cancel = true; Hide(); }   // yayindaki kelebek durumu kaybolmasin
            };
        }

        private void Buton(Button b, string metin, int x, int y, int w, int h, Color? renk, EventHandler olay)
        {
            b.Text = metin;
            b.Location = new Point(x, y);
            b.Size = new Size(w, h);
            b.Font = new Font("Candara", 12F, FontStyle.Bold);
            if (renk != null) { b.BackColor = renk.Value; b.FlatStyle = FlatStyle.Flat; }
            b.Click += olay;
            Controls.Add(b);
        }

        private KelebekTipi? Secili => lst.SelectedItem as KelebekTipi;
        private string Layer => "RENDERER*" + KelebekTipleri.KatmanAdi + "_LAYER";
        private string Stage => KelebekTipleri.KatmanAdi + "_SCENE*STAGE";

        // ------------------------------------------------------------------ arayuz
        private void SecimDegisti()
        {
            var k = Secili;
            int n = k?.Pencereler.Count ?? 0;
            for (int i = 0; i < satirlar.Count; i++)
            {
                bool acik = i < n;
                satirlar[i].No.Enabled = satirlar[i].Isim.Enabled = satirlar[i].Titr.Enabled = satirlar[i].Temizle.Enabled = acik;
                satirlar[i].Titr.Enabled = acik && k!.Pencereler[i].Titr != null;
            }
            lblBilgi.Text = k == null ? "" : n == 0 ? "Bu kelebekte yazı alanı yok." : $"{n} pencere  ·  {k.Sahne}";
            DurumuYaz();
        }

        private void DurumuYaz()
        {
            var k = yayinda;
            lblYayin.Text = k == null ? "YAYINDA: -" : "YAYINDA: " + k.Etiket + (isimDurum == 1 ? "  (isim)" : isimDurum == 2 ? "  (isim + ünvan)" : "");
            btnVer.BackColor = k != null && k == Secili ? Color.Red : Color.LimeGreen;
            btnVer.ForeColor = k != null && k == Secili ? Color.White : Color.Black;
            var hedef = k ?? Secili;
            btnIsim.Enabled = k != null && k.IsimAnimasyonlu;
            btnIsimTitr.Enabled = k != null && k.TitrAnimasyonlu;
            btnIsim.Visible = hedef?.IsimAnimasyonlu ?? false;
            btnIsimTitr.Visible = hedef?.TitrAnimasyonlu ?? false;
            btnGuncelle.Enabled = (hedef?.Pencereler.Count ?? 0) > 0;
            btnIsim.BackColor = isimDurum >= 1 ? Color.Red : Color.Khaki;
            btnIsimTitr.BackColor = isimDurum == 2 ? Color.Red : Color.Khaki;
        }

        private bool Bagli()
        {
            if (viz != null && viz.isConnected) return true;
            MessageBox.Show(this, "GRAFİK-1 motoruna bağlı değil. Ana pencerede GRAFİK-1'e bağlanın.", "Kelebek");
            return false;
        }

        private bool HizliTik()
        {
            if ((DateTime.Now - sonTik).TotalMilliseconds < TiklamaEngeliMs) return true;
            sonTik = DateTime.Now;
            return false;
        }

        // ------------------------------------------------------------------ komutlar
        /// <summary>Pencerelerin yazilarini ve gorunurluklerini gonderir (animasyonsuz).</summary>
        private void YazilariGonder(KelebekTipi k)
        {
            for (int i = 0; i < k.Pencereler.Count && i < satirlar.Count; i++)
            {
                var p = k.Pencereler[i];
                string isim = satirlar[i].Isim.Text.Trim(), titr = satirlar[i].Titr.Text.Trim();
                viz.SetTextPath(k.Sahne, p.Isim, isim);
                if (p.Gizle != null) viz.SetActivePath(k.Sahne, p.Gizle, isim.Length > 0);
                if (p.Titr == null) continue;
                if (p.TitrGizle) viz.SetActivePath(k.Sahne, p.Titr, titr.Length > 0);
                if (!p.TitrGizle || titr.Length > 0) viz.SetTextPath(k.Sahne, p.Titr, titr);
            }
        }

        private async Task VerAsync()
        {
            var k = Secili;
            if (k == null) { MessageBox.Show(this, "Listeden bir kelebek seçin.", "Kelebek"); return; }
            if (mesgul || HizliTik() || !Bagli()) return;
            mesgul = true;
            try
            {
                if (yayinda != null) Al("değişim");   // baska kelebek ekrandaysa once o alinir
                if (k.Akis == "director")
                {
                    if (k.BasaCek != null) viz.Start(k.Sahne, k.BasaCek);
                    viz.Send(Layer + " SET_OBJECT SCENE*" + k.Sahne);
                    if (k.Klip != null && KelebekTipleri.KlipDosya.Length > 0) viz.SetSoftClipFile(k.Sahne, k.Klip, KelebekTipleri.KlipDosya);
                    foreach (var g in k.Gorunur) viz.SetActivePath(k.Sahne, g, true);
                    if (!k.IsimAnimasyonlu) YazilariGonder(k);   // isim animasyonu yoksa yazilar girisle birlikte gorunur
                    await Task.Delay(GirisBeklemeMs);
                    if (k.Giris != null) viz.Start(k.Sahne, k.Giris);
                }
                else
                {
                    YazilariGonder(k);
                    viz.Send(Layer + " SET_OBJECT SCENE*" + k.Sahne);
                    if (k.Akis == "stage")
                    {
                        viz.Send(Stage + " TO_START");
                        viz.Send(Stage + " START");
                    }
                }
                yayinda = k;
                isimDurum = 0;
                log("KELEBEK VERİLDİ", k.Etiket + "  |  " + string.Join("  |  ", satirlar.Take(k.Pencereler.Count).Select(r => r.Isim.Text)));
            }
            finally
            {
                mesgul = false;
                DurumuYaz();
            }
        }

        /// <summary>AL duruma bakmadan gonderir: kayitta kelebek yoksa secili kelebege gore alir.</summary>
        private void Al(string neden)
        {
            var k = yayinda ?? Secili;
            if (k == null || !Bagli()) return;
            if (k.Akis == "director" && k.BasaCek != null) viz.Start(k.Sahne, k.BasaCek);
            else
            {
                if (k.Akis == "stage") viz.Send(Stage + " TO_START");
                viz.Send(Layer + " SET_OBJECT");
            }
            log("KELEBEK ALINDI", k.Etiket + " (" + neden + ")");
            yayinda = null;
            isimDurum = 0;
            DurumuYaz();
        }

        private void Guncelle()
        {
            var k = yayinda ?? Secili;
            if (k == null || !Bagli()) return;
            YazilariGonder(k);
            log("KELEBEK GÜNCELLENDİ", k.Etiket);
        }

        /// <summary>ISIM VER: 0 -> isim girer; 1 -> isim cikar; 2 -> unvan cikar (isim kalir).</summary>
        private async Task IsimVerAsync()
        {
            var k = yayinda;
            if (k == null || !k.IsimAnimasyonlu || mesgul || HizliTik() || !Bagli()) return;
            mesgul = true;
            try
            {
                if (isimDurum == 1) { viz.Start(k.Sahne, k.IsimOut!); isimDurum = 0; }
                else if (isimDurum == 2 && k.TitrOut != null) { viz.Start(k.Sahne, k.TitrOut); isimDurum = 1; }
                else { YazilariGonder(k); viz.Start(k.Sahne, k.IsimIn!); isimDurum = 1; }
                log("KELEBEK İSİM", k.Etiket + " -> " + isimDurum);
                await Task.CompletedTask;
            }
            finally { mesgul = false; DurumuYaz(); }
        }

        /// <summary>ISIM + UNVAN VER: 2 -> unvan cikar, 700 ms, isim cikar; degilse (gerekirse isim girer, 700 ms) unvan girer.</summary>
        private async Task IsimTitrVerAsync()
        {
            var k = yayinda;
            if (k == null || !k.TitrAnimasyonlu || mesgul || HizliTik() || !Bagli()) return;
            mesgul = true;
            try
            {
                if (isimDurum == 2)
                {
                    viz.Start(k.Sahne, k.TitrOut!);
                    await Task.Delay(IsimTitrBeklemeMs);
                    viz.Start(k.Sahne, k.IsimOut!);
                    isimDurum = 0;
                }
                else
                {
                    bool dolu = satirlar.Take(k.Pencereler.Count).Any(r => r.Isim.Text.Trim().Length > 0 && r.Titr.Text.Trim().Length > 0);
                    if (!dolu) { MessageBox.Show(this, "İsmi ve ünvanı dolu en az bir pencere olmalı.", "Kelebek"); return; }
                    YazilariGonder(k);
                    if (isimDurum == 0)
                    {
                        viz.Start(k.Sahne, k.IsimIn!);
                        await Task.Delay(IsimTitrBeklemeMs);
                    }
                    viz.Start(k.Sahne, k.TitrIn!);
                    isimDurum = 2;
                }
                log("KELEBEK İSİM + ÜNVAN", k.Etiket + " -> " + isimDurum);
            }
            finally { mesgul = false; DurumuYaz(); }
        }

        /// <summary>Ana penceredeki GRAFIK-1 SIFIRLA sonrasi: komut gondermeden durumu temizler.</summary>
        public void DurumuSifirla()
        {
            yayinda = null;
            isimDurum = 0;
            DurumuYaz();
        }

        // ------------------------------------------------------------------ dosyalar
        private void IsimleriOku()
        {
            try
            {
                var yeni = new Dictionary<string, string>(StringComparer.CurrentCultureIgnoreCase);
                if (File.Exists(IsimDosyasi))
                    foreach (var k in JsonSerializer.Deserialize<List<IsimKaydi>>(File.ReadAllText(IsimDosyasi)) ?? new List<IsimKaydi>())
                        if (k.Isim.Trim().Length > 0) yeni[k.Isim.Trim()] = k.Titr;
                if (yeni.Count == isimler.Count && yeni.All(x => isimler.TryGetValue(x.Key, out var t) && t == x.Value)) return;
                isimler = yeni;
                foreach (var r in satirlar)
                {
                    string eski = r.Isim.Text;
                    r.Isim.Items.Clear();
                    foreach (var ad in isimler.Keys) r.Isim.Items.Add(ad);
                    r.Isim.Text = eski;
                }
            }
            catch (Exception ex) { log("KELEBEK", "isimler.json okunamadı: " + ex.Message); }
        }

        private void VerileriOku()
        {
            try
            {
                if (!File.Exists(VeriDosyasi)) return;
                var liste = JsonSerializer.Deserialize<List<Satir>>(File.ReadAllText(VeriDosyasi)) ?? new List<Satir>();
                for (int i = 0; i < liste.Count && i < satirlar.Count; i++) { satirlar[i].Isim.Text = liste[i].Isim; satirlar[i].Titr.Text = liste[i].Titr; }
            }
            catch (Exception ex) { log("KELEBEK", "kelebek_data.json okunamadı: " + ex.Message); }
        }

        private void VerileriYaz()
        {
            try
            {
                var ayar = new JsonSerializerOptions { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping };
                File.WriteAllText(VeriDosyasi, JsonSerializer.Serialize(satirlar.Select(r => new Satir { Isim = r.Isim.Text, Titr = r.Titr.Text }).ToList(), ayar));
            }
            catch (Exception ex) { log("KELEBEK", "kelebek_data.json yazılamadı: " + ex.Message); }
        }
    }
}
