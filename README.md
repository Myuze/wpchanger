# 🎨 Multi-Monitor Wallpaper Changer

A Windows application that automatically rotates wallpapers on multiple monitors
with support for portrait/landscape orientation matching.

## 📋 Features

-   ✅ **Multi-monitor support** - Different wallpapers on each monitor
-   ✅ **Orientation matching** - Portrait images → Portrait monitors
-   ✅ **Automatic rotation** - Set custom intervals (minutes)
-   ✅ **Minimize to tray** - Runs in background, minimizes to system tray
-   ✅ **Image rotation** - Auto-rotates portrait images for landscape monitors
-   ✅ **Wallpaper fit options** - Fill, Fit, Stretch, Center, Tile, Span
-   ✅ **Persistent settings** - Saves all your preferences

## 🎯 Usage

1. **Select monitors** - Check which monitors to rotate
2. **Choose directory** - Browse to your wallpaper folder
3. **Set interval** - How often to change (in minutes)
4. **Start rotation** - Click "Start Rotation"

## 🔧 Installation Options

### Run as Python Script

1. Navigate folder containing `wpchanger.py`
2. Run `pip install -r requirements.txt` (if not done yet)
3. Run `python wpchanger.py`

## 📁 Project Files

```text
WallpaperChanger/
├── wpchanger.py                   # Main application
├── requirements.txt               # Python dependencies
└── wallpaper_rotator_config.json  # Saved settings
```

## 🛠️ Development

### Requirements

```text
comtypes
pywin32
pillow
pystray
winshell
```

### Install for Development

```bash
pip install -r requirements.txt
python wpchanger.py
```

## ⚙️ Configuration

Settings are automatically saved in `wallpaper_rotator_config.json`:

-   Active monitors
-   Wallpaper directory
-   Rotation interval
-   Orientation matching mode
-   Wallpaper fit preference

## 💡 Tips

-   **Wallpaper fit not working?** - Use "Open Windows Personalization Settings"
    button

## 📝 License

Free to use and modify!

---

Enjoy your automatic wallpaper rotations! 🎨✨
