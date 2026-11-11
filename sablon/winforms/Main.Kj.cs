using System.Globalization;

namespace __NS__
{
    /// <summary>
    /// KJ blogu: bolum/KJ listeleri (kj_list.json), duzenleme, VER/AL, acil durum, TUMUNU AL.
    ///
    /// Kumanda iki secimle calisir (ikisi de tek secimli, biri hep secili):
    ///  - BANT     : KjTipleri.Varyantlar (NORMAL + sahnedeki bant turleri)
    ///  - KULAKCIK : YOK + KjTipleri.Kulakciklar (bandin ustune eklenir; metin yazilmaz)
    /// TEKLI / CIFTLI butonu: secili bandin tekli/ciftli halini verir (TEKLI yalnizca ust satir),
    /// kulakcik seciliyse onu da yanina ekler. KJ AL ikisini birlikte alir.
    /// Ayni bant yayindayken yeni metin dogrudan IN; farkli bant: once OUT, bekleme, sonra IN.
    /// Satir secilince bant ve kulakcik satirin degerlerine gore kendiliginden secilir; reji degistirebilir.
    /// Sahneye ait her sey (turler, bantlar, kulakciklar, ozel turler, ogeler) KjTipleri.Sahne.cs'tedir;
    /// bu dosya sahneden bagimsizdir. Butonlar Tag ile baglanir: btn_ozel_*_ver (Tag = tur kodu),
    /// btn_oge_*_ver / btn_oge_*_al (Tag = oge anahtari), cbx_bant_* / cbx_kul_* (Tag = anahtar).
    /// </summary>
    public partial class Main
    {
        // ---- yayin durumu ----
        private KjTipi? yayindakiKj;          // ekrandaki bant (metinli KJ)
        private string aktifKulakcik = "";     // ekrandaki kulakcik anahtari ("" = yok)
        private bool kjMesgul;                 // OUT->IN gecisi surerken yeni tiklamalari yut
        private const int TurGecisBeklemeMs = 700;

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

            _btnGrup.AddGroup(btn_KjAl, new[] { btn_tek_ver, btn_cift_ver }.Concat(OzelButonlari()).ToArray());
            foreach (var ver in OgeVerButonlari())
                if (OgeAlButonu(ver.Tag as string) is Button al) _btnGrup.AddGroup(al, ver);

            foreach (var k in BantSecicileri().Concat(KulakcikSecicileri())) SeciciRenk(k);
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

        /// <summary>Ozel tur butonlarinin ortak olayi (Tag = tur kodu). Tek satir verilir, kulakcik eklenmez.</summary>
        private async void btn_ozel_ver_Click(object? sender, EventArgs e)
        {
            if (sender is Button b) await KjVerAsync(KjTipleri.Bul(b.Tag as string), b, cift: false, kulakcikla: false);
        }

        private IEnumerable<Button> OzelButonlari() =>
            grp_Kumanda.Controls.OfType<Button>().Where(b => b.Name.StartsWith("btn_ozel_"));

        private void btn_KjAl_Click(object? sender, EventArgs e) => KjAl();

        private async Task KjVerAsync(KjTipi? tip, Button buton, bool cift, bool kulakcikla)
        {
            if (VizReji == null || !VizReji.isConnected || kjMesgul) return;
            if (tip == null) { MessageBox.Show("Bu tür sahnede tanımlı değil."); return; }

            // Metin: acil durumda kutulardan, degilse secili satirdan. TEKLI yalnizca ust satiri verir.
            string ust, alt;
            if (cbx_AcilDurum.Checked)
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
            }
            if (!cift) alt = "";

            kjMesgul = true;
            try
            {
                SahneyiHazirla();

                // Ayni alanda baska bant yayindaysa: once OUT, bekle
                if (yayindakiKj != null && yayindakiKj != tip && yayindakiKj.Alan == tip.Alan)
                {
                    VizReji.Start(Sahne, yayindakiKj.Cikis);
                    yayindakiKj = null;
                    await Task.Delay(TurGecisBeklemeMs);
                }

                VizReji.SetTextPath(Sahne, tip.Ust, ust);
                if (tip.Alt != null) VizReji.SetTextPath(Sahne, tip.Alt, alt);
                VizReji.Start(Sahne, tip.Giris);   // ayni bant yayindaysa da dogrudan IN (metin degisimi)
                yayindakiKj = tip;

                // Kulakcik: secili olan ekrandakinden farkliysa eskisini al, yenisini ver
                KulakcigiGuncelle(kulakcikla ? SeciliKulakcikAnahtari() : "");   // ozel tur verilince kulakcik da alinir (bandin parcasi)

                _btnGrup.HandleVerClick(buton);
                btn_KjAl.Enabled = true;
                YayinDurumunuYaz();
                if (!cbx_AcilDurum.Checked) { YayinSatiriniIsaretle(); SonrakiSatiraGec(); }
                Log.Log($"KJ VERİLDİ ({tip.Kod}{(aktifKulakcik.Length > 0 ? " + " + aktifKulakcik : "")})", $"Üst: {ust} | Alt: {alt}");
            }
            finally
            {
                kjMesgul = false;
            }
        }

