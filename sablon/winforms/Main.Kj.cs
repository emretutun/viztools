using System.Globalization;
using System.Text.Json;

namespace __NS__
{
    // viztools-sablon: 7
    /// <summary>
    /// KJ blogu: bolum/KJ listeleri (kj_list.json), duzenleme, VER/AL, acil durum, TUMUNU AL.
    ///
    /// Kumanda iki secimle calisir (ikisi de tek secimli, biri hep secili):
    ///  - BANT     : KjTipleri.Varyantlar (NORMAL + sahnedeki bant turleri)
    ///  - KULAKCIK : YOK + KjTipleri.Kulakciklar (bandin ustune eklenir; metin yazilmaz)
    /// TEKLI / CIFTLI butonu: secili bandin tekli/ciftli halini verir (TEKLI yalnizca ust satir),
    /// kulakcik seciliyse onu da yanina ekler. KJ AL ikisini birlikte alir.
    /// Yayin durumu ALAN bazinda tutulur: bant turleri "altbant" alanini paylasir; ozel turler (ISIM, TELEFON,
    /// LOKASYON...) kendi alanindadir, bant ekrandayken verilir ve kendi AL butonuyla alinir.
    /// Ayni alanda:
    ///  - ayni tur yayindayken yeni metin: grafik alinmaz; turun yuvasi varsa siradaki yuvaya gecilir, yoksa giris yeniden oynar
    ///  - cikisi ortak olan baska tur (tekli/ciftli, KJ_FULL_OUT gibi): dogrudan IN
    ///  - baska tur: once OUT, bekleme, sonra IN
    /// Ozel turun metni Kaynak'a gore gelir: "liste" (KJ listesi), "isim" (ISIMLER listesi), "kutu" (butonun ustundeki kutu).
    /// Ayni metin yeniden verilirse bir sey gonderilmez. CIFTLI'de alt satir bossa tekli verilir.
    /// FON kutusu varsa secilen zemin VER'den once gonderilir. Buton yazisinin sonundaki (F3) gibi tus o butonun kisayoludur.
    /// AL butonlari canli uygulamalardaki gibi duruma bakmadan gonderir: KJ AL ekranda bant gorunmuyorsa secili bandin
    /// cikisini, ozel AL o alandaki turlerin cikislarini oynatir (uygulama yeniden acildiginda ekranda kalan grafik alinabilsin).
    /// TUMUNU AL ayrica ana bandin, isim / telefon turlerinin ve yazili logonun cikisini her zaman gonderir.
    /// Satir bazli bantta (tur.AltTur dolu) ust ve alt satir ayri animasyonla girer: TEKLI ust satiri, CIFTLI ust satirin
    /// ardindan alt satiri verir; CIFTLI'den TEKLI'ye gecerken alt satir alinir.
    /// Satir secilince bant ve kulakcik satirin degerlerine gore kendiliginden secilir; reji degistirebilir.
    /// Sahneye ait her sey (turler, bantlar, kulakciklar, ozel turler, ogeler) KjTipleri.Sahne.cs'tedir;
    /// bu dosya sahneden bagimsizdir. Butonlar Tag ile baglanir: btn_ozel_*_ver (Tag = tur kodu),
    /// btn_oge_*_ver / btn_oge_*_al (Tag = oge anahtari), cbx_bant_* / cbx_kul_* (Tag = anahtar).
    /// </summary>
    public partial class Main
    {
        // ---- yayin durumu ----
        private sealed record AlanDurumu(KjTipi Tip, int Yuva, string Ust, string Alt, int AltYuva = -1);   // AltYuva: satir bazli bantta alt satirin yuvasi (-1 = yok)
        private readonly Dictionary<string, AlanDurumu> yayin = new();   // alan -> ekrandaki tur ve yuvasi
        private KjTipi? yayindakiKj => yayin.TryGetValue(KjTipleri.BantAlani, out var d) ? d.Tip : null;   // ekrandaki bant
        private string aktifKulakcik = "";     // ekrandaki kulakcik anahtari ("" = yok)
        private bool kjMesgul;                 // OUT->IN gecisi surerken yeni tiklamalari yut
        private const int TurGecisBeklemeMs = 700;
        private const int KulakcikGecisBeklemeMs = 400;
        private const int OzelGecisBeklemeMs = 400;    // isim <-> telefon gibi ayni yeri paylasan ozel turler arasi
        private const int OzelDegisBeklemeMs = 600;    // yuvasi olmayan ozel turde yazi degisimi: OUT, bekleme, IN
        private const int SatirBeklemeMs = 1000;       // satir bazli bantta ust satir ile alt satir arasi
        private const int ResimBeklemeMs = 250;        // resim gonderildikten sonra giris oncesi
        private const int BantAlmaBeklemeMs = 300;     // bandi alan oge icin
        private const int TiklamaEngeliMs = 600;       // ayni alana art arda tiklama yutulur
        private readonly Dictionary<string, DateTime> sonVer = new();
        private readonly Dictionary<string, string> resimDosyalari = new(StringComparer.OrdinalIgnoreCase);   // tur kodu -> secilen dosya
        private readonly Dictionary<string, System.Windows.Forms.Timer> otoAl = new();                     // oge anahtari -> sureli alma
        private const string IsimDosyasi = "isimler.json";   // kj_list.json ile ayni klasorde

        private int yayindakiSatir = -1;       // listede kirmiziya boyanan satir

        private static readonly CultureInfo Tr = new CultureInfo("tr-TR");

        // liste sutun adlari
        private const string ColSira = "col_sira", ColTur = "col_tur", ColKul = "col_kulakcik", ColS1 = "col_satir1", ColS2 = "col_satir2";

        private KjBolumu? SeciliBolum =>
            dgv_Bolumler.SelectedRows.Count > 0 ? dgv_Bolumler.SelectedRows[0].Tag as KjBolumu : null;

        private DataGridViewRow? SeciliKjSatiri =>
            dgv_KjListesi.SelectedRows.Count > 0 ? dgv_KjListesi.SelectedRows[0] : null;

        private static string Hucre(DataGridViewRow row, string kolon) => row.Cells[kolon].Value?.ToString() ?? "";

        private string Sahne => SDC.KJ_Scenes;

        private static bool TagEsit(Control c, string? deger) =>
            string.Equals(c.Tag as string, deger, StringComparison.OrdinalIgnoreCase);

        /// <summary>Kumanda panelindeki uretilmis kontrol: ad on eki + Tag.</summary>
        private T? Kontrol<T>(string onEk, string? tag) where T : Control =>
            grp_Kumanda.Controls.OfType<T>().FirstOrDefault(c => c.Name.StartsWith(onEk) && TagEsit(c, tag));

