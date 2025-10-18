from pystray import MenuItem as item
import pystray
from PIL import Image
import json
from tkinter import ttk, filedialog, messagebox
import tkinter as tk
import threading
import win32gui
import win32con
import win32api
from comtypes.hresult import S_OK
from comtypes import GUID, COMMETHOD
import comtypes.client
from ctypes.wintypes import UINT, RECT
import os
import sys
import time
import random
import subprocess
from datetime import datetime
from pathlib import Path
from ctypes import windll, c_wchar_p, c_uint, Structure, POINTER, byref, c_int

# Ensure random is properly seeded (important for PyInstaller builds)
random.seed()

# IDesktopWallpaper interface definitions
CLSID_DesktopWallpaper = GUID('{C2CF3110-460E-4fc1-B9D0-8A1C0C9CC4BD}')
IID_IDesktopWallpaper = GUID('{B92B56A9-8B55-4E14-9A89-0199BBB6F93B}')


class IDesktopWallpaper(comtypes.IUnknown):
    _iid_ = IID_IDesktopWallpaper
    _methods_ = [
        COMMETHOD([], UINT, 'SetWallpaper',
                  (['in'], c_wchar_p, 'monitorID'),
                  (['in'], c_wchar_p, 'wallpaper')),
        COMMETHOD([], UINT, 'GetWallpaper',
                  (['in'], c_wchar_p, 'monitorID'),
                  (['out'], POINTER(c_wchar_p), 'wallpaper')),
        COMMETHOD([], UINT, 'GetMonitorDevicePathAt',
                  (['in'], UINT, 'monitorIndex'),
                  (['out'], POINTER(c_wchar_p), 'monitorID')),
        COMMETHOD([], UINT, 'GetMonitorDevicePathCount',
                  (['out'], POINTER(UINT), 'count')),
        COMMETHOD([], UINT, 'GetMonitorRECT',
                  (['in'], c_wchar_p, 'monitorID'),
                  (['out'], POINTER(RECT), 'displayRect')),
        COMMETHOD([], UINT, 'SetPosition',
                  (['in'], c_int, 'position')),
        COMMETHOD([], UINT, 'GetPosition',
                  (['out'], POINTER(c_int), 'position')),
        COMMETHOD([], UINT, 'SetBackgroundColor',
                  (['in'], c_uint, 'color')),
        COMMETHOD([], UINT, 'GetBackgroundColor',
                  (['out'], POINTER(c_uint), 'color')),
        COMMETHOD([], UINT, 'SetSlideshow',
                  (['in'], POINTER(comtypes.IUnknown), 'items')),
        COMMETHOD([], UINT, 'GetSlideshow',
                  (['out'], POINTER(POINTER(comtypes.IUnknown)), 'items')),
        COMMETHOD([], UINT, 'SetSlideshowOptions',
                  (['in'], c_uint, 'options'),
                  (['in'], c_uint, 'slideshowTick')),
        COMMETHOD([], UINT, 'GetSlideshowOptions',
                  (['out'], POINTER(c_uint), 'options'),
                  (['out'], POINTER(c_uint), 'slideshowTick')),
        COMMETHOD([], UINT, 'AdvanceSlideshow',
                  (['in'], c_wchar_p, 'monitorID'),
                  (['in'], c_int, 'direction')),
        COMMETHOD([], UINT, 'GetStatus',
                  (['out'], POINTER(c_int), 'state')),
        COMMETHOD([], UINT, 'Enable',
                  (['in'], c_int, 'enable')),
    ]


# Wallpaper position constants
DWPOS_CENTER = 0
DWPOS_TILE = 1
DWPOS_STRETCH = 2
DWPOS_FIT = 3
DWPOS_FILL = 4
DWPOS_SPAN = 5


