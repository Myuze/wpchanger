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
-   ✅ **Auto-start on launch** - Optionally start rotation when app launches
-   ✅ **Minimize to tray** - Runs in background, minimizes to system tray
-   ✅ **Tray menu controls** - Start/stop rotation without opening window
-   ✅ **Wallpaper fit options** - Fill, Fit, Stretch, Center, Tile, Span
-   ✅ **Persistent settings** - Saves all your preferences
-   ✅ **Resizable UI** - Drag divider to resize status window
-   ✅ **Scrollable interface** - Access all controls easily
-   ✅ **Automatic cleanup** - Temp folder managed automatically

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
-   **Right-click tray icon** → Menu with options:

**Tray Menu Options:**

-   **Restore** - Opens the main window
-   **Start/Stop Rotation** - Toggle rotation without opening window
    (checkmark shows when active)
-   **Auto-start on Launch** - Enable/disable auto-start feature
    (checkmark shows when enabled)
-   **Exit** - Closes the application

### Auto-Start Feature

When **Auto-start on Launch** is enabled:

-   Rotation begins automatically when the app launches
-   Works with your saved wallpaper directory and interval settings
-   Perfect for "set it and forget it" operation
-   Enable/disable from the tray menu at any time

### Resizable Interface

-   **Drag the horizontal divider** between controls and status area to resize
-   **Mouse wheel** scrolls through the controls section
-   **Status window** adjusts automatically as you resize

## 🔧 Installation Options

### Option 1: Run as Python Script

1. Navigate folder containing `wpchanger.py`
2. Run `pip install -r requirements.txt` (if not done yet)
3. Run `python wpchanger.py`

### Option 2: Build Standalone Executable

Build a standalone `.exe` file that doesn't require Python installed:

#### Using PyInstaller

1. Install PyInstaller:

    ```bash
    pip install pyinstaller
    ```

2. Build the executable:

    ```bash
    pyinstaller --onefile --windowed --icon=NONE ^
      --add-data "README.md;." ^
      --hidden-import=PIL._tkinter_finder ^
      --collect-all=pystray ^
      wpchanger.py
    ```

3. Find your executable in `dist/wpchanger.exe`

**PyInstaller options explained:**

-   `--onefile` - Creates a single executable file
-   `--windowed` - No console window (GUI only)
-   `--icon=NONE` - No custom icon (use default)
-   `--add-data` - Include additional files
-   `--hidden-import` - Include PIL tkinter support
-   `--collect-all=pystray` - Include all pystray dependencies

**Note:** The first run may take a moment as PyInstaller unpacks files to a
temp directory.

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
-   Auto-start on launch preference
-   Orientation matching mode
-   Wallpaper fit preference
-   Per-monitor "All orientations" settings
-   Per-monitor rotation direction preferences

The config file is created automatically on first run and updated whenever you
change settings.

## 💡 Tips

-   **Wallpaper fit not working?** - Use "Open Windows Personalization Settings"
    button
-   **Temp folder cleanup** - Rotated images are automatically cleaned up to
    prevent disk space accumulation
-   **Set it and forget it** - Enable auto-start, minimize to tray, and let it
    run in the background

## 📝 License

Free to use and modify!

---

Enjoy your automatic wallpaper rotations! 🎨✨
