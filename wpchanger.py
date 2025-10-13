import os
import sys
import time
import random
from pathlib import Path
from ctypes import windll, c_wchar_p, c_uint, Structure, POINTER, byref, c_int
from ctypes.wintypes import UINT, RECT
import comtypes.client
from comtypes import GUID, COMMETHOD
from comtypes.hresult import S_OK
import win32api
import win32con
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
from PIL import Image

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
            # Set the position/fit mode FIRST (this is global)
            self.desktop_wallpaper.SetPosition(self.wallpaper_position)
            # Then set the wallpaper
            self.desktop_wallpaper.SetWallpaper(monitor_id, abs_path)
            return True
        except Exception as e:
            print(f"Error setting wallpaper: {e}")
            import traceback
            traceback.print_exc()
            return False

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

        # Shuffle both lists
        random.shuffle(self.image_files)
        random.shuffle(self.portrait_images)
        random.shuffle(self.landscape_images)

        # Reset indices for all monitors
        self.monitor_indices = {
            monitor_id: 0 for monitor_id in self.active_monitors.keys()}
        return len(self.image_files)

    def rotate_wallpaper(self):
        """Rotate to next wallpaper for all active monitors"""
        if not self.image_files or not self.active_monitors:
            return False

        success = True
        for monitor_id, orientation in self.active_monitors.items():
            if monitor_id not in self.monitor_indices:
                self.monitor_indices[monitor_id] = 0

            # Select appropriate image list based on mode
            if self.use_image_orientation:
                # Match image orientation to monitor orientation
                if orientation == 'Portrait':
                    image_list = self.portrait_images if self.portrait_images else self.image_files
                else:
                    image_list = self.landscape_images if self.landscape_images else self.image_files
            else:
                # Use all images regardless of orientation
                image_list = self.image_files

            if not image_list:
                continue

            index = self.monitor_indices[monitor_id]
            # Make sure index is within bounds
            index = index % len(image_list)
            image_path = image_list[index]

            if self.set_wallpaper(monitor_id, image_path):
                self.monitor_indices[monitor_id] = (
                    index + 1) % len(image_list)
                print(
                    f"Changed wallpaper on {orientation} monitor to: {os.path.basename(image_path)}")
            else:
                success = False

        return success

    def rotation_loop(self):
        """Background thread for rotating wallpapers"""
        while self.running:
            self.rotate_wallpaper()
            # Sleep in small intervals to allow for quick stopping
            for _ in range(self.rotation_interval * 60):
                if not self.running:
                    break
                time.sleep(1)

    def start_rotation(self):
        """Start the rotation thread"""
        if not self.running:
            self.running = True
            self.rotation_thread = threading.Thread(
                target=self.rotation_loop, daemon=True)
            self.rotation_thread.start()

    def stop_rotation(self):
        """Stop the rotation thread"""
        self.running = False
        if self.rotation_thread:
            self.rotation_thread.join(timeout=2)

    def save_config(self):
        """Save configuration to file"""
        config = {
            'wallpaper_dir': self.wallpaper_dir,
            'active_monitors': self.active_monitors,
            'rotation_interval': self.rotation_interval,
            'use_image_orientation': self.use_image_orientation,
            'wallpaper_position': self.wallpaper_position
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
                    self.rotation_interval = config.get(
                        'rotation_interval', 30)
                    self.use_image_orientation = config.get(
                        'use_image_orientation', True)
                    self.wallpaper_position = config.get(
                        'wallpaper_position', DWPOS_FILL)
        except Exception as e:
            print(f"Error loading config: {e}")


class WallpaperRotatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-Monitor Wallpaper Rotator")
        self.root.geometry("700x600")
        self.rotator = WallpaperRotator()
        self.monitor_checkboxes = []
        self.monitor_orientation_vars = []

        self.create_widgets()
        self.update_status()

    def create_widgets(self):
        # Monitor selection with orientation
        monitor_frame = ttk.LabelFrame(
            self.root, text="Monitor Selection", padding=10)
        monitor_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(monitor_frame, text="Select monitors to rotate and specify their orientation:").pack(
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

            self.monitor_checkboxes.append((monitor, var, orientation_var))

            # Set initial state
            if monitor['id'] in self.rotator.active_monitors:
                orientation_var.set(
                    self.rotator.active_monitors[monitor['id']])

        # Directory selection
        dir_frame = ttk.LabelFrame(
            self.root, text="Wallpaper Directory", padding=10)
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
            self.root, text="Rotation Settings", padding=10)
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

        # Control buttons
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(fill='x', padx=10, pady=5)

        self.start_button = ttk.Button(
            control_frame, text="Start Rotation", command=self.start_rotation)
        self.start_button.pack(side='left', padx=5)

        self.stop_button = ttk.Button(
            control_frame, text="Stop Rotation", command=self.stop_rotation, state='disabled')
        self.stop_button.pack(side='left', padx=5)

        ttk.Button(control_frame, text="Change Now",
                   command=self.change_now).pack(side='left', padx=5)

        # Status
        status_frame = ttk.LabelFrame(self.root, text="Status", padding=10)
        status_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.status_text = tk.Text(
            status_frame, height=10, wrap='word', state='disabled')
        self.status_text.pack(fill='both', expand=True)

        scrollbar = ttk.Scrollbar(
            self.status_text, command=self.status_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.status_text['yscrollcommand'] = scrollbar.set

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
        self.rotator.rotation_interval = self.interval_var.get()
        self.rotator.save_config()
        self.log(
            f"Rotation interval set to {self.rotator.rotation_interval} minutes")

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

    def stop_rotation(self):
        self.rotator.stop_rotation()
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


if __name__ == '__main__':
    root = tk.Tk()
    app = WallpaperRotatorGUI(root)
    root.mainloop()
