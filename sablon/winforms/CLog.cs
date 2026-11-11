using System.Text;

namespace __NS__
{
    /// <summary>
    /// Dosya tabanli log (DB yok). Calisma dizini ShowData oldugu icin:
    ///   LOG\actions__yyyy_MM_dd.log   islemler
    ///   LOG\Error__yyyy_MM_dd.log     hatalar
    ///   REJI_LOG\reji_log_yyyy-MM-dd.txt  operator tiklamalari (OtomatikLogla)
    /// </summary>
    public class CLog
    {
        private readonly Main mainForm;
        private readonly object kilit = new object();

        public CLog(Main form)
        {
            mainForm = form;
            Directory.CreateDirectory("LOG");
            Directory.CreateDirectory("REJI_LOG");
            EskiLoglariSil(30);
        }

        public void Log(string description, string data = "")
        {
            Yaz($"LOG\\actions__{DateTime.Now:yyyy_MM_dd}.log", description, data);
        }

        public void Error(string description, string data = "")
        {
            Yaz($"LOG\\Error__{DateTime.Now:yyyy_MM_dd}.log", description, data);
            DiagnosticYaz("[HATA] " + description + " " + data);
        }

        public void Reji(string olay, string ayrinti)
        {
            Yaz($"REJI_LOG\\reji_log_{DateTime.Now:yyyy-MM-dd}.txt", olay, ayrinti);
        }

        private void Yaz(string dosya, string description, string data)
        {
            string satir = $"[{DateTime.Now:dd-MM-yyyy HH:mm:ss}]{{BS:{description}}}{{{data}}}{Environment.NewLine}";
            try
            {
                lock (kilit) File.AppendAllText(dosya, satir, Encoding.UTF8);
            }
            catch
            {
                // log yazilamazsa uygulama durmamali
            }
        }

        private void DiagnosticYaz(string metin)
        {
            var tbx = mainForm?.tbx_diagnostic;
            if (tbx == null || tbx.IsDisposed || !tbx.Visible) return;
            if (tbx.InvokeRequired) { tbx.BeginInvoke(new Action(() => DiagnosticYaz(metin))); return; }
            tbx.AppendText(metin + Environment.NewLine);
        }

        private static void EskiLoglariSil(int gun)
        {
            try
            {
                foreach (var klasor in new[] { "LOG", "REJI_LOG" })
                    foreach (var f in Directory.GetFiles(klasor))
                        if (File.GetLastWriteTime(f) < DateTime.Now.AddDays(-gun)) File.Delete(f);
            }
            catch { }
        }
    }
}