        private DataGridView? IsimListesi => grp_Kumanda.Controls.OfType<DataGridView>().FirstOrDefault(g => g.Name == "dgv_Isimler");
        private ComboBox? FonKutusu => grp_Kumanda.Controls.OfType<ComboBox>().FirstOrDefault(c => c.Name == "cmb_Fon");

        /// <summary>Sahne yalnizca yuklu degilse yuklenir (her VER'de SCENE LOAD, SET edilen metni ezer).</summary>
        private void SahneyiHazirla()
        {
            if (VizReji.CurrentScene_Middle != Sahne)
                VizReji.LoadScene(Sahne);
        }

        // =====================================================================
        //  ARAYUZ HAZIRLIK
        // =====================================================================
        private void KjArayuzunuHazirla()
        {
            cmb_YeniTur.Items.Clear();
            foreach (var t in KjTipleri.ListeTurleri()) cmb_YeniTur.Items.Add(t);
            if (cmb_YeniTur.Items.Count > 0) cmb_YeniTur.SelectedIndex = 0;

            // Bolumler
            dgv_Bolumler.Columns.Clear();
            dgv_Bolumler.Columns.Add("col_sira", "Sıra");
            dgv_Bolumler.Columns[0].Width = 34;
            dgv_Bolumler.Columns.Add("col_baslik", "Bölüm");
            dgv_Bolumler.Columns[1].AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill;
            dgv_Bolumler.DefaultCellStyle.BackColor = Color.AliceBlue;
            dgv_Bolumler.AlternatingRowsDefaultCellStyle.BackColor = Color.LightYellow;

            // KJ listesi: TUR ve KULAKCIK acilir liste; satirlar yerinde duzenlenir, KAYDET ile JSON'a yazilir
            dgv_KjListesi.Columns.Clear();
            dgv_KjListesi.Columns.Add(ColSira, "SIRA");
            dgv_KjListesi.Columns[ColSira].Width = 52;
            dgv_KjListesi.Columns[ColSira].ReadOnly = true;

            var tur = new DataGridViewComboBoxColumn { Name = ColTur, HeaderText = "BANT / TÜR", Width = 200, DisplayStyle = DataGridViewComboBoxDisplayStyle.Nothing, FlatStyle = FlatStyle.Flat };
            foreach (var t in KjTipleri.ListeTurleri()) tur.Items.Add(t.Kod);
            dgv_KjListesi.Columns.Add(tur);

            var kul = new DataGridViewComboBoxColumn { Name = ColKul, HeaderText = "KULAKÇIK", Width = 110, DisplayStyle = DataGridViewComboBoxDisplayStyle.Nothing, FlatStyle = FlatStyle.Flat };
            kul.Items.Add("");
            foreach (var k in KjTipleri.Kulakciklar) kul.Items.Add(k.Anahtar);
            dgv_KjListesi.Columns.Add(kul);

            // Gereksiz sutunlar gizlenir: tek bantta TUR, kulakcik yoksa KULAKCIK (canli uygulamalardaki gibi yalnizca iki satir)
            tur.Visible = !KjTipleri.TekBant;
            kul.Visible = KjTipleri.Kulakciklar.Count > 0;

            dgv_KjListesi.Columns.Add(ColS1, "SATIR 1 / ÜST");
            dgv_KjListesi.Columns.Add(ColS2, "SATIR 2 / ALT");
            dgv_KjListesi.Columns[ColS1].AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill;
            dgv_KjListesi.Columns[ColS2].AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill;
            dgv_KjListesi.DefaultCellStyle.BackColor = Color.AntiqueWhite;
            dgv_KjListesi.AlternatingRowsDefaultCellStyle.BackColor = Color.LightYellow;
            dgv_KjListesi.DefaultCellStyle.WrapMode = DataGridViewTriState.True;
            dgv_KjListesi.AutoSizeRowsMode = DataGridViewAutoSizeRowsMode.AllCells;
            dgv_KjListesi.EditMode = DataGridViewEditMode.EditOnKeystrokeOrF2;
            dgv_KjListesi.DataError += (s, e) => e.ThrowException = false; // bilinmeyen kod gridi kilitlemesin

            // Kendi AL butonu olan ozel tur ayri gruptur (ayni alani paylasanlar tek AL kullanir);
            // AL'i olmayan (eski panel) bant grubuna girer ve KJ AL ile alinir
            _btnGrup.AddGroup(btn_KjAl, new[] { btn_tek_ver, btn_cift_ver }
                .Concat(OzelButonlari().Where(b => OzelAlButonu(b.Tag as string) == null)).ToArray());
            foreach (var g in OzelButonlari().GroupBy(b => OzelAlButonu(b.Tag as string)))
                if (g.Key != null) _btnGrup.AddGroup(g.Key, g.ToArray());
            foreach (var ver in OgeVerButonlari())
                if (OgeAlButonu(ver.Tag as string) is Button al) _btnGrup.AddGroup(al, ver);

            foreach (var k in BantSecicileri().Concat(KulakcikSecicileri())) SeciciRenk(k);

            // AL butonlari hep aciktir (duruma bakmadan gonderir)
            btn_KjAl.Enabled = true;
            foreach (var al in grp_Kumanda.Controls.OfType<Button>().Where(b => b.Name.StartsWith("btn_ozel_") && b.Name.EndsWith("_al"))) al.Enabled = true;

            IsimleriHazirla();
            if (FonKutusu is { } fon)
            {
                fon.Items.Clear();
                foreach (var f in KjTipleri.FonSecenekleri) fon.Items.Add(f);
                int i = fon.Items.IndexOf(KjTipleri.FonVarsayilan);
                if (fon.Items.Count > 0) fon.SelectedIndex = Math.Max(0, i);
            }
            KeyPreview = true;
            KeyDown += Kisayol_KeyDown;

            // KELEBEK: sahneleri KelebekTipleri.Sahne.cs'te; ikinci motorda (GRAFIK-1) calisir
            btn_Kelebek.Enabled = KelebekTipleri.Tumu.Count > 0;
            btn_Kelebek.Click += (s, e) =>
            {
                if (kelebekForm == null || kelebekForm.IsDisposed) kelebekForm = new KelebekForm(VizGrafik, (a, b) => Log.Log(a, b));
                kelebekForm.Show();
                kelebekForm.Activate();
            };
        }

        private KelebekForm? kelebekForm;