        private void KulakcigiGuncelle(string hedef)
        {
            if (aktifKulakcik == hedef) return;
            var eski = KjTipleri.KulakcikBul(aktifKulakcik);
            if (eski != null) VizReji.Start(Sahne, eski.Cikis);
            var yeni = KjTipleri.KulakcikBul(hedef);
            if (yeni != null) VizReji.Start(Sahne, yeni.Giris);
            aktifKulakcik = yeni?.Anahtar ?? "";
        }

        private void KjAl()
        {
            if (VizReji == null || !VizReji.isConnected) return;
            if (yayindakiKj != null)
            {
                VizReji.Start(Sahne, yayindakiKj.Cikis);
                Log.Log("KJ ALINDI", yayindakiKj.Kod);
            }
            KulakcigiGuncelle("");
            yayindakiKj = null;
            _btnGrup.HandleAlClick(btn_KjAl);
            btn_KjAl.Enabled = false;
            YayinDurumunuYaz();
            YayinIsaretiniTemizle();
        }

        private void YayinDurumunuYaz()
        {
            if (yayindakiKj == null) { lbl_YayinTuru.Text = "YAYINDA: -"; return; }
            var kul = KjTipleri.KulakcikBul(aktifKulakcik);
            lbl_YayinTuru.Text = "YAYINDA: " + yayindakiKj.Etiket + (kul != null ? "  +  " + kul.Etiket : "");
        }

        // =====================================================================
        //  LOGO / SOSYAL MEDYA / AZ SONRA KAPAK (metinsiz, ayri VER/AL)
        // =====================================================================
        private readonly HashSet<string> yayindakiOgeler = new HashSet<string>();

        private IEnumerable<Button> OgeVerButonlari() =>
            grp_Kumanda.Controls.OfType<Button>().Where(b => b.Name.StartsWith("btn_oge_") && b.Name.EndsWith("_ver"));

        private Button? OgeAlButonu(string? anahtar) =>
            grp_Kumanda.Controls.OfType<Button>().FirstOrDefault(b => b.Name.StartsWith("btn_oge_") && b.Name.EndsWith("_al") && (b.Tag as string) == anahtar);

        /// <summary>Metinsiz oge VER butonlarinin ortak olayi (Tag = oge anahtari).</summary>
        private void btn_oge_ver_Click(object? sender, EventArgs e)
        {
            if (sender is not Button ver || KjTipleri.OgeBul(ver.Tag as string) is not { } oge) return;
            if (VizReji == null || !VizReji.isConnected) return;
            SahneyiHazirla();
            VizReji.Start(Sahne, oge.Giris);
            yayindakiOgeler.Add(oge.Anahtar);
            _btnGrup.HandleVerClick(ver);
            if (OgeAlButonu(oge.Anahtar) is Button al) al.Enabled = true;
            Log.Log(oge.Etiket + " VERİLDİ", "");
        }

        /// <summary>Metinsiz oge AL butonlarinin ortak olayi (Tag = oge anahtari).</summary>
        private void btn_oge_al_Click(object? sender, EventArgs e)
        {
            if (sender is Button al) OgeAl(al.Tag as string);
        }

        private void OgeAl(string? anahtar)
        {
            if (VizReji == null || !VizReji.isConnected || KjTipleri.OgeBul(anahtar) is not { } oge) return;
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
            foreach (var anahtar in yayindakiOgeler.ToList()) OgeAl(anahtar);
            _btnGrup.ResetAllGroups();
            Log.Log("TÜMÜNÜ AL", "");
        }

        /// <summary>SIFIRLA sonrasi: komut gondermeden yayin durumunu temizler.</summary>
        private void YayinDurumunuSifirla()
        {
            yayindakiKj = null;
            aktifKulakcik = "";
            yayindakiOgeler.Clear();
            btn_KjAl.Enabled = false;
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
