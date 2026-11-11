namespace __NS__
{
    internal static class Program
    {
        [STAThread]
        static void Main()
        {
            ApplicationConfiguration.Initialize();

            // Tum veri/ayar dosyalari (scenes.txt, setting, IpList.txt, DenyIPlist.txt, kj_list.json, LOG)
            // exe yanindaki ShowData klasorunden okunur.
            string showData = Path.Combine(AppContext.BaseDirectory, "ShowData");
            Directory.CreateDirectory(showData);
            Directory.SetCurrentDirectory(showData);

            Application.Run(new Main());
        }
    }
}