        /// <summary>
        /// Kisayol: buton yazisinin sonundaki "(F3)" gibi tus o butona basar. F7 / F8 Main.cs'te islenir.
        /// Tusu degistirmek icin Designer'da buton yazisini degistirmek yeter.
        /// </summary>
        private void Kisayol_KeyDown(object? sender, KeyEventArgs e)
        {
            if (e.Modifiers != Keys.None || e.KeyCode < Keys.F1 || e.KeyCode > Keys.F12 || e.KeyCode is Keys.F7 or Keys.F8) return;
            string ek = "(" + e.KeyCode + ")";
            var b = grp_Kumanda.Controls.OfType<Button>().FirstOrDefault(x => x.Text.TrimEnd().EndsWith(ek, StringComparison.OrdinalIgnoreCase));
            if (b == null) return;
            e.Handled = e.SuppressKeyPress = true;
            Log?.Reji("Kısayol", b.Text);
            if (b.Enabled) b.PerformClick();
        }

        // =====================================================================
        //  ISIMLER LISTESI (isim + unvan; ISIM / TELEFON gibi ozel turlerin metin kaynagi)
        // =====================================================================
        private void IsimleriHazirla()
        {
            if (IsimListesi is not { } g) return;
            g.Columns.Clear();
            g.Columns.Add("col_isim", "İSİM");
            g.Columns.Add("col_titr", "TİTR / ÜNVAN");
            g.Columns[0].AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill;
            g.Columns[1].AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill;
            g.DefaultCellStyle.BackColor = Color.Honeydew;
            g.EditMode = DataGridViewEditMode.EditOnKeystroke;   // F2 kisayol olarak kullanilabilsin
            g.Rows.Clear();
            try
            {
                var liste = File.Exists(IsimDosyasi)
                    ? JsonSerializer.Deserialize<List<IsimKaydi>>(File.ReadAllText(IsimDosyasi)) ?? new List<IsimKaydi>()
                    : KjTipleri.IsimOrnekleri.Select(x => new IsimKaydi { Isim = x.Isim, Titr = x.Titr }).ToList();
                foreach (var k in liste) g.Rows.Add(k.Isim, k.Titr);
            }
            catch (Exception ex)
            {
                Log.Log("İSİMLER", "isimler.json okunamadı: " + ex.Message);
            }
        }

