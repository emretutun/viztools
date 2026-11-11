namespace __NS__
{
    /// <summary>
    /// Ana form: motor baglantilari, saat, aktif pencere cercevesi, admin/teshis paneli, klavye kisayollari.
    /// KJ listesi ve VER/AL mantigi Main.Kj.cs'te.
    /// </summary>
    public partial class Main : Form
    {
        // CClientSession / Vizrt (NTR Show'dan kopya) bu uyelere eristigi icin internal
        internal CSceneDataController SDC = null!;
        internal CLog Log = null!;
        internal List<string> denyList = new List<string>();
        internal bool diagnosticPasuse = false;

        internal Vizrt VizReji = null!;     // KJ motoru (viz1)
        internal Vizrt VizGrafik = null!;   // GRAFIK-1 motoru (viz2, kelebek)

        private ButtonGroupManager _btnGrup = null!;
        private bool aktif = false;
        private long tik = 0;

        public Main()
        {
            InitializeComponent();
            Text = "__BASLIK__ - V" + AppVersions.Surum;
        }

        // =====================================================================
        //  ACILIS / KAPANIS
        // =====================================================================
        private void Main_Load(object? sender, EventArgs e)
        {
            Log = new CLog(this);
            try
            {
                SDC = new CSceneDataController();
            }
            catch (Exception ex)
            {
                MessageBox.Show("Veri dosyaları okunamadı:\n" + ex.Message, "__BASLIK__", MessageBoxButtons.OK, MessageBoxIcon.Error);
                SDC = new CSceneDataController();
            }
            Log.Log("Main", "Uygulama başlatıldı");

            _btnGrup = new ButtonGroupManager(Color.Red, Color.LimeGreen, Color.White, Color.Black);

            IpListeleriniOku();

            VizReji = new Vizrt(1, "viz-KJ", this);
            VizGrafik = new Vizrt(2, "viz-Grafik 1", this);
            VizReji.OnConnected += OnRejiBaglandi;
            VizReji.OnDisconnected += OnRejiKoptu;
            VizGrafik.OnConnected += OnGrafikBaglandi;
            VizGrafik.OnDisconnected += OnGrafikKoptu;
            VizReji.heartbeat = cbx_RejiHb.Checked;
            VizGrafik.heartbeat = cbx_GrafikHb.Checked;

            if (File.Exists(@"C:\ego") || Environment.GetCommandLineArgs().Any(a => a.Equals("/teshis", StringComparison.OrdinalIgnoreCase)))
                AdminModu(true);

            KjArayuzunuHazirla();
            BolumleriYukle();
            OtomatikLogla(this);

            tmr_Tik.Interval = 100;
            tmr_Tik.Start();
        }

        private void Main_FormClosing(object? sender, FormClosingEventArgs e)
        {
            tmr_Tik.Stop();
            Log?.Log("Main", "Uygulama kapatıldı");
        }

        // =====================================================================
        //  ZAMANLAYICI (100 ms)
        // =====================================================================
        private void tmr_Tik_Tick(object? sender, EventArgs e)
        {
            tik++;
            if (tik % 10 == 0) Saniyelik();
        }

        private void Saniyelik()
        {
            lbl_Saat.Text = DateTime.Now.ToString("dd-MM-yyyy HH:mm:ss");

            if (btn_RejiBaglan.BackColor == Color.Maroon && cbx_RejiAc.Checked && !string.IsNullOrWhiteSpace(cmb_RejiIp.Text))
                VizReji.AutoConnectControl(cmb_RejiIp.Text);
            if (btn_GrafikBaglan.BackColor == Color.Maroon && cbx_GrafikAc.Checked && !string.IsNullOrWhiteSpace(cmb_GrafikIp.Text))
                VizGrafik.AutoConnectControl(cmb_GrafikIp.Text);

            // Reji kopuksa liste basliklari yanip soner (NTR Show davranisi)
            Color renk = (!VizReji.isConnected && lbl_KjBaslik.BackColor == Color.SeaGreen) ? Color.Red : Color.SeaGreen;
            lbl_KjBaslik.BackColor = renk;
            lbl_BolumBaslik.BackColor = renk;
        }

        // =====================================================================
        //  AKTIF PENCERE CERCEVESI
        // =====================================================================
        private void Main_Activated(object? sender, EventArgs e) { aktif = true; CerceveyiBoya(); }
        private void Main_Deactivate(object? sender, EventArgs e) { aktif = false; CerceveyiBoya(); }

        private void CerceveyiBoya()
        {
            Color c = aktif ? Color.Red : Color.Gray;
            pnl_Cerceve1.BackColor = pnl_Cerceve2.BackColor = pnl_Cerceve3.BackColor = pnl_Cerceve4.BackColor = c;
        }

        // =====================================================================
        //  IP LISTELERI
        // =====================================================================
        private void IpListeleriniOku()
        {
            denyList.Clear();
            if (File.Exists("DenyIPlist.txt"))
                denyList.AddRange(File.ReadAllLines("DenyIPlist.txt").Select(s => s.Trim()).Where(s => s.Length > 0));

            cmb_RejiIp.Items.Clear();
            cmb_GrafikIp.Items.Clear();
            if (File.Exists("IpList.txt"))
            {
                ComboBox? hedef = null;
                foreach (var ham in File.ReadAllLines("IpList.txt"))
                {
                    string s = ham.Trim();
                    if (s.Length == 0) continue;
                    if (s.Equals("REJI", StringComparison.OrdinalIgnoreCase)) { hedef = cmb_RejiIp; continue; }
                    if (s.Equals("GRAFIK-1", StringComparison.OrdinalIgnoreCase)) { hedef = cmb_GrafikIp; continue; }
                    if (s.StartsWith("GRAFIK", StringComparison.OrdinalIgnoreCase)) { hedef = null; continue; }
                    hedef?.Items.Add(s);
                }
            }
            if (cmb_RejiIp.Items.Count > 0) cmb_RejiIp.SelectedIndex = 0;
            if (cmb_GrafikIp.Items.Count > 0) cmb_GrafikIp.SelectedIndex = 0;
        }

        // =====================================================================
        //  BAGLANTI
        // =====================================================================
        private void btn_RejiBaglan_Click(object? sender, EventArgs e) => BaglantiDegistir(VizReji, cmb_RejiIp);
        private void btn_GrafikBaglan_Click(object? sender, EventArgs e) => BaglantiDegistir(VizGrafik, cmb_GrafikIp);

        private void BaglantiDegistir(Vizrt viz, ComboBox ip)
        {
            if (viz.isConnected) { viz.Disconnect(); return; }
            if (string.IsNullOrWhiteSpace(ip.Text)) { MessageBox.Show("Geçerli bir IP girin."); return; }
            viz.Connect(ip.Text);
        }

        private void OnRejiBaglandi(int id, string name) => UI(() =>
        {
            Baglandi(btn_RejiBaglan, lbl_RejiDurum, cmb_RejiIp);
            // Sahne baglanir baglanmaz yuklenir: Graphic Hub'dan yukleme asenkron oldugu icin
            // ilk VER aninda yuklemek, ardindan gelen yukleme ile az once yazilan metni ezebiliyor.
            VizReji.CurrentScene_Middle = "";
            SahneyiHazirla();
        });
        private void OnRejiKoptu(int id, string name) => UI(() => Koptu(btn_RejiBaglan, lbl_RejiDurum));
        private void OnGrafikBaglandi(int id, string name) => UI(() => Baglandi(btn_GrafikBaglan, lbl_GrafikDurum, cmb_GrafikIp));
        private void OnGrafikKoptu(int id, string name) => UI(() => Koptu(btn_GrafikBaglan, lbl_GrafikDurum));

        private void Baglandi(Button btn, Label lbl, ComboBox ip)
        {
            btn.BackColor = Color.LimeGreen;
            btn.ForeColor = Color.Black;
            btn.Text = "BAĞLI";
            lbl.Text = ip.Text;
            lbl.ForeColor = Color.DarkGreen;
            Log.Log("Bağlantı", ip.Text + " bağlandı");
        }

        private void Koptu(Button btn, Label lbl)
        {
            btn.BackColor = Color.Maroon;
            btn.ForeColor = Color.White;
            btn.Text = "BAĞLAN";
            lbl.Text = "no connection";
            lbl.ForeColor = Color.Maroon;
            if (btn == btn_RejiBaglan) VizReji.CurrentScene_Middle = ""; // yeniden baglaninca sahne tekrar yuklensin
        }

        private void cbx_RejiHb_CheckedChanged(object? sender, EventArgs e) { if (VizReji != null) VizReji.heartbeat = cbx_RejiHb.Checked; }
        private void cbx_GrafikHb_CheckedChanged(object? sender, EventArgs e) { if (VizGrafik != null) VizGrafik.heartbeat = cbx_GrafikHb.Checked; }

        private void btn_RejiSifirla_Click(object? sender, EventArgs e) => Sifirla(VizReji, "KJ REJİ");
        private void btn_GrafikSifirla_Click(object? sender, EventArgs e) => Sifirla(VizGrafik, "GRAFİK-1");

        private void Sifirla(Vizrt viz, string ad)
        {
            if (!viz.isConnected) return;
            if (MessageBox.Show($"{ad} motoru sıfırlanacak. Emin misiniz?", "Onay", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) != DialogResult.Yes) return;
            viz.Send("RENDERER*MAIN_LAYER*STAGE TO_START");
            viz.FullCleanup();
            viz.CurrentScene_Middle = "";
            if (viz == VizReji)
            {
                YayinDurumunuSifirla();
                SahneyiHazirla();   // temizlikten sonra sahne hemen yeniden yuklensin
            }
            Log.Log("SIFIRLA", ad);
        }

        // =====================================================================
        //  ADMIN / TESHIS
        // =====================================================================
        private void AdminModu(bool acik)
        {
            pnl_Diagnostic.Visible = acik;
        }

        private void btn_DiagnosticStep_Click(object? sender, EventArgs e) => diagnosticPasuse = true;
        private void btn_DiagnosticTemizle_Click(object? sender, EventArgs e) => tbx_diagnostic.Clear();

        private void btn_HamKomut_Click(object? sender, EventArgs e)
        {
            if (VizReji == null || !VizReji.isConnected || string.IsNullOrWhiteSpace(txt_HamKomut.Text)) return;
            VizReji.Send(txt_HamKomut.Text.Trim());
            Log.Log("HAM KOMUT", txt_HamKomut.Text.Trim());
        }

        // =====================================================================
        //  KLAVYE
        // =====================================================================
        protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
        {
            switch (keyData)
            {
                case Keys.F7:
                    Log?.Reji("Kısayol", "F7 (KJ AL)");
                    KjAl();
                    return true;
                case Keys.F8:
                    Log?.Reji("Kısayol", "F8 (TÜMÜNÜ AL)");
                    btn_TumunuAl_Click(btn_TumunuAl, EventArgs.Empty);
                    return true;
                case Keys.Control | Keys.Shift | Keys.D:
                    AdminModu(!pnl_Diagnostic.Visible);   // teshis paneli (gonderilen komutlari gosterir)
                    return true;
            }
            return base.ProcessCmdKey(ref msg, keyData);
        }

        // =====================================================================
        //  YARDIMCILAR
        // =====================================================================
        private void UI(Action a)
        {
            if (IsDisposed) return;
            if (InvokeRequired) BeginInvoke(a); else a();
        }

        /// <summary>Tum buton / checkbox / combo olaylarini REJI_LOG'a yazar (NTR Show'daki otomatik loglama).</summary>
        private void OtomatikLogla(Control kok)
        {
            foreach (Control c in kok.Controls)
            {
                switch (c)
                {
                    case Button b:
                        b.Click += (s, e) => Log.Reji("Tıklama", $"{b.Name} ({b.Text})");
                        break;
                    case CheckBox cb:
                        cb.CheckedChanged += (s, e) => Log.Reji("CheckBox", $"{cb.Name} ({cb.Text}) -> {(cb.Checked ? "AÇIK" : "KAPALI")}");
                        break;
                    case ComboBox cmb:
                        cmb.SelectionChangeCommitted += (s, e) => Log.Reji("ComboBox", $"{cmb.Name} -> {cmb.Text}");
                        break;
                }
                if (c.HasChildren) OtomatikLogla(c);
            }
        }
    }
}
