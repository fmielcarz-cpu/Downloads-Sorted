import customtkinter as ctk
import os
import shutil
import time
import math
import threading
import json
import sys
from pathlib import Path

CONFIG_FILE = Path.home() / ".downloadsorter_config.json"

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

ACCENT = "#0A84FF"
ACCENT_SOFT = "#63B3FF"
ACCENT_HOVER = "#0071E3"
DANGER = "#FF453A"
DANGER_HOVER = "#D7342C"
SUCCESS = "#30D158"
SUCCESS_SOFT = "#63E88A"
IDLE_GRAY = ("#8E8E93", "#8E8E93")

CARD_FG = ("#FFFFFF", "#1C1C1E")
CARD_BORDER = ("#E5E5EA", "#2C2C2E")
GLASS_TINT = ("#F7F9FC", "#17181B")
CHIP_FG = ("#F2F2F7", "#2C2C2E")
HOVER_TINT = ("#F2F2F7", "#2C2C2E")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("DownloadSorter")
        self.geometry("760x700")
        self.resizable(False, False)
        self.configure(fg_color=("#EDEFF4", "#000000"))

        self.is_running = False
        self._pulse_job = None
        self._pulse_running = False
        self._pulse_start = 0.0

        self.config_data = {
            "categories": {
                "Photos": [".jpg", ".png", ".jpeg"],
                "Documents": [".pdf", ".txt", ".docx"],
                "Videos": [".mp4", ".mkv", ".avi", ".mov"],
                "Audio": [".mp3", ".wav", ".flac", ".aac"],
                "Zip Files": [".zip", ".rar", ".7z"],
                "Executables": [".exe", ".msi", ".bat"],
                "Others": [".html", ".css", ".js", ".json", ".xml"],
                "Spreadsheets": [".xls", ".xlsx", ".csv"],
            },
            "subfolder_sorting": False,
            "autostart": False
        }

        self.load_config()
        self.categories = self.config_data["categories"]
        self.selected_category = list(self.categories.keys())[0] if self.categories else "Documents"

        try:
            self.attributes("-alpha", 0.0)
        except Exception:
            pass

        self.tabview = ctk.CTkTabview(
            self, width=712, height=640, corner_radius=26,
            fg_color=CARD_FG,
            segmented_button_fg_color=("#EAEAF0", "#232326"),
            segmented_button_selected_color=(ACCENT, ACCENT),
            segmented_button_selected_hover_color=(ACCENT_HOVER, ACCENT_HOVER),
            segmented_button_unselected_color=("#EAEAF0", "#232326"),
            segmented_button_unselected_hover_color=HOVER_TINT,
            text_color=("#FFFFFF", "#FFFFFF"),
            border_width=1,
            border_color=CARD_BORDER,
        )
        self.tabview.pack(padx=24, pady=24)

        self.tab_main = self.tabview.add("  ✳️  Main  ")
        self.tab_settings = self.tabview.add("  🗂️  Categories & Settings  ")


        self.header_frame = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=22, pady=(24, 4))

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="Download Sorter",
            font=ctk.CTkFont(family="SF Pro Display", size=30, weight="bold"),
            text_color=("#1C1C1E", "#F5F5F7"),
        )
        self.title_label.pack(side="left")

        self.status_badge = ctk.CTkLabel(
            self.header_frame,
            text="●  Off",
            text_color=IDLE_GRAY,
            fg_color=("#E9E9EB", "#2C2C2E"),
            corner_radius=20,
            width=100,
            height=32,
            font=ctk.CTkFont(family="SF Pro Text", size=13, weight="bold")
        )
        self.status_badge.pack(side="right")

        self.subtitle_label = ctk.CTkLabel(
            self.tab_main,
            text="Keeps your Downloads folder tidy, automatically.",
            font=ctk.CTkFont(family="SF Pro Text", size=13),
            text_color=("#8E8E93", "#8E8E93"),
        )
        self.subtitle_label.pack(padx=22, anchor="w", pady=(0, 14))

        self.hero_card = ctk.CTkFrame(self.tab_main, corner_radius=24, fg_color=GLASS_TINT,
                                       border_width=2, border_color=CARD_BORDER)
        self.hero_card.pack(fill="x", padx=22, pady=12)

        self.start_button = ctk.CTkButton(
            self.hero_card,
            text="Start Sorting Engine",
            font=ctk.CTkFont(family="SF Pro Text", size=16, weight="bold"),
            height=52,
            corner_radius=26,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self.start_sorting
        )
        self.start_button.pack(fill="x", padx=22, pady=(22, 10))

        self.engine_bar = ctk.CTkProgressBar(
            self.hero_card, height=6, corner_radius=6, mode="indeterminate",
            progress_color=ACCENT, fg_color=("#E5E5EA", "#2C2C2E")
        )
        self.engine_bar.pack(fill="x", padx=22, pady=(0, 22))
        self.engine_bar.set(0)

        self.options_card = ctk.CTkFrame(self.tab_main, corner_radius=24, fg_color=CARD_FG,
                                          border_width=1, border_color=CARD_BORDER)
        self.options_card.pack(fill="x", padx=22, pady=12)

        self.subfolder_var = ctk.BooleanVar(value=self.config_data.get("subfolder_sorting", False))
        self.subfolder_row = ctk.CTkFrame(self.options_card, fg_color="transparent")
        self.subfolder_row.pack(fill="x", padx=18, pady=(16, 8))

        ctk.CTkLabel(
            self.subfolder_row, text="Organize into extension subfolders",
            font=ctk.CTkFont(family="SF Pro Text", size=13, weight="bold"),
            text_color=("#1C1C1E", "#F2F2F7"), anchor="w"
        ).pack(side="left")
        ctk.CTkLabel(
            self.subfolder_row, text="", anchor="w"
        ).pack(side="left")

        self.subfolder_switch = ctk.CTkSwitch(
            self.subfolder_row, text="", variable=self.subfolder_var,
            onvalue=True, offvalue=False, width=46,
            progress_color=ACCENT, button_color="#FFFFFF", button_hover_color="#FFFFFF",
            fg_color=("#D1D1D6", "#3A3A3C"),
            command=self.on_subfolder_change
        )
        self.subfolder_switch.pack(side="right")

        self.subfolder_hint = ctk.CTkLabel(
            self.options_card, text="e.g. Documents/pdf/ instead of one flat folder",
            font=ctk.CTkFont(family="SF Pro Text", size=11),
            text_color=("#8E8E93", "#8E8E93"), anchor="w"
        )
        self.subfolder_hint.pack(fill="x", padx=18, pady=(0, 12))

        self.divider = ctk.CTkFrame(self.options_card, height=1, fg_color=CARD_BORDER)
        self.divider.pack(fill="x", padx=18)

        self.autostart_var = ctk.BooleanVar(value=self.config_data.get("autostart", False))
        self.autostart_row = ctk.CTkFrame(self.options_card, fg_color="transparent")
        self.autostart_row.pack(fill="x", padx=18, pady=(14, 4))

        ctk.CTkLabel(
            self.autostart_row, text="Launch automatically with system startup",
            font=ctk.CTkFont(family="SF Pro Text", size=13, weight="bold"),
            text_color=("#1C1C1E", "#F2F2F7"), anchor="w"
        ).pack(side="left")

        self.autostart_switch = ctk.CTkSwitch(
            self.autostart_row, text="", variable=self.autostart_var,
            onvalue=True, offvalue=False, width=46,
            progress_color=SUCCESS, button_color="#FFFFFF", button_hover_color="#FFFFFF",
            fg_color=("#D1D1D6", "#3A3A3C"),
            command=self.on_autostart_change
        )
        self.autostart_switch.pack(side="right")

        ctk.CTkLabel(
            self.options_card, text="Starts quietly in the background on login",
            font=ctk.CTkFont(family="SF Pro Text", size=11),
            text_color=("#8E8E93", "#8E8E93"), anchor="w"
        ).pack(fill="x", padx=18, pady=(0, 16))

        self.footer_frame = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        self.footer_frame.pack(fill="x", padx=22, pady=18)

        self.info_label = ctk.CTkLabel(
            self.footer_frame,
            text="Closing window (X) keeps the engine active in background.",
            text_color=("#8E8E93", "#8E8E93"),
            font=ctk.CTkFont(family="SF Pro Text", size=12)
        )
        self.info_label.pack(side="left")

        self.exit_button = ctk.CTkButton(
            self.footer_frame,
            text="Quit App",
            width=100,
            height=36,
            font=ctk.CTkFont(family="SF Pro Text", size=13, weight="bold"),
            fg_color=DANGER,
            hover_color=DANGER_HOVER,
            corner_radius=18,
            command=self.exit_app
        )
        self.exit_button.pack(side="right")

        self.setup_settings_ui()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.after(30, self._fade_in)


    def _fade_in(self, alpha=0.0):
        try:
            alpha = min(1.0, alpha + 0.08)
            self.attributes("-alpha", alpha)
            if alpha < 1.0:
                self.after(15, lambda: self._fade_in(alpha))
        except Exception:
            pass

    @staticmethod
    def _hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def _rgb_to_hex(rgb):
        return "#%02x%02x%02x" % tuple(max(0, min(255, c)) for c in rgb)

    def _interp_color(self, c1, c2, t):
        r1, g1, b1 = self._hex_to_rgb(c1)
        r2, g2, b2 = self._hex_to_rgb(c2)
        return self._rgb_to_hex((
            int(r1 + (r2 - r1) * t),
            int(g1 + (g2 - g1) * t),
            int(b1 + (b2 - b1) * t),
        ))

    def _start_running_animation(self):
        self._pulse_running = True
        self._pulse_start = time.time()
        self.engine_bar.start()
        self._animate_pulse()

    def _stop_running_animation(self):
        self._pulse_running = False
        if self._pulse_job:
            try:
                self.after_cancel(self._pulse_job)
            except Exception:
                pass
        self.engine_bar.stop()
        self.engine_bar.set(0)
        self.status_badge.configure(text_color=IDLE_GRAY, fg_color=("#E9E9EB", "#2C2C2E"))
        self.hero_card.configure(border_color=CARD_BORDER)

    def _animate_pulse(self):
        if not self._pulse_running:
            return
        t = (math.sin((time.time() - self._pulse_start) * 3) + 1) / 2  
        dot_color = self._interp_color(SUCCESS, SUCCESS_SOFT, t)
        border_color = self._interp_color(ACCENT, ACCENT_SOFT, t)
        try:
            self.status_badge.configure(text_color=dot_color)
            self.hero_card.configure(border_color=border_color)
        except Exception:
            pass
        self._pulse_job = self.after(40, self._animate_pulse)


    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "categories" in data:
                        self.config_data["categories"] = data["categories"]
                    if "subfolder_sorting" in data:
                        self.config_data["subfolder_sorting"] = data["subfolder_sorting"]
                    if "autostart" in data:
                        self.config_data["autostart"] = data["autostart"]
            except Exception:
                pass

    def save_config(self):
        try:
            self.config_data["categories"] = self.categories
            self.config_data["subfolder_sorting"] = self.subfolder_var.get()
            self.config_data["autostart"] = self.autostart_var.get()
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def on_subfolder_change(self):
        self.save_config()

    def on_autostart_change(self):
        self.save_config()
        self.apply_autostart_registry()

    def apply_autostart_registry(self):
        is_checked = self.autostart_var.get()
        if sys.platform == "win32":
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "DownloadSorter"
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
                if is_checked:
                    script_path = os.path.abspath(sys.argv[0])
                    python_path = sys.executable
                    if script_path.endswith(".py"):
                        command = f'"{python_path}" "{script_path}"'
                    else:
                        command = f'"{script_path}"'
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                    except FileNotFoundError:
                        pass
                winreg.CloseKey(key)
            except Exception:
                pass


    def setup_settings_ui(self):
        self.settings_container = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        self.settings_container.pack(fill="both", expand=True, padx=14, pady=14)

        self.left_frame = ctk.CTkFrame(self.settings_container, width=240, corner_radius=22,
                                        fg_color=CARD_FG,
                                        border_width=1, border_color=CARD_BORDER)
        self.left_frame.pack(side="left", fill="y", padx=(0, 14))

        ctk.CTkLabel(self.left_frame, text="Categories", font=ctk.CTkFont(family="SF Pro Display", size=17, weight="bold"),
                     text_color=("#1C1C1E", "#F5F5F7")).pack(padx=18, pady=(18, 10), anchor="w")

        self.folders_scroll = ctk.CTkScrollableFrame(self.left_frame, width=196, height=280, fg_color="transparent")
        self.folders_scroll.pack(padx=8, pady=5, fill="both", expand=True)

        self.folder_ops_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.folder_ops_frame.pack(padx=14, pady=10, fill="x")

        self.new_folder_entry = ctk.CTkEntry(self.folder_ops_frame, placeholder_text="New category...", height=36,
                                              corner_radius=14, fg_color=CHIP_FG, border_width=0)
        self.new_folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.add_folder_btn = ctk.CTkButton(self.folder_ops_frame, text="+", width=38, height=36, corner_radius=14,
                                             font=ctk.CTkFont(size=16, weight="bold"),
                                             fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.add_folder)
        self.add_folder_btn.pack(side="right")

        self.delete_folder_btn = ctk.CTkButton(self.left_frame, text="Delete Selected", height=36, corner_radius=16,
                                                font=ctk.CTkFont(family="SF Pro Text", size=13, weight="bold"),
                                                fg_color=DANGER, hover_color=DANGER_HOVER, command=self.confirm_delete_folder)
        self.delete_folder_btn.pack(padx=14, pady=(0, 18), fill="x")

        self.right_frame = ctk.CTkFrame(self.settings_container, corner_radius=22,
                                         fg_color=CARD_FG,
                                         border_width=1, border_color=CARD_BORDER)
        self.right_frame.pack(side="right", fill="both", expand=True)

        self.right_title = ctk.CTkLabel(self.right_frame, text="Extensions", font=ctk.CTkFont(family="SF Pro Display", size=17, weight="bold"),
                                         text_color=("#1C1C1E", "#F5F5F7"))
        self.right_title.pack(padx=18, pady=(18, 6), anchor="w")

        self.rename_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.rename_frame.pack(padx=18, pady=6, fill="x")

        self.rename_entry = ctk.CTkEntry(self.rename_frame, height=36, corner_radius=14,
                                          fg_color=CHIP_FG, border_width=0)
        self.rename_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.rename_btn = ctk.CTkButton(self.rename_frame, text="Rename", width=88, height=36, corner_radius=14,
                                         font=ctk.CTkFont(family="SF Pro Text", size=13, weight="bold"),
                                         fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.rename_folder)
        self.rename_btn.pack(side="right")

        self.exts_scroll = ctk.CTkScrollableFrame(self.right_frame, height=200, fg_color="transparent")
        self.exts_scroll.pack(padx=18, pady=6, fill="both", expand=True)

        self.add_ext_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.add_ext_frame.pack(padx=18, pady=18, fill="x")

        self.ext_entry = ctk.CTkEntry(self.add_ext_frame, placeholder_text="e.g. .pdf", height=36, corner_radius=14,
                                       fg_color=CHIP_FG, border_width=0)
        self.ext_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.add_ext_btn = ctk.CTkButton(self.add_ext_frame, text="Add", width=88, height=36, corner_radius=14,
                                          font=ctk.CTkFont(family="SF Pro Text", size=13, weight="bold"),
                                          fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.add_extension)
        self.add_ext_btn.pack(side="right")

        self.refresh_ui()

    def refresh_ui(self):
        for widget in self.folders_scroll.winfo_children():
            widget.destroy()

        for cat in self.categories.keys():
            is_selected = (cat == self.selected_category)
            btn_color = (("#E9F3FF", "#0A2A4D") if is_selected else "transparent")
            text_color = (("#0A84FF", "#4DA3FF") if is_selected else ("#1C1C1E", "#F2F2F7"))

            f_btn = ctk.CTkButton(
                self.folders_scroll,
                text=f"📁  {cat}",
                font=ctk.CTkFont(family="SF Pro Text", size=13, weight="bold" if is_selected else "normal"),
                fg_color=btn_color,
                text_color=text_color,
                hover_color=HOVER_TINT,
                anchor="w",
                corner_radius=14,
                height=38,
                command=lambda c=cat: self.select_category(c)
            )
            f_btn.pack(padx=3, pady=3, fill="x")

        if self.selected_category not in self.categories and self.categories:
            self.selected_category = list(self.categories.keys())[0]

        self.right_title.configure(text=f"Extensions in: {self.selected_category}")

        self.rename_entry.delete(0, "end")
        self.rename_entry.insert(0, self.selected_category)

        for widget in self.exts_scroll.winfo_children():
            widget.destroy()

        if self.selected_category in self.categories:
            for ext in self.categories[self.selected_category]:
                row = ctk.CTkFrame(self.exts_scroll, fg_color=CHIP_FG, corner_radius=16, height=40)
                row.pack(fill="x", pady=4)

                lbl = ctk.CTkLabel(row, text=ext, font=ctk.CTkFont(family="SF Pro Text", size=13, weight="bold"),
                                    text_color=("#1C1C1E", "#F2F2F7"))
                lbl.pack(side="left", padx=16)

                del_btn = ctk.CTkButton(
                    row, text="✕", width=30, height=30, corner_radius=15, fg_color="transparent",
                    text_color=DANGER, hover_color=("#FFE5E3", "#4A2624"),
                    command=lambda e=ext: self.remove_extension(e)
                )
                del_btn.pack(side="right", padx=8)

        self.save_config()

    def select_category(self, cat):
        self.selected_category = cat
        self.refresh_ui()

    def add_folder(self):
        new_name = self.new_folder_entry.get().strip()
        if new_name and new_name not in self.categories:
            self.categories[new_name] = []
            self.selected_category = new_name
            self.new_folder_entry.delete(0, "end")
            self.refresh_ui()

    def rename_folder(self):
        new_name = self.rename_entry.get().strip()
        if not new_name or new_name == self.selected_category:
            return
        if new_name in self.categories:
            return

        self.categories[new_name] = self.categories.pop(self.selected_category)
        self.selected_category = new_name
        self.refresh_ui()

    def confirm_delete_folder(self):
        if len(self.categories) <= 1:
            return

        dialog = ctk.CTkInputDialog(text=f"Are you sure you want to delete folder '{self.selected_category}'?\nType 'YES' to confirm:", title="Delete Folder")
        result = dialog.get_input()

        if result == "YES":
            del self.categories[self.selected_category]
            self.selected_category = list(self.categories.keys())[0]
            self.refresh_ui()

    def add_extension(self):
        ext = self.ext_entry.get().strip().lower()
        if not ext:
            return
        if not ext.startswith("."):
            ext = "." + ext

        if ext not in self.categories[self.selected_category]:
            self.categories[self.selected_category].append(ext)
            self.ext_entry.delete(0, "end")
            self.refresh_ui()

    def remove_extension(self, ext):
        if ext in self.categories[self.selected_category]:
            self.categories[self.selected_category].remove(ext)
            self.refresh_ui()


    def start_sorting(self):
        if not self.is_running:
            self.is_running = True
            self.start_button.configure(text="Stop Sorting Engine", fg_color=DANGER, hover_color=DANGER_HOVER)
            self.status_badge.configure(text="●  Running", text_color=SUCCESS, fg_color=("#E3FBEA", "#0F2A17"))
            self._start_running_animation()

            self.sorting_thread = threading.Thread(target=self.run_sorter, daemon=True)
            self.sorting_thread.start()
        else:
            self.is_running = False
            self.start_button.configure(text="Start Sorting Engine", fg_color=ACCENT, hover_color=ACCENT_HOVER)
            self.status_badge.configure(text="●  Off", text_color=IDLE_GRAY, fg_color=("#E9E9EB", "#2C2C2E"))
            self._stop_running_animation()

    def run_sorter(self):
        downloads_path = str(Path.home() / "Downloads")

        while self.is_running:
            try:
                for file_name in os.listdir(downloads_path):
                    if not self.is_running:
                        break
                    complete_path = os.path.join(downloads_path, file_name)

                    if os.path.isdir(complete_path):
                        continue
                    if file_name.endswith((".crdownload", ".part", ".tmp", ".download")):
                        continue
                    extension = os.path.splitext(file_name)[1].lower()

                    for category, extensions in self.categories.items():
                        if extension in extensions:
                            if self.subfolder_var.get():
                                ext_folder_name = extension.lstrip(".")
                                category_folder = os.path.join(downloads_path, category, ext_folder_name)
                            else:
                                category_folder = os.path.join(downloads_path, category)

                            os.makedirs(category_folder, exist_ok=True)
                            try:
                                shutil.move(complete_path, os.path.join(category_folder, file_name))
                            except Exception:
                                pass
                            break
            except Exception:
                pass

            for _ in range(30):
                if not self.is_running:
                    break
                time.sleep(0.1)

    def on_closing(self):
        self.withdraw()

    def exit_app(self):
        self.is_running = False
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()