        private void IsimleriKaydet()
        {
            if (IsimListesi is not { } g) return;
            g.EndEdit();
            var liste = new List<IsimKaydi>();
            foreach (DataGridViewRow r in g.Rows)
            {
                if (r.IsNewRow) continue;
                string isim = r.Cells[0].Value?.ToString() ?? "", titr = r.Cells[1].Value?.ToString() ?? "";
                if (isim.Trim().Length + titr.Trim().Length > 0) liste.Add(new IsimKaydi { Isim = isim, Titr = titr });
            }
            try
            {
                var ayar = new JsonSerializerOptions { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping };
                File.WriteAllText(IsimDosyasi, JsonSerializer.Serialize(liste, ayar));
                Log.Log("İSİMLER", $"Kaydedildi ({liste.Count} satır)");
            }
            catch (Exception ex)
            {
                MessageBox.Show("isimler.json yazılamadı: " + ex.Message, "Kayıt hatası", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void btn_IsimKaydet_Click(object? sender, EventArgs e) => IsimleriKaydet();

        private void btn_IsimSil_Click(object? sender, EventArgs e)
        {
            if (IsimListesi is not { } g) return;
            var r = g.SelectedRows.Count > 0 ? g.SelectedRows[0] : g.CurrentRow;
            if (r == null || r.IsNewRow) return;
            g.Rows.Remove(r);
            IsimleriKaydet();
        }

        /// <summary>Fotografli tur icin GOZAT (Tag = tur kodu). Dosya yolu engine'in gorebildigi bir yol olmalidir.</summary>
        private void btn_ozel_gozat_Click(object? sender, EventArgs e)
        {
            if (sender is not Button b || b.Tag is not string kod) return;
            using var d = new OpenFileDialog { Filter = "Resimler|*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tga|Tüm dosyalar|*.*" };
            if (d.ShowDialog(this) != DialogResult.OK) return;
            var lbl = Kontrol<Label>("lbl_ozel_", kod);
            if (d.FileName.Contains(' '))
            {
                resimDosyalari.Remove(kod);
                if (lbl != null) lbl.Text = "DOSYA ADINDA BOŞLUK VAR!";
                return;
            }
            resimDosyalari[kod] = d.FileName;
            if (lbl != null) lbl.Text = Path.GetFileName(d.FileName);
        }

        /// <summary>FON (zemin) ayarlarini secime gore gonderir. Hedef: alan, tur kodu ya da oge anahtari.</summary>
        private void FonUygula(params string?[] hedefler)
        {
            if (FonKutusu is not { } kutu || KjTipleri.FonAyarlari.Count == 0) return;
            foreach (var a in KjTipleri.FonAyarlari)
            {
                if (!hedefler.Any(h => string.Equals(h, a.Hedef, StringComparison.OrdinalIgnoreCase))) continue;
                if (!a.Degerler.TryGetValue(kutu.Text, out var deger) && !a.Degerler.TryGetValue("*", out deger)) continue;
                switch (a.Tip)
                {
                    case "imageclip": VizReji.SetImageClipFile(Sahne, a.Yol, deger); break;
                    case "image": VizReji.SetImageFile(Sahne, a.Yol, deger); break;
                    case "director":
                        if (deger.Equals("REVERSE", StringComparison.OrdinalIgnoreCase)) VizReji.StartReverse(Sahne, a.Yol);
                        else VizReji.Start(Sahne, a.Yol);
                        break;
                }
            }
        }

        // =====================================================================
        //  LISTELER
        // =====================================================================
        private void BolumleriYukle()
        {
            dgv_Bolumler.Rows.Clear();
            int sira = 1;
            foreach (var b in SDC.Kj.Bolumler)
            {
                int r = dgv_Bolumler.Rows.Add(sira++.ToString(), b.Baslik);
                dgv_Bolumler.Rows[r].Tag = b;
            }
            if (dgv_Bolumler.Rows.Count > 0)
            {
                dgv_Bolumler.ClearSelection();
                dgv_Bolumler.Rows[0].Selected = true;
            }
            KjListesiniDoldur();
        }

        private void KjListesiniDoldur()
        {
            dgv_KjListesi.Rows.Clear();
            yayindakiSatir = -1;
            var bolum = SeciliBolum;
            if (bolum == null) return;
            int sira = 1;
            foreach (var kj in bolum.Kjler)
            {
                string tur = KjTipleri.Bul(kj.Tur)?.Kod ?? kj.Tur;
                string kul = KjTipleri.KulakcikBul(kj.Kulakcik)?.Anahtar ?? "";
                int r = dgv_KjListesi.Rows.Add(sira++.ToString(), tur, kul, kj.Satir1, kj.Satir2);
                dgv_KjListesi.Rows[r].Tag = kj;
            }
        }

        private void dgv_Bolumler_SelectionChanged(object? sender, EventArgs e)
        {
            if (SDC == null) return;
            KjListesiniDoldur();
        }

        /// <summary>Satir secilince bant, kulakcik ve basilacak ana buton satirin degerlerine gore ayarlanir.</summary>
        private void dgv_KjListesi_SelectionChanged(object? sender, EventArgs e)
        {
            var row = SeciliKjSatiri;
            var tip = row == null ? null : KjTipleri.Bul(Hucre(row, ColTur));
            lbl_Tur.Text = tip == null ? "-" : $"{tip.Etiket} ({(tip.CiftSatir ? "çift satır" : "tek satır")})";
            if (row == null || tip == null) { AnaButonuIsaretle(null); return; }

            SeciciSec(KulakcikSecicileri(), Hucre(row, ColKul));

            var ayr = KjTipleri.Ayristir(tip.Kod);
            if (ayr == null)   // ozel tur (kendi butonu var)
            {
                AnaButonuIsaretle(OzelButonlari().FirstOrDefault(b => string.Equals(b.Tag as string, tip.Kod, StringComparison.OrdinalIgnoreCase)));
                return;
            }
            SeciciSec(BantSecicileri(), ayr.Value.Anahtar);
            bool cift = ayr.Value.Cift ?? !string.IsNullOrWhiteSpace(Hucre(row, ColS2));
            AnaButonuIsaretle(cift ? btn_cift_ver : btn_tek_ver);
        }

        private void txt_Ara_TextChanged(object? sender, EventArgs e)
        {
            string q = txt_Ara.Text.Trim().ToUpper(Tr);
            foreach (DataGridViewRow row in dgv_Bolumler.Rows)
            {
                string baslik = (row.Cells[1].Value?.ToString() ?? "").ToUpper(Tr);
                row.Visible = q.Length == 0 || baslik.Contains(q) || row.Selected;
            }
        }

        private void btn_AraTemizle_Click(object? sender, EventArgs e) => txt_Ara.Text = "";

        // =====================================================================
        //  DUZENLEME (JSON)
        // =====================================================================
        private void KjListesiniKaydet()
        {
            var bolum = SeciliBolum;
            if (bolum == null) return;
            dgv_KjListesi.EndEdit();
            var yeni = new List<KjKaydi>();
            foreach (DataGridViewRow row in dgv_KjListesi.Rows)
            {
                if (row.IsNewRow) continue;
                var kj = row.Tag as KjKaydi ?? new KjKaydi();
                kj.Tur = Hucre(row, ColTur) is { Length: > 0 } t ? t : (KjTipleri.Tumu.FirstOrDefault()?.Kod ?? "");
                kj.Kulakcik = Hucre(row, ColKul);
                kj.Satir1 = Hucre(row, ColS1);
                kj.Satir2 = Hucre(row, ColS2);
                row.Tag = kj;
                yeni.Add(kj);
            }
            bolum.Kjler = yeni;
            try
            {
                SDC.KjKaydet();
                Log.Log("KJ LİSTESİ", $"Kaydedildi: {bolum.Baslik} ({yeni.Count} satır)");
            }
            catch (Exception ex)
            {
                MessageBox.Show("kj_list.json yazılamadı: " + ex.Message, "Kayıt hatası", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            SiraNolariniGuncelle();
        }

        private void SiraNolariniGuncelle()
        {
            int sira = 1;
            foreach (DataGridViewRow row in dgv_KjListesi.Rows)
                if (!row.IsNewRow) row.Cells[ColSira].Value = (sira++).ToString();
        }

        private void btn_Kaydet_Click(object? sender, EventArgs e) => KjListesiniKaydet();

        private void btn_Sil_Click(object? sender, EventArgs e)
        {
            var row = SeciliKjSatiri;
            if (row == null) return;
            if (MessageBox.Show("Seçili KJ silinecek. Emin misiniz?", "KJ Sil", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes) return;
            if (row.Index == yayindakiSatir) yayindakiSatir = -1;
            dgv_KjListesi.Rows.Remove(row);
            KjListesiniKaydet();
        }

        private void btn_Yukari_Click(object? sender, EventArgs e) => SatirTasi(-1);
        private void btn_Asagi_Click(object? sender, EventArgs e) => SatirTasi(+1);

        private void SatirTasi(int yon)
        {
            var row = SeciliKjSatiri;
            if (row == null) return;
            int i = row.Index, j = i + yon;
            if (j < 0 || j >= dgv_KjListesi.Rows.Count) return;
            YayinIsaretiniTemizle();
            dgv_KjListesi.Rows.RemoveAt(i);
            dgv_KjListesi.Rows.Insert(j, row);
            dgv_KjListesi.ClearSelection();
            dgv_KjListesi.Rows[j].Selected = true;
            KjListesiniKaydet();
        }

        private void btn_YeniEkle_Click(object? sender, EventArgs e)
        {
            if (SeciliBolum == null) { MessageBox.Show("Önce soldan bir bölüm seçin."); return; }
            if (cmb_YeniTur.SelectedItem is not KjTipi tip) return;
            var kj = new KjKaydi { Tur = tip.Kod, Kulakcik = SeciliKulakcikAnahtari(), Satir1 = txt_AcilUst.Text, Satir2 = tip.CiftSatir ? txt_AcilAlt.Text : "" };
            int r = dgv_KjListesi.Rows.Add("", kj.Tur, kj.Kulakcik, kj.Satir1, kj.Satir2);
            dgv_KjListesi.Rows[r].Tag = kj;
            dgv_KjListesi.ClearSelection();
            dgv_KjListesi.Rows[r].Selected = true;
            KjListesiniKaydet();
        }

        // =====================================================================
        //  BANT / KULAKCIK SECICILERI (tek secimli, biri hep secili)
        // =====================================================================
        private bool seciciKilit;

        private IEnumerable<CheckBox> BantSecicileri() =>
            grp_Kumanda.Controls.OfType<CheckBox>().Where(c => c.Name.StartsWith("cbx_bant_"));

        private IEnumerable<CheckBox> KulakcikSecicileri() =>
            grp_Kumanda.Controls.OfType<CheckBox>().Where(c => c.Name.StartsWith("cbx_kul_"));

        private void Secici_CheckedChanged(object? sender, EventArgs e)
        {
            if (seciciKilit || sender is not CheckBox kutu) return;
            var grup = kutu.Name.StartsWith("cbx_bant_") ? BantSecicileri() : KulakcikSecicileri();
            seciciKilit = true;
            if (kutu.Checked)
            {
                foreach (var k in grup) if (k != kutu) k.Checked = false;
            }
            else if (!grup.Any(k => k.Checked))
            {
                kutu.Checked = true;   // biri hep secili kalir: secili olana tekrar basmak kaldirmaz
            }
            seciciKilit = false;
            foreach (var k in grup) SeciciRenk(k);
        }

        private static void SeciciRenk(CheckBox k)
        {
            bool bant = k.Name.StartsWith("cbx_bant_");
            k.BackColor = k.Checked ? (bant ? Color.Gold : Color.DeepSkyBlue) : Color.WhiteSmoke;
            k.ForeColor = k.Checked && !bant ? Color.White : Color.Black;
        }

        private void SeciciSec(IEnumerable<CheckBox> grup, string anahtar)
        {
            var liste = grup.ToList();
            if (liste.Count == 0) return;
            var hedef = liste.FirstOrDefault(k => (k.Tag as string ?? "") == anahtar)
                        ?? liste.FirstOrDefault(k => (k.Tag as string ?? "") == "") ?? liste[0];
            seciciKilit = true;
            foreach (var k in liste) k.Checked = k == hedef;
            seciciKilit = false;
            foreach (var k in liste) SeciciRenk(k);
        }

        private string SeciliBantAnahtari() => BantSecicileri().FirstOrDefault(k => k.Checked)?.Tag as string ?? "";
        private string SeciliKulakcikAnahtari() => KulakcikSecicileri().FirstOrDefault(k => k.Checked)?.Tag as string ?? "";

        // =====================================================================
        //  VER / AL
        // =====================================================================
        private async void btn_tek_ver_Click(object? sender, EventArgs e) =>
            await KjVerAsync(KjTipleri.Coz(SeciliBantAnahtari(), cift: false), btn_tek_ver, cift: false, kulakcikla: true);

        private async void btn_cift_ver_Click(object? sender, EventArgs e) =>
            await KjVerAsync(KjTipleri.Coz(SeciliBantAnahtari(), cift: true), btn_cift_ver, cift: true, kulakcikla: true);

        /// <summary>Ozel tur butonlarinin ortak olayi (Tag = tur kodu). Turun iki metin alani varsa iki satir da verilir; kulakcik eklenmez.</summary>
        private async void btn_ozel_ver_Click(object? sender, EventArgs e)
        {
            if (sender is not Button b) return;
            var tip = KjTipleri.Bul(b.Tag as string);
            await KjVerAsync(tip, b, cift: tip?.CiftSatir ?? false, kulakcikla: false);
        }

        private IEnumerable<Button> OzelButonlari() =>
            grp_Kumanda.Controls.OfType<Button>().Where(b => b.Name.StartsWith("btn_ozel_") && b.Name.EndsWith("_ver"));

        /// <summary>Ozel turun AL butonu: Tag = turun alani (ayni alani paylasanlar tek AL kullanir) ya da tur kodu.</summary>
        private Button? OzelAlButonu(string? kod)
        {
            var tip = KjTipleri.Bul(kod);
            return grp_Kumanda.Controls.OfType<Button>().FirstOrDefault(b => b.Name.StartsWith("btn_ozel_") && b.Name.EndsWith("_al")
                && (TagEsit(b, kod) || (tip != null && TagEsit(b, tip.Alan))));
        }

        /// <summary>Ozel tur AL butonlarinin ortak olayi (Tag = alan ya da tur kodu): o alanda ekranda ne varsa alir.</summary>
        private void btn_ozel_al_Click(object? sender, EventArgs e)
        {
            if (sender is not Button al || al.Tag is not string hedef) return;
            if (VizReji == null || !VizReji.isConnected) return;
            string alan = KjTipleri.Tumu.Any(t => string.Equals(t.Alan, hedef, StringComparison.OrdinalIgnoreCase))
                ? hedef : KjTipleri.Bul(hedef)?.Alan ?? hedef;
            var anahtar = yayin.Keys.FirstOrDefault(k => string.Equals(k, alan, StringComparison.OrdinalIgnoreCase));
            if (anahtar != null)
            {
                Log.Log(yayin[anahtar].Tip.Etiket + " ALINDI", "");
                AlanAl(anahtar, komut: true);
            }
            else   // uygulamanin kaydinda yok: yine de o alandaki turlerin cikislarini gonder
            {
                CikislariGonder(KjTipleri.Tumu.Where(t => string.Equals(t.Alan, alan, StringComparison.OrdinalIgnoreCase)));
                Log.Log(alan.ToUpper(Tr) + " AL (zorla)", "");
            }
            YayinDurumunuYaz();
        }

        private void btn_KjAl_Click(object? sender, EventArgs e) => KjAl();

        /// <summary>Turun AL butonu: ozel turun kendi AL'i, yoksa KJ AL.</summary>
        private Button AlButonu(KjTipi tip) => OzelAlButonu(tip.Kod) ?? btn_KjAl;

        /// <summary>Verilen turlerin cikislarini (yuva cikislari dahil, her biri bir kez) gonderir.</summary>
        private void CikislariGonder(IEnumerable<KjTipi> turler)
        {
            foreach (var cikis in turler.SelectMany(t => t.Cikislar).Distinct().ToList()) VizReji.Start(Sahne, cikis);
        }

        /// <summary>Alandaki grafigi kayittan duser, istenirse cikisini oynatir ve butonlarini eski haline getirir.</summary>
        private void AlanAl(string alan, bool komut)
        {
            if (!yayin.Remove(alan, out var d)) return;
            if (komut) foreach (var cikis in d.Tip.Cikislar) VizReji.Start(Sahne, cikis);
            var al = AlButonu(d.Tip);
            if (yayin.Values.All(x => AlButonu(x.Tip) != al))   // ayni AL'i kullanan baska grafik kalmadiysa
            {
                _btnGrup.HandleAlClick(al);
                al.Enabled = true;   // AL hep acik kalir
            }
        }

        private async Task KjVerAsync(KjTipi? tip, Button buton, bool cift, bool kulakcikla)
        {
            if (VizReji == null || !VizReji.isConnected || kjMesgul) return;
            if (tip == null) { MessageBox.Show("Bu tür sahnede tanımlı değil."); return; }

            bool bant = tip.Alan == KjTipleri.BantAlani;
            string kaynak = bant ? "liste" : tip.Kaynak;
            bool listeden = false;

            // Metin: ozel turde kaynagina gore (ISIMLER listesi / kendi kutusu); bantta acil durumda kutulardan,
            // degilse secili KJ satirindan. TEKLI yalnizca ust satiri verir.
            string ust, alt;
            if (kaynak == "isim" && IsimListesi is { } isimler)
            {
                isimler.EndEdit();
                var r = isimler.SelectedRows.Count > 0 ? isimler.SelectedRows[0] : isimler.CurrentRow;
                if (r == null || r.IsNewRow) { MessageBox.Show("İSİMLER listesinden bir satır seçin."); return; }
                ust = r.Cells[0].Value?.ToString() ?? "";
                alt = r.Cells[1].Value?.ToString() ?? "";
            }
            else if (kaynak == "kutu" && Kontrol<TextBox>("txt_ozel_", tip.Kod) is { } kutu)
            {
                ust = kutu.Text;
                alt = "";
                if (ust.Trim().Length == 0) { MessageBox.Show(tip.Etiket + " yazısını yazın."); return; }
            }
            else if (cbx_AcilDurum.Checked)
            {
                ust = txt_AcilUst.Text;
                alt = txt_AcilAlt.Text;
            }
            else
            {
                var row = SeciliKjSatiri;
                if (row == null) return;
                dgv_KjListesi.EndEdit();
                ust = Hucre(row, ColS1);
                alt = Hucre(row, ColS2);
                listeden = true;
            }
            if (!cift) alt = "";

            // CIFTLI'de alt satir bossa tekli verilir (canli uygulamalardaki gibi)
            if (bant && cift && string.IsNullOrWhiteSpace(alt) && KjTipleri.Coz(SeciliBantAnahtari(), cift: false) is { } tek)
            {
                tip = tek;
                buton = btn_tek_ver;
                cift = false;
            }

            // Fotografli tur: dosya adinda bosluk olmamali (engine komutu bosluktan boler)
            string? resim = null;
            if (tip.Resim != null)
            {
                resimDosyalari.TryGetValue(tip.Kod, out resim);
                if (string.IsNullOrWhiteSpace(resim)) resim = tip.ResimVarsayilan;
            }

            // Ayni alana art arda tiklama yutulur
            if (sonVer.TryGetValue(tip.Alan, out var son) && (DateTime.Now - son).TotalMilliseconds < TiklamaEngeliMs) return;
            sonVer[tip.Alan] = DateTime.Now;

            kjMesgul = true;
            try
            {
                yayin.TryGetValue(tip.Alan, out var onceki);

                // Ayni tur ayni metinle zaten ekranda: bir sey gonderme
                if (onceki != null && onceki.Tip == tip && onceki.Ust == ust && onceki.Alt == alt)
                {
                    if (listeden) SonrakiSatiraGec();
                    return;
                }

                SahneyiHazirla();

                // Ayni alanda baska tur yayinda. Cikislari ortaksa (tekli <-> ciftli) dogrudan IN; degilse once OUT, bekle.
                if (onceki != null && onceki.Tip != tip)
                {
                    bool ortakCikis = onceki.Tip.Cikis == tip.Cikis;
                    AlanAl(tip.Alan, komut: !ortakCikis);
                    if (!ortakCikis) await Task.Delay(bant ? TurGecisBeklemeMs : OzelGecisBeklemeMs);
                    onceki = null;
                }
                // Yuvasi olmayan ozel tur yayindayken yeni yazi (canli uygulamalardaki gibi): OUT, bekleme, sonra IN
                else if (onceki != null && !bant && tip.Yuvalar.Count == 0)
                {
                    foreach (var c in tip.Cikislar) VizReji.Start(Sahne, c);
                    await Task.Delay(OzelDegisBeklemeMs);
                }

                if (tip.AltTur != null && KjTipleri.Bul(tip.AltTur) is { } altTip)
                {
                    FonUygula(tip.Alan, tip.Kod);
                    yayin[tip.Alan] = SatirliVer(tip, altTip, onceki, ust, alt, cift, out int bekle1, out Action? sonra);
                    if (sonra != null)
                    {
                        await Task.Delay(bekle1);
                        sonra();
                    }
                }
                else
                {

                // Ayni tur yayindayken yeni metin: yuvasi varsa siradaki yuvaya gec (grafik alinmaz)
                int yuva = onceki != null && tip.Yuvalar.Count > 0 ? (onceki.Yuva + 1) % (tip.Yuvalar.Count + 1) : 0;
                var (giris, ustYol, altYol, ayirac) = tip.Yuva(yuva);

                FonUygula(tip.Alan, tip.Kod);
                VizReji.SetTextPath(Sahne, ustYol, ust);
                if (altYol != null) VizReji.SetTextPath(Sahne, altYol, alt);
                if (ayirac != null) VizReji.SetActivePath(Sahne, ayirac, !string.IsNullOrWhiteSpace(alt));
                if (tip.Resim != null && !string.IsNullOrWhiteSpace(resim))
                {
                    VizReji.SetImageFile(Sahne, tip.Resim, resim);
                    await Task.Delay(ResimBeklemeMs);
                }
                VizReji.Start(Sahne, giris);
                yayin[tip.Alan] = new AlanDurumu(tip, yuva, ust, alt);
                }

                // Kulakcik bandin parcasidir: yalnizca bant verilirken guncellenir; ozel tur kulakciga dokunmaz
                if (bant) await KulakcigiGuncelleAsync(kulakcikla ? SeciliKulakcikAnahtari() : "");

                _btnGrup.HandleVerClick(buton);
                AlButonu(tip).Enabled = true;
                YayinDurumunuYaz();
                if (listeden) { YayinSatiriniIsaretle(); SonrakiSatiraGec(); }

                // "KJ ile" kutusu isaretli ogeler (yazili logo gibi) bantla birlikte verilir
                if (bant)
                    foreach (var c in grp_Kumanda.Controls.OfType<CheckBox>().Where(c => c.Name.StartsWith("cbx_ogekj_") && c.Checked).ToList())
                        if (KjTipleri.OgeBul(c.Tag as string) is { } o && !yayindakiOgeler.Contains(o.Anahtar)) await OgeVerAsync(o);
                Log.Log($"KJ VERİLDİ ({tip.Kod}{(aktifKulakcik.Length > 0 ? " + " + aktifKulakcik : "")})", $"Üst: {ust} | Alt: {alt}");
            }
            finally
            {
                kjMesgul = false;
            }
        }

        /// <summary>
        /// Satir bazli bant (canli NTR HT akisi). Hemen gonderilecek komutlari gonderir; beklemeden sonra gonderilecekler
        /// "sonra" ile doner (cagiran bekle ms bekleyip calistirir). Donus: yeni yayin durumu.
        ///   ilk giris      : ust yaz, ust IN, alt cikis, alt yuvalari bosalt; ciftliyse bekle, alt yaz, alt IN
        ///   tekli -> tekli : yazi degistiyse ust satir siradaki yuvaya gecer
        ///   tekli -> ciftli: ust (degistiyse) doner; alt yaz, alt IN
        ///   ciftli -> ciftli: degisen satir(lar) kendi yuvasinda doner
        ///   ciftli -> tekli: alt cikis, bekle, ust (degistiyse) doner
        /// </summary>
        private AlanDurumu SatirliVer(KjTipi tip, KjTipi altTip, AlanDurumu? onceki, string ust, string alt, bool cift,
                                      out int bekle, out Action? sonra)
        {
            bekle = 0;
            sonra = null;
            void UstYaz(int y) { var (g, yol, _, _) = tip.Yuva(y); VizReji.SetTextPath(Sahne, yol, ust); VizReji.Start(Sahne, g); }
            void AltYaz(int y) { var (g, yol, _, _) = altTip.Yuva(y); VizReji.SetTextPath(Sahne, yol, alt); VizReji.Start(Sahne, g); }
            int Sonraki(KjTipi t, int y) => t.Yuvalar.Count > 0 ? (y + 1) % (t.Yuvalar.Count + 1) : 0;

            if (onceki == null)   // ilk giris
            {
                UstYaz(0);
                if (tip.AltCikis != null) VizReji.Start(Sahne, tip.AltCikis);
                for (int i = 0; i <= altTip.Yuvalar.Count; i++) VizReji.SetTextPath(Sahne, altTip.Yuva(i).Ust, "");
                if (cift)
                {
                    bekle = SatirBeklemeMs;
                    sonra = () => AltYaz(0);
                }
                return new AlanDurumu(tip, 0, ust, alt, cift ? 0 : -1);
            }

            bool altVar = onceki.AltYuva >= 0;
            int ustYuva = onceki.Ust == ust ? onceki.Yuva : Sonraki(tip, onceki.Yuva);
            int altYuva = -1;
            if (!cift && altVar)   // ciftliden tekliye: once alt satir cikar
            {
                if (tip.AltCikis != null) VizReji.Start(Sahne, tip.AltCikis);
                if (onceki.Ust != ust)
                {
                    bekle = SatirBeklemeMs;
                    sonra = () => UstYaz(ustYuva);
                }
                return new AlanDurumu(tip, ustYuva, ust, "", -1);
            }
            if (onceki.Ust != ust) UstYaz(ustYuva);
            if (cift)
            {
                altYuva = !altVar ? 0 : onceki.Alt == alt ? onceki.AltYuva : Sonraki(altTip, onceki.AltYuva);
                if (!altVar || onceki.Alt != alt) AltYaz(altYuva);
            }
            return new AlanDurumu(tip, ustYuva, ust, cift ? alt : "", altYuva);
        }

        /// <summary>Kulakcik degisimi: eskisi cikar, kisa bekleme, yenisi girer (ikisi ayni yerde durur).</summary>
        private async Task KulakcigiGuncelleAsync(string hedef)
        {
            if (aktifKulakcik == hedef) return;
            var eski = KjTipleri.KulakcikBul(aktifKulakcik);
            var yeni = KjTipleri.KulakcikBul(hedef);
            aktifKulakcik = yeni?.Anahtar ?? "";
            if (eski != null) VizReji.Start(Sahne, eski.Cikis);
            if (eski != null && yeni != null) await Task.Delay(KulakcikGecisBeklemeMs);
            if (yeni != null) VizReji.Start(Sahne, yeni.Giris);
        }

        private void KulakcigiAl()
        {
            if (KjTipleri.KulakcikBul(aktifKulakcik) is { } eski) VizReji.Start(Sahne, eski.Cikis);
            aktifKulakcik = "";
        }

        /// <summary>KJ AL (F7): bandi ve kulakcigi alir. Kendi AL butonu olmayan ozel turler (eski panel) de bununla alinir.</summary>
        private void KjAl()
        {
            if (VizReji == null || !VizReji.isConnected) return;
            var alanlar = yayin.Where(x => AlButonu(x.Value.Tip) == btn_KjAl).Select(x => x.Key).ToList();
            foreach (var alan in alanlar)
            {
                Log.Log("KJ ALINDI", yayin[alan].Tip.Kod);
                AlanAl(alan, komut: true);
            }
            if (!alanlar.Contains(KjTipleri.BantAlani) && KjTipleri.Coz(SeciliBantAnahtari(), cift: false) is { } secili)
            {
                // Kayitta bant yok (uygulama yeniden acilmis olabilir): secili bandin cikisini yine de gonder
                SahneyiHazirla();
                CikislariGonder(new[] { secili });
                Log.Log("KJ AL (zorla)", secili.Kod);
            }
            KulakcigiAl();
            _btnGrup.HandleAlClick(btn_KjAl);
            btn_KjAl.Enabled = true;
            YayinDurumunuYaz();
            YayinIsaretiniTemizle();
        }

        private void YayinDurumunuYaz()
        {
            if (yayin.Count == 0) { lbl_YayinTuru.Text = "YAYINDA: -"; return; }
            var kul = KjTipleri.KulakcikBul(aktifKulakcik);
            var adlar = yayin.OrderBy(x => x.Key != KjTipleri.BantAlani).Select(x => x.Value.Tip.Etiket);
            lbl_YayinTuru.Text = "YAYINDA: " + string.Join("  |  ", adlar) + (kul != null ? "  +  " + kul.Etiket : "");
        }

        // =====================================================================
        //  LOGO / SOSYAL MEDYA / AZ SONRA KAPAK (metinsiz, ayri VER/AL)
        // =====================================================================
        private readonly HashSet<string> yayindakiOgeler = new HashSet<string>();

        private IEnumerable<Button> OgeVerButonlari() =>
            grp_Kumanda.Controls.OfType<Button>().Where(b => b.Name.StartsWith("btn_oge_") && b.Name.EndsWith("_ver"));

        private Button? OgeAlButonu(string? anahtar) =>
            grp_Kumanda.Controls.OfType<Button>().FirstOrDefault(b => b.Name.StartsWith("btn_oge_") && b.Name.EndsWith("_al") && (b.Tag as string) == anahtar);

        /// <summary>Oge VER butonlarinin ortak olayi (Tag = oge anahtari).</summary>
        private async void btn_oge_ver_Click(object? sender, EventArgs e)
        {
            if (sender is Button ver && KjTipleri.OgeBul(ver.Tag as string) is { } oge) await OgeVerAsync(oge);
        }

        private async Task OgeVerAsync(KjTipleri.Oge oge)
        {
            if (VizReji == null || !VizReji.isConnected) return;
            SahneyiHazirla();
            if (oge.BandiAl && yayin.ContainsKey(KjTipleri.BantAlani))
            {
                KjAl();
                await Task.Delay(BantAlmaBeklemeMs);
            }
            FonUygula(oge.Anahtar);
            // Yazi: cok satirli kutudan (satirlar oldugu gibi) ya da hazir secenek listesinden
            string metin = Kontrol<TextBox>("txt_oge_", oge.Anahtar) is { } yazi
                ? string.Join("\n", yazi.Lines.Select(x => x.Trim()).Where(x => x.Length > 0))
                : Kontrol<ComboBox>("cmb_oge_", oge.Anahtar)?.Text.Replace("\\n", "\n") ?? "";
            if (oge.Metin != null && metin.Trim().Length > 0)
                VizReji.SetTextPath(Sahne, oge.Metin, metin);
            foreach (var g in oge.Gorunur) VizReji.SetActivePath(Sahne, g, true);
            VizReji.Start(Sahne, oge.Giris);
            yayindakiOgeler.Add(oge.Anahtar);
            if (OgeVerButonlari().FirstOrDefault(b => TagEsit(b, oge.Anahtar)) is Button ver) _btnGrup.HandleVerClick(ver);
            if (OgeAlButonu(oge.Anahtar) is Button al) al.Enabled = true;
            if (oge.OtoAlSn > 0 && (Kontrol<CheckBox>("cbx_ogeoto_", oge.Anahtar)?.Checked ?? true)) OtoAlKur(oge);
            Log.Log(oge.Etiket + " VERİLDİ", metin.Replace("\n", " / "));
        }

        /// <summary>Sureli alma: VER'den OtoAlSn saniye sonra oge kendiliginden alinir.</summary>
        private void OtoAlKur(KjTipleri.Oge oge)
        {
            OtoAlDurdur(oge.Anahtar);
            var t = new System.Windows.Forms.Timer { Interval = oge.OtoAlSn * 1000 };
            t.Tick += (s, e) => OgeAl(oge.Anahtar);
            otoAl[oge.Anahtar] = t;
            t.Start();
        }

        private void OtoAlDurdur(string anahtar)
        {
            if (!otoAl.Remove(anahtar, out var t)) return;
            t.Stop();
            t.Dispose();
        }

        /// <summary>Metinsiz oge AL butonlarinin ortak olayi (Tag = oge anahtari).</summary>
        private void btn_oge_al_Click(object? sender, EventArgs e)
        {
            if (sender is Button al) OgeAl(al.Tag as string);
        }

        private void OgeAl(string? anahtar)
        {
            if (KjTipleri.OgeBul(anahtar) is not { } oge) return;
            OtoAlDurdur(oge.Anahtar);
            if (VizReji == null || !VizReji.isConnected) return;
            if (yayindakiOgeler.Remove(oge.Anahtar)) VizReji.Start(Sahne, oge.Cikis);
            if (OgeAlButonu(oge.Anahtar) is Button al)
            {
                _btnGrup.HandleAlClick(al);
                al.Enabled = false;
            }
            Log.Log(oge.Etiket + " ALINDI", "");
        }

        private void btn_TumunuAl_Click(object? sender, EventArgs e)
        {
            if (VizReji == null || !VizReji.isConnected) return;
            KjAl();
            foreach (var alan in yayin.Keys.ToList()) AlanAl(alan, komut: true);   // ozel turler
            foreach (var anahtar in yayindakiOgeler.ToList()) OgeAl(anahtar);
            // Canli uygulamalardaki gibi duruma bakmadan: ana bant, isim / telefon turleri ve yazili logo her zaman alinir
            CikislariGonder(KjTipleri.Tumu.Where(t => t.Kaynak == "isim" || t == KjTipleri.Coz("", cift: false)));
            foreach (var o in KjTipleri.Ogeler.Where(o => o.Metin != null)) VizReji.Start(Sahne, o.Cikis);
            YayinDurumunuYaz();
            _btnGrup.ResetAllGroups();
            Log.Log("TÜMÜNÜ AL", "");
        }

        /// <summary>SIFIRLA sonrasi: komut gondermeden yayin durumunu temizler.</summary>
        private void YayinDurumunuSifirla()
        {
            yayin.Clear();
            aktifKulakcik = "";
            yayindakiOgeler.Clear();
            foreach (var a in otoAl.Keys.ToList()) OtoAlDurdur(a);
            sonVer.Clear();
            btn_KjAl.Enabled = true;
            foreach (var ver in OzelButonlari()) if (OzelAlButonu(ver.Tag as string) is Button ozelAl) ozelAl.Enabled = true;
            foreach (var ver in OgeVerButonlari()) if (OgeAlButonu(ver.Tag as string) is Button al) al.Enabled = false;
            YayinDurumunuYaz();
            _btnGrup.ResetAllGroups();
            YayinIsaretiniTemizle();
        }

        /// <summary>Secili satir icin basilacak ana butonu kalin mavi cerceveyle gosterir.</summary>
        private void AnaButonuIsaretle(Button? hedef)
        {
            foreach (var b in new[] { btn_tek_ver, btn_cift_ver }.Concat(OzelButonlari()))
            {
                b.FlatAppearance.BorderSize = b == hedef ? 4 : 1;
                b.FlatAppearance.BorderColor = b == hedef ? Color.Blue : Color.Black;
            }
        }

        private void cbx_AcilDurum_CheckedChanged(object? sender, EventArgs e)
        {
            // Yalnizca metin kaynagini degistirir; sahneye komut gondermez.
            cbx_AcilDurum.BackColor = cbx_AcilDurum.Checked ? Color.Red : SystemColors.Control;
            cbx_AcilDurum.ForeColor = cbx_AcilDurum.Checked ? Color.White : Color.Red;
        }

        // =====================================================================
        //  LISTEDE YAYIN ISARETI
        // =====================================================================
        private void YayinSatiriniIsaretle()
        {
            YayinIsaretiniTemizle();
            var row = SeciliKjSatiri;
            if (row == null) return;
            yayindakiSatir = row.Index;
            row.DefaultCellStyle.BackColor = Color.Red;
            row.DefaultCellStyle.ForeColor = Color.White;
            row.DefaultCellStyle.SelectionBackColor = Color.DarkRed;
        }

        private void YayinIsaretiniTemizle()
        {
            if (yayindakiSatir >= 0 && yayindakiSatir < dgv_KjListesi.Rows.Count)
            {
                var st = dgv_KjListesi.Rows[yayindakiSatir].DefaultCellStyle;
                st.BackColor = Color.Empty;
                st.ForeColor = Color.Empty;
                st.SelectionBackColor = Color.Empty;
            }
            yayindakiSatir = -1;
        }

        private void SonrakiSatiraGec()
        {
            var row = SeciliKjSatiri;
            if (row == null || row.Index >= dgv_KjListesi.Rows.Count - 1) return;
            int j = row.Index + 1;
            dgv_KjListesi.ClearSelection();
            dgv_KjListesi.Rows[j].Selected = true;
            dgv_KjListesi.CurrentCell = dgv_KjListesi.Rows[j].Cells[ColS1];
        }
    }
}
