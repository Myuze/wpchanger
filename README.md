# 🎨 Multi-Monitor Wallpaper Changer

A Windows application that automatically rotates wallpapers on multiple monitors with support for portrait/landscape orientation matching.

## ✅ Your App is Ready!

### 🚀 Quick Start

**You now have TWO ways to run the app:**

1. **Desktop Shortcut** (✓ Already created!)

    - Look for "**Wallpaper Changer**" icon on your desktop
    - Double-click to run

2. **Standalone Executable** (✓ Already built!)
    - Located at: `dist/WallpaperChanger.exe`
    - Copy this file anywhere you want - it works independently!
    - Size: ~21 MB (includes everything needed)

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

### Tray Icon

-   **X button or Minimize** → Hides to system tray
-   **Double-click tray icon** → Restores window
-   **Right-click tray icon** → Menu with Restore/Exit options

## 🔧 Installation Options

### Option 1: Run on Windows Startup

1. Press `Win + R`
2. Type: `shell:startup`
3. Press Enter
4. Drag your desktop shortcut into the Startup folder

Now the app will start automatically when Windows boots!

### Option 2: Share the App

The `WallpaperChanger.exe` file is completely standalone:

-   Copy it to any Windows PC
-   No Python installation needed
-   No dependencies to install
-   Just double-click and run!

### Option 3: Rebuild/Update

If you make changes to the code:

```bash
# Rebuild the executable
python build_exe.py

# Create new shortcut
python create_exe_shortcut.py
```

## 📁 Project Files

```
WallpaperChanger/
├── wpchanger.py                    # Main application
├── dist/
│   └── WallpaperChanger.exe       # ← Standalone executable (21 MB)
├── build_exe.py                   # Build executable script
├── create_exe_shortcut.py         # Create desktop shortcut to .exe
├── create_shortcut.py             # Create desktop shortcut to Python script
├── WallpaperChanger.bat           # Batch launcher
├── requirements.txt               # Python dependencies
├── wallpaper_rotator_config.json  # Saved settings
└── INSTALLATION.md                # This file
```

## 🛠️ Development

### Requirements

```
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

-   **First run of .exe may be slow** - Windows Defender scans it
-   **Wallpaper fit not working?** - Use "Open Windows Personalization Settings" button
-   **Want custom icon?** - Edit `build_exe.py` and add `.ico` file
-   **Clean build folder?** - Delete `build/` and `dist/` folders, rebuild

## 🐛 Troubleshooting

**Executable too large?**

-   This is normal! It includes Python runtime and all libraries

**Antivirus alerts?**

-   Common with PyInstaller executables
-   Add to your antivirus exceptions

**Shortcut doesn't work after moving project?**

-   Run `python create_shortcut.py` again to recreate it

**App won't start?**

-   Check Windows Event Viewer for errors
-   Try running from command line to see error messages

## 📝 License

Free to use and modify!

---

**Enjoy your automatic wallpaper rotations! 🎨✨**
