using System.Collections.Generic;
using System.Drawing;
using System.Windows.Forms;

/// <summary>
/// Birbirleriyle ilişkili buton gruplarının renk ve durum yönetimini yapar.
/// </summary>
public class ButtonGroupManager
{
    // --- Alanlar (Fields) ---

    // Temel grupları saklamak için sözlükler (dictionaries)
    private readonly Dictionary<Button, List<Button>> _alButtonGroups = new Dictionary<Button, List<Button>>();
    private readonly Dictionary<Button, List<Button>> _verButtonToGroupMap = new Dictionary<Button, List<Button>>();

    // Özel davranış gruplarını saklamak için kümeler (sets)
    private readonly HashSet<Button> _mutuallyExclusiveVerButtons = new HashSet<Button>();
    private readonly HashSet<Button> _specialResetTriggerAlButtons = new HashSet<Button>();
    private readonly HashSet<Button> _specialResetTriggerVerButtons = new HashSet<Button>();
    private readonly HashSet<Button> _specialResetTargetVerButtons = new HashSet<Button>();

    // Buton renkleri
    private readonly Color _activeBackColor;
    private readonly Color _inactiveBackColor;
    private readonly Color _activeForeColor;
    private readonly Color _inactiveForeColor;


    // --- Kurucu Metot (Constructor) ---

    public ButtonGroupManager(Color activeBackColor, Color inactiveBackColor, Color activeForeColor, Color inactiveForeColor)
    {
        _activeBackColor = activeBackColor;
        _inactiveBackColor = inactiveBackColor;
        _activeForeColor = activeForeColor;
        _inactiveForeColor = inactiveForeColor;
    }


    // --- Grup Tanımlama Metotları ---

    /// <summary>
    /// Bir "AL" butonu ve ona bağlı bir veya daha fazla "VER" butonundan oluşan bir grup ekler.
    /// </summary>
    public void AddGroup(Button alButton, params Button[] verButtons)
    {
        var verButtonList = new List<Button>(verButtons);
        _alButtonGroups[alButton] = verButtonList;

        foreach (var verButton in verButtonList)
        {
            _verButtonToGroupMap[verButton] = verButtonList;
            verButton.BackColor = _inactiveBackColor;
            verButton.ForeColor = _inactiveForeColor;
        }
    }

    /// <summary>
    /// Birine basıldığında diğerlerinin kapanması gereken "VER" butonlarından oluşan büyük bir grup tanımlar.
    /// </summary>
    public void DefineMutuallyExclusiveGroup(params Button[] verButtons)
    {
        foreach (var verButton in verButtons)
        {
            _mutuallyExclusiveVerButtons.Add(verButton);
        }
    }

    /// <summary>
    /// Diğer butonları sıfırlamak için tetikleyici olarak kullanılacak "AL" butonlarını tanımlar.
    /// </summary>
    public void DefineSpecialResetTriggers(params Button[] alButtons)
    {
        foreach (var alButton in alButtons)
        {
            _specialResetTriggerAlButtons.Add(alButton);
        }
    }

    /// <summary>
    /// Diğer butonları sıfırlamak için tetikleyici olarak kullanılacak "VER" butonlarını tanımlar.
    /// </summary>
    public void DefineSpecialVerResetTriggers(params Button[] verButtons)
    {
        foreach (var verButton in verButtons)
        {
            _specialResetTriggerVerButtons.Add(verButton);
        }
    }

    /// <summary>
    /// Özel tetikleyicilere basıldığında sıfırlanacak olan hedef "VER" butonlarını tanımlar.
    /// </summary>
    public void DefineSpecialResetTargets(params Button[] verButtons)
    {
        foreach (var verButton in verButtons)
        {
            _specialResetTargetVerButtons.Add(verButton);
        }
    }


    // --- Olay Yönetim Metotları ---

    /// <summary>
    /// Bir "VER" butonuna tıklandığında çağrılır. İlgili butonları aktif/pasif duruma getirir.
    /// </summary>
    public void HandleVerClick(Button clickedVerButton)
    {
        // Eğer tıklanan buton büyük "karşılıklı dışlayıcı" grupta ise, önce o gruptaki tüm butonları pasif hale getir.
        if (_mutuallyExclusiveVerButtons.Contains(clickedVerButton))
        {
            foreach (var buttonInExclusiveGroup in _mutuallyExclusiveVerButtons)
            {
                buttonInExclusiveGroup.BackColor = _inactiveBackColor;
                buttonInExclusiveGroup.ForeColor = _inactiveForeColor;
            }
        }

        // Tıklanan butonun kendi küçük grubunu yönet (tıklananı aktif yap, diğerlerini pasif yap).
        if (_verButtonToGroupMap.TryGetValue(clickedVerButton, out List<Button> group))
        {
            foreach (var buttonInGroup in group)
            {
                buttonInGroup.BackColor = (buttonInGroup == clickedVerButton) ? _activeBackColor : _inactiveBackColor;
                buttonInGroup.ForeColor = (buttonInGroup == clickedVerButton) ? _activeForeColor : _inactiveForeColor;
            }
        }

        // Eğer tıklanan "VER" butonu özel bir tetikleyici ise, hedef butonları sıfırla.
        if (_specialResetTriggerVerButtons.Contains(clickedVerButton))
        {
            foreach (var targetButton in _specialResetTargetVerButtons)
            {
                targetButton.BackColor = _inactiveBackColor;
                targetButton.ForeColor = _inactiveForeColor;
            }
        }
    }

    /// <summary>
    /// Bir "AL" butonuna tıklandığında çağrılır. İlgili grupları pasif duruma getirir.
    /// </summary>
    public void HandleAlClick(Button clickedAlButton)
    {
        // Tıklanan "AL" butonunun kendi grubundaki "VER" butonlarını sıfırla.
        if (_alButtonGroups.TryGetValue(clickedAlButton, out List<Button> group))
        {
            foreach (var buttonInGroup in group)
            {
                buttonInGroup.BackColor = _inactiveBackColor;
                buttonInGroup.ForeColor = _inactiveForeColor;
            }
        }

        // Eğer tıklanan "AL" butonu özel bir tetikleyici ise, hedef butonları da sıfırla.
        if (_specialResetTriggerAlButtons.Contains(clickedAlButton))
        {
            foreach (var targetButton in _specialResetTargetVerButtons)
            {
                targetButton.BackColor = _inactiveBackColor;
                targetButton.ForeColor = _inactiveForeColor;
            }
        }
    }

    /// <summary>
    /// Yönetilen tüm gruplardaki bütün "VER" butonlarını pasif durumuna getirir.
    /// </summary>
    public void ResetAllGroups()
    {
        foreach (var group in _alButtonGroups.Values)
        {
            foreach (var buttonInGroup in group)
            {
                buttonInGroup.BackColor = _inactiveBackColor;
                buttonInGroup.ForeColor = _inactiveForeColor;
            }
        }
    }
}