class WallpaperRotator:
    def __init__(self):
        self.desktop_wallpaper = comtypes.client.CreateObject(
            CLSID_DesktopWallpaper,
            interface=IDesktopWallpaper
        )
        self.monitors = self.get_monitors()
        self.active_monitors = {}  # {monitor_id: orientation}
        # {monitor_id: bool} - Allow all image orientations
        self.monitor_allow_all_orientations = {}
        # {monitor_id: 'left'|'right'} - Rotation direction for mismatched orientations
        self.monitor_rotation_direction = {}
        self.wallpaper_dir = None
        self.image_files = []
        self.portrait_images = []
        self.landscape_images = []
        self.monitor_indices = {}  # {monitor_id: current_index}
        self.rotation_interval = 30  # minutes
        self.running = False
        self.rotation_thread = None
        self.config_file = 'wallpaper_rotator_config.json'
        self.use_image_orientation = True  # New option
        self.wallpaper_position = DWPOS_FILL  # Default to Fill
        self.last_wallpaper_path = None  # Track last set wallpaper for refresh
        self.current_rotated_images = set()  # Track currently used rotated images
        self.auto_start_rotation = False  # Auto-start rotation on app launch
        self.load_config()

    def get_monitors(self):
        """Get all monitors with their IDs and orientations"""
        monitors = []
        count = self.desktop_wallpaper.GetMonitorDevicePathCount()

        for i in range(count):
            monitor_id = self.desktop_wallpaper.GetMonitorDevicePathAt(i)

            rect = self.desktop_wallpaper.GetMonitorRECT(monitor_id)

            width = rect.right - rect.left
            height = rect.bottom - rect.top
            orientation = 'Portrait' if height > width else 'Landscape'

            monitors.append({
                'id': monitor_id,
                'index': i,
                'width': width,
                'height': height,
                'orientation': orientation,
                'rect': f"{width}x{height}"
            })

        return monitors

    def set_wallpaper(self, monitor_id, image_path):
        """Set wallpaper for specific monitor"""
        try:
            abs_path = os.path.abspath(image_path)

            # Check if we need to rotate the image
            rotated_path = self.prepare_image_for_monitor(monitor_id, abs_path)

            # Set the wallpaper for this specific monitor
            self.desktop_wallpaper.SetWallpaper(monitor_id, rotated_path)

            # Store the last wallpaper path for refresh purposes
            self.last_wallpaper_path = rotated_path

            print(
                f"Set wallpaper on monitor to: {os.path.basename(image_path)}")
            return True
        except Exception as e:
            print(f"ERROR setting wallpaper: {e}")
            import traceback
            traceback.print_exc()
            return False

    def prepare_image_for_monitor(self, monitor_id, image_path):
        """Rotate image if needed to match monitor orientation"""
        try:
            # Get monitor orientation
            monitor_orientation = None
            for monitor in self.monitors:
                if monitor['id'] == monitor_id:
                    monitor_orientation = monitor['orientation']
                    break

            if not monitor_orientation:
                return image_path

            # Check image orientation
            with Image.open(image_path) as img:
                # Handle EXIF orientation
                try:
                    exif = img.getexif()
                    if exif:
                        orientation = exif.get(274)
                        if orientation in [6, 8]:  # Already rotated in EXIF
                            width, height = img.height, img.width
                        else:
                            width, height = img.size
                    else:
                        width, height = img.size
                except:
                    width, height = img.size

                image_orientation = 'Portrait' if height > width else 'Landscape'

                # If portrait image on landscape monitor OR landscape image on portrait monitor, rotate it
                if image_orientation != monitor_orientation:
                    # Get rotation direction for this monitor
                    rotation_direction = self.monitor_rotation_direction.get(
                        monitor_id, 'none')

                    # If rotation is set to 'none', don't rotate - use original orientation
                    if rotation_direction == 'none':
                        print(
                            f"  No rotation applied - using image in default orientation")
                        return image_path

                    # Create rotated version
                    temp_dir = os.path.join(os.path.dirname(
                        image_path), '.wallpaper_temp')
                    os.makedirs(temp_dir, exist_ok=True)

                    rotated_filename = f"rotated_{rotation_direction}_{os.path.basename(image_path)}"
                    rotated_path = os.path.join(temp_dir, rotated_filename)

                    # Load and rotate image
                    img_copy = Image.open(image_path)

                    # Apply EXIF rotation first if needed
                    try:
                        exif = img_copy.getexif()
                        if exif and exif.get(274):
                            # Auto-orient based on EXIF
                            from PIL import ImageOps
                            img_copy = ImageOps.exif_transpose(img_copy)
                    except:
                        pass

                    # Rotate based on direction: left = 90° counter-clockwise, right = 270° counter-clockwise (or -90°)
                    if rotation_direction == 'left':
                        rotated_img = img_copy.rotate(90, expand=True)
                    else:  # right
                        rotated_img = img_copy.rotate(-90, expand=True)

                    rotated_img.save(rotated_path, quality=95)
                    img_copy.close()

                    # Track this rotated image as currently in use
                    self.current_rotated_images.add(rotated_path)

                    print(
                        f"  Rotated {image_orientation} image {rotation_direction} for {monitor_orientation} monitor: {rotated_filename}")
                    return rotated_path

                return image_path

        except Exception as e:
            print(f"Error preparing image: {e}")
            return image_path

    def cleanup_temp_images(self):
        """Clean up old rotated images that are no longer in use"""
        try:
            if not self.wallpaper_dir:
                return

            temp_dir = os.path.join(self.wallpaper_dir, '.wallpaper_temp')
            if not os.path.exists(temp_dir):
                return

            # Get all files in temp directory
            temp_files = []
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                if os.path.isfile(file_path):
                    temp_files.append(file_path)

            # Delete files that are not currently in use
            deleted_count = 0
            for file_path in temp_files:
                if file_path not in self.current_rotated_images:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        print(f"Could not delete temp file {file_path}: {e}")

            if deleted_count > 0:
                print(
                    f"Cleaned up {deleted_count} old rotated images from temp folder")

        except Exception as e:
            print(f"Error cleaning up temp images: {e}")

    def refresh_desktop(self):
        """Force Windows to refresh the desktop wallpaper display"""
        try:
            # Method 1: Use SystemParametersInfo to force wallpaper update
            SPI_SETDESKWALLPAPER = 20
            SPIF_UPDATEINIFILE = 0x01
            SPIF_SENDCHANGE = 0x02

            # Pass None to refresh current wallpaper settings
            result = windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER,
                0,
                None,
                SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            )
            print(f"DEBUG: SystemParametersInfo called, result: {result}")

            # Method 2: Broadcast setting change
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            SMTO_ABORTIFHUNG = 0x0002
            win32gui.SendMessageTimeout(
                HWND_BROADCAST,
                WM_SETTINGCHANGE,
                SPI_SETDESKWALLPAPER,
                "ImmersiveColorSet",
                SMTO_ABORTIFHUNG,
                5000
            )
            print(f"DEBUG: Desktop refresh broadcast sent")

            # Small delay to let Windows process
            time.sleep(0.1)

        except Exception as e:
            print(f"DEBUG: Error refreshing desktop: {e}")
            import traceback
            traceback.print_exc()

    def get_image_orientation(self, image_path):
        """Determine if image is portrait or landscape based on dimensions"""
        try:
            with Image.open(image_path) as img:
                # Handle EXIF orientation - but do it quickly
                try:
                    # Check EXIF orientation tag
                    exif = img.getexif()
                    if exif:
                        # 274 is the orientation tag
                        orientation = exif.get(274)
                        # If rotated 90 or 270 degrees, swap dimensions
                        if orientation in [6, 8]:  # 6=90CW, 8=90CCW
                            width, height = img.size
                            width, height = height, width  # Swap
                        else:
                            width, height = img.size
                    else:
                        width, height = img.size
                except:
                    width, height = img.size

                return 'Portrait' if height > width else 'Landscape'
        except Exception as e:
            print(f"Error reading image {image_path}: {e}")
            return None

    def scan_images(self, directory, progress_callback=None):
        """Scan directory and subdirectories for image files"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'}
        self.image_files = []
        self.portrait_images = []
        self.landscape_images = []

        # First pass: collect all image paths (fast)
        for root, dirs, files in os.walk(directory):
            for file in files:
                if Path(file).suffix.lower() in image_extensions:
                    full_path = os.path.join(root, file)
                    self.image_files.append(full_path)

        total = len(self.image_files)

        # Second pass: categorize by orientation if enabled (slower)
        if self.use_image_orientation and total > 0:
            for idx, full_path in enumerate(self.image_files):
                if progress_callback:
                    progress_callback(idx, total)

                orientation = self.get_image_orientation(full_path)
                if orientation == 'Portrait':
                    self.portrait_images.append(full_path)
                elif orientation == 'Landscape':
                    self.landscape_images.append(full_path)

        # Shuffle both lists - use time-based seed for extra randomness
        random.shuffle(self.image_files)
        if self.portrait_images:
            random.shuffle(self.portrait_images)
        if self.landscape_images:
            random.shuffle(self.landscape_images)

        # Reset indices for all monitors with offset to ensure different images
        # Group monitors by orientation and offset their starting indices
        portrait_count = 0
        landscape_count = 0
        self.monitor_indices = {}

        # Sort monitor IDs to ensure consistent ordering
        sorted_monitors = sorted(self.active_monitors.items())

        for monitor_id, orientation in sorted_monitors:
            if orientation == 'Portrait':
                # Ensure each portrait monitor gets a different starting image
                image_list_len = len(
                    self.portrait_images) if self.portrait_images else len(self.image_files)
                if image_list_len > 0:
                    self.monitor_indices[monitor_id] = portrait_count % image_list_len
                else:
                    self.monitor_indices[monitor_id] = 0
                portrait_count += 1
            else:  # Landscape
                # Ensure each landscape monitor gets a different starting image
                image_list_len = len(
                    self.landscape_images) if self.landscape_images else len(self.image_files)
                if image_list_len > 0:
                    self.monitor_indices[monitor_id] = landscape_count % image_list_len
                else:
                    self.monitor_indices[monitor_id] = 0
                landscape_count += 1

        return len(self.image_files)

    def rotate_wallpaper(self):
        """Rotate to next wallpaper for all active monitors"""
        if not self.image_files or not self.active_monitors:
            return False

        # Clean up old rotated images before creating new ones
        # Clear the current set so we can track new rotated images
        self.cleanup_temp_images()
        self.current_rotated_images.clear()

        # Set all wallpapers as quickly as possible
        # Note: Windows updates monitors sequentially - there's no way to prevent
        # a brief flash when using per-monitor wallpapers with IDesktopWallpaper
        success = True
        wallpapers_set = []

        # Initialize indices for any monitors that don't have them yet
        # Use random indices to ensure each monitor gets a different random image
        if not self.monitor_indices:
            used_image_paths = set()
            sorted_monitors = sorted(self.active_monitors.items())

            for mon_id, mon_orientation in sorted_monitors:
                allow_all = self.monitor_allow_all_orientations.get(
                    mon_id, False)

                # Determine which image list to use
                if allow_all:
                    temp_list = self.image_files
                elif self.use_image_orientation:
                    if mon_orientation == 'Portrait':
                        temp_list = self.portrait_images if self.portrait_images else self.image_files
                    else:
                        temp_list = self.landscape_images if self.landscape_images else self.image_files
                else:
                    temp_list = self.image_files

                # Assign a random index, trying to avoid using the same image file
                if temp_list:
                    list_len = len(temp_list)
                    # Try to get a unique image (not already used by another monitor)
                    attempts = 0
                    # Try up to 50 times or list length
                    while attempts < min(50, list_len):
                        idx = random.randint(0, list_len - 1)
                        image_path = temp_list[idx]
                        # Check if this image has already been assigned to another monitor
                        if image_path not in used_image_paths or attempts >= min(49, list_len - 1):
                            used_image_paths.add(image_path)
                            self.monitor_indices[mon_id] = idx
                            break
                        attempts += 1
                else:
                    self.monitor_indices[mon_id] = 0

        # Track which images are being used in this rotation to avoid duplicates
        images_being_used = {}  # {monitor_id: image_path}

        for monitor_id, orientation in self.active_monitors.items():
            # If a specific monitor is missing an index, assign a random one to ensure uniqueness
            if monitor_id not in self.monitor_indices:
                allow_all = self.monitor_allow_all_orientations.get(
                    monitor_id, False)

                # Select appropriate image list
                if allow_all:
                    temp_list = self.image_files
                elif self.use_image_orientation:
                    if orientation == 'Portrait':
                        temp_list = self.portrait_images if self.portrait_images else self.image_files
                    else:
                        # Landscape monitors use landscape images only (unless allow_all is checked)
                        temp_list = self.landscape_images if self.landscape_images else self.image_files
                else:
                    temp_list = self.image_files

                # Assign a random starting index
                if temp_list:
                    self.monitor_indices[monitor_id] = random.randint(
                        0, len(temp_list) - 1)
                else:
                    self.monitor_indices[monitor_id] = 0

            # Select appropriate image list based on mode and per-monitor settings
            allow_all = self.monitor_allow_all_orientations.get(
                monitor_id, False)

            if allow_all:
                # Use all images if "All orientations" is enabled for this monitor
                image_list = self.image_files
            elif self.use_image_orientation:
                # Match image orientation to monitor orientation
                if orientation == 'Portrait':
                    image_list = self.portrait_images if self.portrait_images else self.image_files
                else:
                    # Landscape monitors only use landscape images unless "All orientations" is checked
                    image_list = self.landscape_images if self.landscape_images else self.image_files
            else:
                # Use all images regardless of orientation
                image_list = self.image_files

            if not image_list:
                continue

            # Pick a random image that's not already being used by another monitor
            attempts = 0
            max_attempts = min(50, len(image_list))  # Try up to 50 times
            image_path = None

            while attempts < max_attempts:
                # Pick a random index
                index = random.randint(0, len(image_list) - 1)
                image_path = image_list[index]

                # Check if this image is already being used
                if image_path not in images_being_used.values():
                    # Found a unique image
                    break

                attempts += 1

            # If we couldn't find a unique image after max_attempts, just use the last one tried
            if image_path is None:
                index = random.randint(0, len(image_list) - 1)
                image_path = image_list[index]

            images_being_used[monitor_id] = image_path

            # Store the index for reference (though we'll pick random next time anyway)
            self.monitor_indices[monitor_id] = index

            # Set wallpaper
            if self.set_wallpaper(monitor_id, image_path):
                wallpapers_set.append(monitor_id)
            else:
                success = False

        # Apply the wallpaper position/fit mode
        if wallpapers_set:
            try:
                # Set position
                self.desktop_wallpaper.SetPosition(self.wallpaper_position)
                print(f"Wallpaper fit mode set to: {self.wallpaper_position}")

                # Notify Windows of the change
                SPI_SETDESKWALLPAPER = 20
                SPIF_UPDATEINIFILE = 0x01
                SPIF_SENDCHANGE = 0x02

                windll.user32.SystemParametersInfoW(
                    SPI_SETDESKWALLPAPER,
                    0,
                    None,
                    SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
                )
                print(
                    f"Wallpapers set on {len(wallpapers_set)} monitors")

            except Exception as e:
                print(f"Error applying wallpaper settings: {e}")

        return success

    def start_rotation(self):
        """Start the rotation (no thread needed - uses tkinter timer)"""
        if not self.running:
            self.running = True
            # Change wallpaper immediately on start
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] Starting wallpaper rotation")
            self.rotate_wallpaper()
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] Next change in {self.rotation_interval} minutes")

    def stop_rotation(self):
        """Stop the rotation"""
        self.running = False
        # Clean up temp images when stopping
        self.cleanup_temp_images()

    def save_config(self):
        """Save configuration to file"""
        config = {
            'wallpaper_dir': self.wallpaper_dir,
            'active_monitors': self.active_monitors,
            'monitor_allow_all_orientations': self.monitor_allow_all_orientations,
            'monitor_rotation_direction': self.monitor_rotation_direction,
            'rotation_interval': self.rotation_interval,
            'use_image_orientation': self.use_image_orientation,
            'wallpaper_position': self.wallpaper_position,
            'auto_start_rotation': self.auto_start_rotation
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f)

    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.wallpaper_dir = config.get('wallpaper_dir')
                    self.active_monitors = config.get('active_monitors', {})
                    self.monitor_allow_all_orientations = config.get(
                        'monitor_allow_all_orientations', {})
                    self.monitor_rotation_direction = config.get(
                        'monitor_rotation_direction', {})
                    self.rotation_interval = config.get(
                        'rotation_interval', 30)
                    self.use_image_orientation = config.get(
                        'use_image_orientation', True)
                    self.wallpaper_position = config.get(
                        'wallpaper_position', DWPOS_FILL)
                    self.auto_start_rotation = config.get(
                        'auto_start_rotation', False)
        except Exception as e:
            print(f"Error loading config: {e}")


class WallpaperRotatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-Monitor Wallpaper Rotator")
        self.root.geometry("750x700")
        self.rotator = WallpaperRotator()
        self.monitor_checkboxes = []
        self.monitor_orientation_vars = []
        self.rotation_timer_id = None  # Track timer for rotation

        self.tray_icon = None
        self.icon_image = None
        self.is_tray_active = False
        self.tray_check_timer_id = None  # Timer for monitoring tray icon

        # Create a PanedWindow to split controls and status area
        # Using tk.PanedWindow instead of ttk for better sash visibility/draggability
        self.paned_window = tk.PanedWindow(
            self.root,
            orient=tk.VERTICAL,
            sashwidth=8,
            sashrelief=tk.RAISED,
            bg='#d0d0d0'
        )
        self.paned_window.pack(fill='both', expand=True)

        # Create scrollable frame for controls
        controls_container = ttk.Frame(self.paned_window)

        self.main_canvas = tk.Canvas(controls_container, highlightthickness=0)
        self.main_scrollbar = ttk.Scrollbar(
            controls_container, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.main_canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(
                scrollregion=self.main_canvas.bbox("all"))
        )

        self.main_canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)

        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.main_scrollbar.pack(side="right", fill="y")

        # Enable mouse wheel scrolling
        self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Add controls container to paned window
        self.paned_window.add(controls_container, stretch="always")

        self.create_widgets()
        self.update_status()
        self.setup_tray_support()

        # Auto-start rotation if configured
        if self.rotator.auto_start_rotation and self.rotator.wallpaper_dir:
            self.log("Auto-starting rotation on launch...")
            self.root.iconify()  # Minimize window
            # Delay slightly to ensure GUI is ready
            self.root.after(500, self.start_rotation)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def create_widgets(self):
        # Monitor selection with orientation
        monitor_frame = ttk.LabelFrame(
            self.scrollable_frame, text="Monitor Selection", padding=10)
        monitor_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(monitor_frame, text="Configure each monitor's wallpaper settings:").pack(
            anchor='w', pady=5)

        # Create checkbox and orientation dropdown for each monitor
        for monitor in self.rotator.monitors:
            monitor_row = ttk.Frame(monitor_frame)
            monitor_row.pack(fill='x', pady=2)

            # Checkbox for enabling/disabling monitor
            var = tk.BooleanVar(
                value=monitor['id'] in self.rotator.active_monitors)
            checkbox = ttk.Checkbutton(
                monitor_row,
                text=f"Monitor {monitor['index']} - {monitor['orientation']} ({monitor['rect']})",
                variable=var,
                command=lambda m=monitor, v=var: self.on_monitor_toggle(m, v)
            )
            checkbox.pack(side='left', padx=5)

            # Orientation dropdown
            orientation_var = tk.StringVar(
                value=self.rotator.active_monitors.get(
                    monitor['id'], monitor['orientation'])
            )
            orientation_combo = ttk.Combobox(
                monitor_row,
                textvariable=orientation_var,
                values=['Portrait', 'Landscape'],
                state='readonly',
                width=10
            )
            orientation_combo.pack(side='left', padx=5)
            orientation_combo.bind('<<ComboboxSelected>>',
                                   lambda e, m=monitor, v=orientation_var: self.on_orientation_change(m, v))

            # Checkbox for allowing all orientations
            allow_all_var = tk.BooleanVar(
                value=self.rotator.monitor_allow_all_orientations.get(
                    monitor['id'], False)
            )
            allow_all_check = ttk.Checkbutton(
                monitor_row,
                text="All orientations",
                variable=allow_all_var,
                command=lambda m=monitor, v=allow_all_var: self.on_allow_all_orientations_change(
                    m, v)
            )
            allow_all_check.pack(side='left', padx=5)

            # Rotation direction dropdown
            rotation_var = tk.StringVar(
                value=self.rotator.monitor_rotation_direction.get(
                    monitor['id'], 'none')
            )
            ttk.Label(monitor_row, text="Rotate:").pack(
                side='left', padx=(10, 2))
            rotation_combo = ttk.Combobox(
                monitor_row,
                textvariable=rotation_var,
                values=['none', 'left', 'right'],
                state='readonly',
                width=8
            )
            rotation_combo.pack(side='left', padx=2)
            rotation_combo.bind('<<ComboboxSelected>>',
                                lambda e, m=monitor, v=rotation_var: self.on_rotation_direction_change(m, v))

            self.monitor_checkboxes.append(
                (monitor, var, orientation_var, allow_all_var, rotation_var))

            # Set initial state
            if monitor['id'] in self.rotator.active_monitors:
                orientation_var.set(
                    self.rotator.active_monitors[monitor['id']])

        # Directory selection
        dir_frame = ttk.LabelFrame(
            self.scrollable_frame, text="Wallpaper Directory", padding=10)
        dir_frame.pack(fill='x', padx=10, pady=5)

        self.dir_label = ttk.Label(
            dir_frame, text="No directory selected", wraplength=500)
        self.dir_label.pack(anchor='w', pady=5)

        self.image_count_label = ttk.Label(
            dir_frame, text="Images found: 0", foreground="blue")
        self.image_count_label.pack(anchor='w', pady=2)

        ttk.Button(dir_frame, text="Browse Directory",
                   command=self.browse_directory).pack(anchor='w')

        # Rotation interval
        interval_frame = ttk.LabelFrame(
            self.scrollable_frame, text="Rotation Settings", padding=10)
        interval_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(interval_frame, text="Rotation Interval (minutes):").pack(
            anchor='w')

        self.interval_var = tk.IntVar(value=self.rotator.rotation_interval)
        interval_spinbox = ttk.Spinbox(
            interval_frame, from_=1, to=1440, textvariable=self.interval_var, width=10)
        interval_spinbox.pack(anchor='w', pady=5)
        interval_spinbox.bind('<FocusOut>', self.on_interval_change)

        # Image orientation matching option
        self.use_orientation_var = tk.BooleanVar(
            value=self.rotator.use_image_orientation)
        orientation_check = ttk.Checkbutton(
            interval_frame,
            text="Match image orientation to monitor (Portrait images → Portrait monitors)",
            variable=self.use_orientation_var,
            command=self.on_orientation_mode_change
        )
        orientation_check.pack(anchor='w', pady=5)

        # Wallpaper fit/position option
        ttk.Label(interval_frame, text="Wallpaper Fit:").pack(
            anchor='w', pady=(10, 0))

        self.position_var = tk.StringVar()
        position_options = {
            'Fill': DWPOS_FILL,
            'Fit': DWPOS_FIT,
            'Stretch': DWPOS_STRETCH,
            'Center': DWPOS_CENTER,
            'Tile': DWPOS_TILE,
            'Span': DWPOS_SPAN
        }

        # Find current position name
        current_position_name = 'Fill'
        for name, value in position_options.items():
            if value == self.rotator.wallpaper_position:
                current_position_name = name
                break

        self.position_var.set(current_position_name)
        self.position_options = position_options

        position_combo = ttk.Combobox(
            interval_frame,
            textvariable=self.position_var,
            values=list(position_options.keys()),
            state='readonly',
            width=15
        )
        position_combo.pack(anchor='w', pady=5)
        position_combo.bind('<<ComboboxSelected>>', self.on_position_change)

        # Add descriptions for fit options
        fit_desc = ttk.Label(
            interval_frame,
            text="Fill: Crops to fill screen | Fit: Shows entire image | Stretch: May distort",
            font=('TkDefaultFont', 8),
            foreground='gray'
        )
        fit_desc.pack(anchor='w')

        # Add note about Windows Settings
        fit_note = ttk.Label(
            interval_frame,
            text="Note: If this setting doesn't work (Likely in later versions of Windows), manually set 'Choose a fit' in Windows Settings > Personalization > Background",
            font=('TkDefaultFont', 8),
            foreground='orange',
            wraplength=600
        )
        fit_note.pack(anchor='w', pady=(5, 0))

        # Button to open Windows Settings
        ttk.Button(
            interval_frame,
            text="Open Windows Personalization Settings",
            command=self.open_windows_settings
        ).pack(anchor='w', pady=(5, 0))

        # Control buttons
        control_frame = ttk.Frame(self.scrollable_frame, padding=10)
        control_frame.pack(fill='x', padx=10, pady=5)

        self.start_button = ttk.Button(
            control_frame, text="Start Rotation", command=self.start_rotation)
        self.start_button.pack(side='left', padx=5)

        self.stop_button = ttk.Button(
            control_frame, text="Stop Rotation", command=self.stop_rotation, state='disabled')
        self.stop_button.pack(side='left', padx=5)

        ttk.Button(control_frame, text="Change Now",
                   command=self.change_now).pack(side='left', padx=5)

        # Status area in separate pane (resizable by dragging divider)
        status_container = ttk.Frame(self.paned_window)

        status_frame = ttk.LabelFrame(
            status_container, text="Status (Drag divider above to resize)", padding=5)
        status_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Pack scrollbar first (right side) so it's always visible
        scrollbar = ttk.Scrollbar(status_frame)
        scrollbar.pack(side='right', fill='y')

        # Then pack text widget to fill remaining space
        self.status_text = tk.Text(
            status_frame, wrap='word', state='disabled',
            yscrollcommand=scrollbar.set)
        self.status_text.pack(side='left', fill='both', expand=True)

        scrollbar.config(command=self.status_text.yview)

        # Add status container to paned window with minimum height
        self.paned_window.add(status_container, minsize=100, stretch="always")

        # Load saved directory if exists
        if self.rotator.wallpaper_dir and os.path.exists(self.rotator.wallpaper_dir):
            self.dir_label.config(text=self.rotator.wallpaper_dir)
            self.log("Loading saved directory in background...")

            # Load images in background to not freeze startup
            def load_saved():
                count = self.rotator.scan_images(self.rotator.wallpaper_dir)
                self.image_count_label.config(text=f"Images found: {count}")
                self.log(f"Loaded {count} images from saved directory")
                if self.rotator.use_image_orientation:
                    self.log(
                        f"  Portrait: {len(self.rotator.portrait_images)}, Landscape: {len(self.rotator.landscape_images)}")

            # Run in separate thread to avoid blocking
            threading.Thread(target=load_saved, daemon=True).start()

    def on_monitor_toggle(self, monitor, var):
        """Handle monitor checkbox toggle"""
        if var.get():
            # Find the orientation var for this monitor
            for m, v, o in self.monitor_checkboxes:
                if m['id'] == monitor['id']:
                    self.rotator.active_monitors[monitor['id']] = o.get()
                    break
            self.log(
                f"Enabled Monitor {monitor['index']} - {self.rotator.active_monitors[monitor['id']]}")
        else:
            if monitor['id'] in self.rotator.active_monitors:
                del self.rotator.active_monitors[monitor['id']]
            self.log(f"Disabled Monitor {monitor['index']}")

        self.rotator.save_config()

    def on_orientation_change(self, monitor, orientation_var):
        """Handle orientation dropdown change"""
        if monitor['id'] in self.rotator.active_monitors:
            self.rotator.active_monitors[monitor['id']] = orientation_var.get()
            self.log(
                f"Monitor {monitor['index']} orientation set to {orientation_var.get()}")
            self.rotator.save_config()

    def on_allow_all_orientations_change(self, monitor, allow_all_var):
        """Handle allow all orientations checkbox change"""
        self.rotator.monitor_allow_all_orientations[monitor['id']] = allow_all_var.get(
        )
        status = "enabled" if allow_all_var.get() else "disabled"
        self.log(f"Monitor {monitor['index']} all orientations {status}")
        self.rotator.save_config()

    def on_rotation_direction_change(self, monitor, rotation_var):
        """Handle rotation direction dropdown change"""
        self.rotator.monitor_rotation_direction[monitor['id']] = rotation_var.get(
        )
        self.log(
            f"Monitor {monitor['index']} rotation direction set to {rotation_var.get()}")
        self.rotator.save_config()

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.rotator.wallpaper_dir = directory
            self.dir_label.config(text=directory)

            self.log("Scanning images...")
            self.root.update()  # Force UI update

            # Progress callback
            def update_progress(current, total):
                if current % 10 == 0 or current == total - 1:  # Update every 10 images
                    self.log(f"Processing images: {current + 1}/{total}")
                    self.root.update()  # Keep UI responsive

            count = self.rotator.scan_images(directory, update_progress)
            self.image_count_label.config(text=f"Images found: {count}")

            if count > 0:
                self.log(
                    f"Found {count} images in directory and subdirectories")

                if self.rotator.use_image_orientation:
                    self.log(
                        f"  Portrait images: {len(self.rotator.portrait_images)}")
                    self.log(
                        f"  Landscape images: {len(self.rotator.landscape_images)}")

                # Show first few images as examples
                examples = self.rotator.image_files[:5]
                self.log("Example images:")
                for img in examples:
                    self.log(f"  - {os.path.basename(img)}")
                if count > 5:
                    self.log(f"  ... and {count - 5} more")
            else:
                self.log("No images found! Please check the directory.")
                messagebox.showwarning("No Images",
                                       "No image files found in the selected directory.\n\n"
                                       "Supported formats: JPG, JPEG, PNG, BMP, GIF, TIFF")

            self.rotator.save_config()

    def on_interval_change(self, event):
        try:
            interval = self.interval_var.get()
            if interval < 1:
                # Reset to minimum value if invalid
                interval = 1
                self.interval_var.set(interval)
            self.rotator.rotation_interval = interval
            self.rotator.save_config()
            self.log(
                f"Rotation interval set to {self.rotator.rotation_interval} minutes")
        except (ValueError, tk.TclError):
            # If empty or invalid, reset to current value
            self.interval_var.set(self.rotator.rotation_interval)
            self.log("Invalid interval value - keeping current setting")

    def on_orientation_mode_change(self):
        self.rotator.use_image_orientation = self.use_orientation_var.get()
        self.rotator.save_config()

        if self.rotator.use_image_orientation:
            self.log("Enabled: Matching image orientation to monitor orientation")
        else:
            self.log("Disabled: Using all images for all monitors")

        # Re-scan images if directory is already set
        if self.rotator.wallpaper_dir and os.path.exists(self.rotator.wallpaper_dir):
            self.log("Re-scanning images...")
            count = self.rotator.scan_images(self.rotator.wallpaper_dir)
            if self.rotator.use_image_orientation:
                self.log(
                    f"  Portrait images: {len(self.rotator.portrait_images)}")
                self.log(
                    f"  Landscape images: {len(self.rotator.landscape_images)}")

    def on_position_change(self, event):
        position_name = self.position_var.get()
        self.rotator.wallpaper_position = self.position_options[position_name]
        self.rotator.save_config()
        self.log(f"Wallpaper fit mode set to: {position_name}")
        self.log("Click 'Change Now' to apply the new fit mode to wallpapers")

    def open_windows_settings(self):
        """Open Windows Personalization > Background settings"""
        try:
            import subprocess
            subprocess.Popen(
                "start ms-settings:personalization-background", shell=True)
            self.log("Opening Windows Personalization settings...")
        except Exception as e:
            self.log(f"Error opening Windows Settings: {e}")
            messagebox.showerror(
                "Error", f"Could not open Windows Settings:\n{e}")

    def start_rotation(self):
        if not self.rotator.active_monitors:
            messagebox.showerror("Error", "Please select at least one monitor")
            return

        if not self.rotator.image_files:
            messagebox.showerror(
                "Error", "Please select a directory with images")
            return

        self.rotator.rotation_interval = self.interval_var.get()
        self.rotator.start_rotation()
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')

        monitor_list = ", ".join([f"Monitor {m['index']}" for m in self.rotator.monitors
                                  if m['id'] in self.rotator.active_monitors])
        self.log(f"Rotation started on: {monitor_list}")

        # Schedule the next rotation using tkinter's timer (runs in main thread)
        self._schedule_next_rotation()

    def _schedule_next_rotation(self):
        """Schedule the next rotation using tkinter's after() method"""
        if self.rotator.running:
            # Convert minutes to milliseconds
            interval_ms = self.rotator.rotation_interval * 60 * 1000
            self.rotation_timer_id = self.root.after(
                interval_ms, self._do_rotation)

    def _do_rotation(self):
        """Perform rotation and schedule the next one"""
        if self.rotator.running:
            self.log(f"Rotating wallpaper automatically")
            self.rotator.rotate_wallpaper()
            self.log(
                f"Next change in {self.rotator.rotation_interval} minutes")
            # Schedule the next rotation
            self._schedule_next_rotation()

    def stop_rotation(self):
        self.rotator.stop_rotation()

        # Cancel the scheduled timer
        if self.rotation_timer_id is not None:
            self.root.after_cancel(self.rotation_timer_id)
            self.rotation_timer_id = None

        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.log("Rotation stopped")

    def change_now(self):
        if not self.rotator.active_monitors:
            messagebox.showerror("Error", "Please select at least one monitor")
            return

        if not self.rotator.image_files:
            messagebox.showerror(
                "Error", "Please select a directory with images")
            return

        self.rotator.rotate_wallpaper()
        self.log("Wallpaper changed manually on all active monitors")

    def log(self, message):
        self.status_text.config(state='normal')
        self.status_text.insert(
            'end', f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.status_text.see('end')
        self.status_text.config(state='disabled')

    def update_status(self):
        # Update status periodically
        self.root.after(1000, self.update_status)

    def setup_tray_support(self):
        """Setup system tray icon support"""
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        # Bind iconify (minimize) event - use after_idle to check state after event completes
        self.root.bind("<Unmap>", self.check_minimized)

        # Start monitoring tray icon status
        self._monitor_tray_icon()

    def check_minimized(self, event):
        """Check if window was actually minimized (not just unmapped for other reasons)"""
        # Use after_idle to check state after the event has been fully processed
        self.root.after_idle(self._check_if_iconic)

    def _check_if_iconic(self):
        """Check if window is in iconic (minimized) state"""
        try:
            if self.root.state() == 'iconic' and not self.is_tray_active:
                self.show_tray_icon()
                self.root.withdraw()  # Hide from taskbar
        except Exception as e:
            pass  # Silently handle any state checking errors

    def on_close(self):
        """Minimize to tray instead of closing"""
        if not self.is_tray_active:
            self.show_tray_icon()
        self.root.withdraw()  # Hide window completely

    def _monitor_tray_icon(self):
        """Periodically check if tray icon is still active and recreate if needed"""
        try:
            # Only monitor if window is hidden/minimized and should be in tray
            if self.is_tray_active and self.root.state() == 'withdrawn':
                # Check if tray icon exists and is visible
                if self.tray_icon is None or not self.tray_icon.visible:
                    self.log("Tray icon disappeared - recreating...")
                    self.is_tray_active = False
                    self.tray_icon = None
                    self.show_tray_icon()
        except Exception as e:
            # Silently handle any errors during monitoring
            pass

        # Schedule next check in 5 seconds
        self.tray_check_timer_id = self.root.after(
            5000, self._monitor_tray_icon)

    def show_tray_icon(self):
        """Create and show the system tray icon"""
        # Load tray icon image from file if available
        if not self.icon_image:
            # Handle PyInstaller bundled resources
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                base_path = sys._MEIPASS
            else:
                # Running as script
                base_path = os.path.dirname(__file__)

            icon_path = os.path.join(base_path, "MMWP_icon_64x64.png")
            try:
                self.icon_image = Image.open(icon_path)
            except Exception:
                # Fallback: simple colored square
                self.icon_image = Image.new(
                    "RGBA", (64, 64), (80, 120, 200, 255))

        if self.tray_icon is None:
            try:
                # Create menu with restore as default action and rotation toggle
                menu = pystray.Menu(
                    item('Restore', self.restore_window, default=True),
                    pystray.Menu.SEPARATOR,
                    item(
                        'Start Rotation' if not self.rotator.running else 'Stop Rotation',
                        self.toggle_rotation_from_tray,
                        checked=lambda item: self.rotator.running
                    ),
                    item(
                        'Auto-start on Launch',
                        self.toggle_auto_start,
                        checked=lambda item: self.rotator.auto_start_rotation
                    ),
                    pystray.Menu.SEPARATOR,
                    item('Exit', self.exit_app)
                )
                self.tray_icon = pystray.Icon(
                    "WallpaperChanger",
                    self.icon_image,
                    "Wallpaper Changer",
                    menu
                )
                self.is_tray_active = True
                # Start tray icon in separate thread
                threading.Thread(target=self.tray_icon.run,
                                 daemon=True).start()
            except Exception as e:
                # If tray icon fails, log it to the status window
                self.log(f"Error creating tray icon: {e}")

    def toggle_rotation_from_tray(self, icon=None, item=None):
        """Toggle rotation on/off from tray menu"""
        if self.rotator.running:
            self.stop_rotation()
        else:
            self.start_rotation()
        # Update tray menu to reflect new state
        if self.tray_icon:
            self.tray_icon.update_menu()

    def toggle_auto_start(self, icon=None, item=None):
        """Toggle auto-start rotation on launch"""
        self.rotator.auto_start_rotation = not self.rotator.auto_start_rotation
        self.rotator.save_config()
        status = "enabled" if self.rotator.auto_start_rotation else "disabled"
        self.log(f"Auto-start rotation {status}")
        # Update tray menu to reflect new state
        if self.tray_icon:
            self.tray_icon.update_menu()

    def restore_window(self, icon=None, item=None):
        """Restore the window from tray"""
        self.is_tray_active = False
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.deiconify()
        self.root.after(100, self.root.lift)
        self.root.focus_force()

    def exit_app(self, icon=None, item=None):
        """Exit the application"""
        # Cancel tray monitoring timer
        if self.tray_check_timer_id is not None:
            self.root.after_cancel(self.tray_check_timer_id)
            self.tray_check_timer_id = None

        # Clean up temp images on exit
        self.rotator.cleanup_temp_images()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = WallpaperRotatorGUI(root)
    root.mainloop()
