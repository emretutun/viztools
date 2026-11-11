namespace __NS__
{
    /// <summary>NTR Show'daki ToolsHelper'in gonderim icin gereken kismi (CClientSession kullanir).</summary>
    public static class ToolsHelper
    {
        public const char END_POINTER = '\0';

        public static string CreateMessagePack(object[] prmList)
        {
            string pack = "";
            string addSpr = "";
            foreach (object prm in prmList)
            {
                pack += addSpr + prm;
                addSpr = " ";
            }
            pack += END_POINTER;
            return pack;
        }
    }

    public static class AppVersions
    {
        public const string Surum = "0.1";
    }
}
