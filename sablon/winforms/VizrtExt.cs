namespace __NS__
{
    /// <summary>
    /// VizScenes sabitleri ('$' ile baslayan tam yollar) icin komut yardimcilari.
    /// Vizrt.cs NTR Show'dan oldugu gibi kopyalandi; ona dokunmamak icin eklenti olarak duruyor.
    /// </summary>
    public static class VizrtExt
    {
        public static void SetTextPath(this Vizrt viz, string scene, string containerPath, string text)
            => viz.Send("SCENE*" + scene + "*TREE*" + containerPath + "*GEOM*TEXT SET " + text);

        public static void SetActivePath(this Vizrt viz, string scene, string containerPath, bool active)
            => viz.Send("SCENE*" + scene + "*TREE*" + containerPath + "*ACTIVE SET " + (active ? "1" : "0"));

        public static void SetImagePath(this Vizrt viz, string scene, string containerPath, string imagePath)
            => viz.Send("SCENE*" + scene + "*TREE*" + containerPath + "*IMAGE SET \"" + imagePath + "\"");

        /// <summary>Resim dosyasi (canli uygulamalardaki gibi tirnaksiz; dosya adinda bosluk olmamali).</summary>
        public static void SetImageFile(this Vizrt viz, string scene, string containerPath, string dosya)
            => viz.Send("SCENE*" + scene + "*TREE*" + containerPath + "*IMAGE SET " + dosya);

        public static void SetImageClipFile(this Vizrt viz, string scene, string containerPath, string dosya)
            => viz.Send("SCENE*" + scene + "*TREE*" + containerPath + "*FUNCTION*imageClip*imageLoadFileName SET " + dosya);

        /// <summary>Arka plan klibi (kelebek BG$softclip).</summary>
        public static void SetSoftClipFile(this Vizrt viz, string scene, string containerPath, string dosya)
            => viz.Send("SCENE*" + scene + "*TREE*" + containerPath + "*FUNCTION*SoftClip*clipFile SET " + dosya);

        public static void StartReverse(this Vizrt viz, string scene, string directorPath)
            => viz.Send("SCENE*" + scene + "*STAGE*DIRECTOR*" + directorPath + " START REVERSE");

        /// <summary>Director'u (tam yol, orn. "$KJ$TEK_KJ$IN") baslatir.</summary>
        public static void Start(this Vizrt viz, string scene, string directorPath)
            => viz.Send("SCENE*" + scene + "*STAGE*DIRECTOR*" + directorPath + " START");
    }
}
