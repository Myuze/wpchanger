# 🎨 Multi-Monitor Wallpaper Changer

A Windows application that automatically rotates wallpapers on multiple monitors
with support for portrait/landscape orientation matching.

## 📋 Features

-   ✅ **Multi-monitor support** - Different wallpapers on each monitor
-   ✅ **Truly random selection** - Each monitor gets a different random image
-   ✅ **Per-monitor orientation control** - Configure each monitor independently
-   ✅ **Flexible image rotation** - Choose rotation direction (left/right/none)
-   ✅ **All orientations mode** - Allow portrait images on landscape monitors
    (and vice versa)
-   ✅ **Automatic rotation** - Set custom intervals (minutes)
-   ✅ **Minimize to tray** - Runs in background, minimizes to system tray
-   ✅ **Wallpaper fit options** - Fill, Fit, Stretch, Center, Tile, Span
-   ✅ **Persistent settings** - Saves all your preferences
-   ✅ **Resizable UI** - Drag divider to resize status window
-   ✅ **Scrollable interface** - Access all controls easily

## 🎯 Usage

### Basic Setup

1. **Select monitors** - Check which monitors to rotate wallpapers on
2. **Choose directory** - Browse to your wallpaper folder
3. **Set interval** - How often to change (in minutes)
4. **Start rotation** - Click "Start Rotation"

### Advanced Per-Monitor Settings

For each monitor, you can configure:

-   **Orientation** - Set monitor as Portrait or Landscape
-   **All orientations** - Enable to allow both portrait and landscape images
-   **Rotation direction** - Choose how to rotate mismatched images
    (**none**, **left**, or **right**)

**Rotation options:**

-   **none** - No rotation (default orientation with black bars)
-   **left** - Rotate 90° counter-clockwise
-   **right** - Rotate 90° clockwise

### Examples

**Landscape monitor + "All orientations" checked + "left" rotation:**

-   Shows both landscape and portrait images
-   Portrait images are rotated 90° left to fill the screen

**Portrait monitor + "All orientations" unchecked:**

-   Shows only portrait images

**Any monitor + "none" rotation:**

-   Images display in their original orientation (may have black bars)

### Tray Icon

-   **Minimize button** → Hides to system tray
-   **Double-click tray icon** → Restores window
-   **Right-click tray icon** → Menu with Restore/Exit options

### Resizable Interface

-   **Drag the horizontal divider** between controls and status area to resize
-   **Mouse wheel** scrolls through the controls section
-   **Status window** adjusts automatically as you resize

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
-   Per-monitor "All orientations" settings
-   Per-monitor rotation direction preferences

## 💡 Tips

-   **Wallpaper fit not working?** - Use "Open Windows Personalization Settings"
    button

## 📝 License

Free to use and modify!

---

Enjoy your automatic wallpaper rotations! 🎨✨
