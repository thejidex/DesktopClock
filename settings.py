import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from tkinter import ttk


class SettingsWindow:
    def __init__(
        self,
        parent,
        on_theme_change,
        on_wallpaper_change,
        on_wallpaper_clear,
        on_wallpaper_darkness_change,
        on_show_date_change,
        on_show_weekday_change,
        on_show_seconds_change,
        on_mode_change,
        on_desktop_mode_change,
        on_always_on_top_change,
        on_position_window,
    ):
        self.parent = parent
        self.on_theme_change = on_theme_change
        self.on_wallpaper_change = on_wallpaper_change
        self.on_wallpaper_clear = on_wallpaper_clear
        self.on_wallpaper_darkness_change = on_wallpaper_darkness_change
        self.on_show_date_change = on_show_date_change
        self.on_show_weekday_change = on_show_weekday_change
        self.on_show_seconds_change = on_show_seconds_change
        self.on_mode_change = on_mode_change
        self.on_desktop_mode_change = on_desktop_mode_change
        self.on_always_on_top_change = on_always_on_top_change
        self.on_position_window = on_position_window
        self.window = None
        self.selected_theme = tk.StringVar(master=parent, value="dark")
        self.wallpaper_name = tk.StringVar(master=parent, value="未选择壁纸")
        self.wallpaper_darkness = tk.IntVar(master=parent, value=30)
        self.wallpaper_darkness_text = tk.StringVar(
            master=parent,
            value="壁纸暗化程度：30%",
        )
        self.show_date = tk.BooleanVar(master=parent, value=True)
        self.show_weekday = tk.BooleanVar(master=parent, value=True)
        self.show_seconds = tk.BooleanVar(master=parent, value=True)
        self.selected_mode = tk.StringVar(master=parent, value="clock")
        self.desktop_mode = tk.BooleanVar(master=parent, value=False)
        self.always_on_top = tk.BooleanVar(master=parent, value=False)

    def open(
        self,
        current_theme,
        current_wallpaper_path,
        wallpaper_darkness,
        show_date,
        show_weekday,
        show_seconds,
        current_mode,
        desktop_mode,
        always_on_top,
    ):
        self.selected_theme.set(current_theme)
        self.set_current_wallpaper(current_wallpaper_path)
        self.set_wallpaper_darkness(wallpaper_darkness)
        self.set_show_date(show_date)
        self.set_show_weekday(show_weekday)
        self.set_show_seconds(show_seconds)
        self.set_current_mode(current_mode)
        self.set_desktop_mode(desktop_mode)
        self.set_always_on_top(always_on_top)

        if self.window is None or not self.window.winfo_exists():
            self.create_window()

        self.window.deiconify()
        self.window.geometry("430x600")
        self.window.update_idletasks()
        self.on_position_window(self.window)
        self.window.lift()
        self.window.focus_force()

    def is_open(self):
        return self.window is not None and self.window.winfo_exists()

    def create_window(self):
        self.window = tk.Toplevel(self.parent)
        self.window.title("设置")
        self.window.geometry("430x600")
        self.window.resizable(False, False)
        self.window.transient(self.parent)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        notebook = ttk.Notebook(self.window)
        notebook.pack(fill="both", expand=True, padx=18, pady=(18, 10))

        function_tab = tk.Frame(notebook)
        appearance_tab = tk.Frame(notebook)
        window_tab = tk.Frame(notebook)
        notebook.add(function_tab, text="功能")
        notebook.add(appearance_tab, text="外观与显示")
        notebook.add(window_tab, text="窗口")

        function_frame = tk.LabelFrame(
            function_tab,
            text="主窗口模式",
            padx=20,
            pady=14,
        )
        function_frame.pack(fill="x", padx=18, pady=18)

        mode_options = (
            ("时钟", "clock"),
            ("倒计时", "countdown"),
            ("秒表", "stopwatch"),
            ("闹钟", "alarm"),
        )
        for index, (text, mode_name) in enumerate(mode_options):
            option = tk.Radiobutton(
                function_frame,
                text=text,
                value=mode_name,
                variable=self.selected_mode,
                command=self.change_mode,
                anchor="w",
            )
            option.grid(
                row=index // 2,
                column=index % 2,
                sticky="ew",
                padx=(0, 16),
                pady=7,
            )
        function_frame.columnconfigure(0, weight=1)
        function_frame.columnconfigure(1, weight=1)

        mode_help = tk.Label(
            function_tab,
            text="倒计时、秒表和闹钟的操作控件会显示在主窗口底部。\n"
            "也可使用 Ctrl+Shift+1～4 快速切换。",
            justify="left",
            anchor="w",
        )
        mode_help.pack(fill="x", padx=22)

        appearance_frame = tk.LabelFrame(
            appearance_tab,
            text="外观",
            padx=20,
            pady=12,
        )
        appearance_frame.pack(fill="x", padx=18, pady=(18, 10))

        theme_options = (
            ("深色", "dark"),
            ("浅色", "light"),
            ("OLED 黑", "oled"),
        )
        for text, theme_name in theme_options:
            option = tk.Radiobutton(
                appearance_frame,
                text=text,
                value=theme_name,
                variable=self.selected_theme,
                command=self.change_theme,
                anchor="w",
            )
            option.pack(side="left", expand=True, fill="x", pady=3)

        background_frame = tk.LabelFrame(
            appearance_tab,
            text="背景",
            padx=20,
            pady=12,
        )
        background_frame.pack(fill="x", padx=18, pady=(0, 10))

        wallpaper_label = tk.Label(
            background_frame,
            textvariable=self.wallpaper_name,
            anchor="w",
        )
        wallpaper_label.pack(fill="x", pady=(0, 10))

        wallpaper_buttons = tk.Frame(background_frame)
        wallpaper_buttons.pack(fill="x")

        choose_button = tk.Button(
            wallpaper_buttons,
            text="选择壁纸...",
            command=self.choose_wallpaper,
        )
        choose_button.pack(side="left", expand=True, fill="x", padx=(0, 5))

        clear_button = tk.Button(
            wallpaper_buttons,
            text="清除壁纸",
            command=self.clear_wallpaper,
        )
        clear_button.pack(side="left", expand=True, fill="x", padx=(5, 0))

        darkness_label = tk.Label(
            background_frame,
            textvariable=self.wallpaper_darkness_text,
            anchor="w",
        )
        darkness_label.pack(fill="x", pady=(16, 0))

        darkness_scale = tk.Scale(
            background_frame,
            from_=0,
            to=70,
            resolution=1,
            orient="horizontal",
            showvalue=False,
            variable=self.wallpaper_darkness,
            command=self.change_wallpaper_darkness,
        )
        darkness_scale.pack(fill="x")

        display_frame = tk.LabelFrame(
            appearance_tab,
            text="显示",
            padx=20,
            pady=12,
        )
        display_frame.pack(fill="x", padx=18, pady=(0, 18))

        show_date_button = tk.Checkbutton(
            display_frame,
            text="显示日期",
            variable=self.show_date,
            command=self.change_show_date,
            anchor="w",
        )
        show_date_button.pack(fill="x", pady=3)

        show_weekday_button = tk.Checkbutton(
            display_frame,
            text="显示星期",
            variable=self.show_weekday,
            command=self.change_show_weekday,
            anchor="w",
        )
        show_weekday_button.pack(fill="x", pady=3)

        show_seconds_button = tk.Checkbutton(
            display_frame,
            text="显示秒",
            variable=self.show_seconds,
            command=self.change_show_seconds,
            anchor="w",
        )
        show_seconds_button.pack(fill="x", pady=3)

        window_frame = tk.LabelFrame(
            window_tab,
            text="窗口",
            padx=20,
            pady=12,
        )
        window_frame.pack(fill="x", padx=18, pady=18)

        desktop_mode_button = tk.Checkbutton(
            window_frame,
            text="桌面模式",
            variable=self.desktop_mode,
            command=self.change_desktop_mode,
            anchor="w",
        )
        desktop_mode_button.pack(fill="x", pady=3)

        always_on_top_button = tk.Checkbutton(
            window_frame,
            text="始终置顶",
            variable=self.always_on_top,
            command=self.change_always_on_top,
            anchor="w",
        )
        always_on_top_button.pack(fill="x", pady=3)

        close_button = tk.Button(
            self.window,
            text="关闭",
            width=10,
            command=self.close,
        )
        close_button.pack(pady=(0, 14))

    def change_theme(self):
        self.on_theme_change(self.selected_theme.get())

    def set_current_theme(self, theme_name):
        self.selected_theme.set(theme_name)

    def change_wallpaper_darkness(self, value):
        darkness = round(float(value))
        self.wallpaper_darkness_text.set(f"壁纸暗化程度：{darkness}%")
        self.on_wallpaper_darkness_change(darkness)

    def set_wallpaper_darkness(self, value):
        darkness = max(0, min(70, int(value)))
        self.wallpaper_darkness.set(darkness)
        self.wallpaper_darkness_text.set(f"壁纸暗化程度：{darkness}%")

    def change_show_date(self):
        self.on_show_date_change(self.show_date.get())

    def set_show_date(self, value):
        self.show_date.set(bool(value))

    def change_show_weekday(self):
        self.on_show_weekday_change(self.show_weekday.get())

    def set_show_weekday(self, value):
        self.show_weekday.set(bool(value))

    def change_show_seconds(self):
        self.on_show_seconds_change(self.show_seconds.get())

    def set_show_seconds(self, value):
        self.show_seconds.set(bool(value))

    def change_mode(self):
        self.on_mode_change(self.selected_mode.get())

    def set_current_mode(self, mode_name):
        self.selected_mode.set(mode_name)

    def change_desktop_mode(self):
        self.on_desktop_mode_change(self.desktop_mode.get())

    def set_desktop_mode(self, value):
        self.desktop_mode.set(bool(value))

    def change_always_on_top(self):
        self.on_always_on_top_change(self.always_on_top.get())

    def set_always_on_top(self, value):
        self.always_on_top.set(bool(value))

    def choose_wallpaper(self):
        file_path = filedialog.askopenfilename(
            parent=self.window,
            title="选择壁纸",
            filetypes=(
                ("图片文件", "*.png *.jpg *.jpeg *.webp"),
                ("所有文件", "*.*"),
            ),
        )
        if file_path:
            self.on_wallpaper_change(file_path)

    def clear_wallpaper(self):
        self.on_wallpaper_clear()

    def set_current_wallpaper(self, file_path):
        if file_path:
            self.wallpaper_name.set(Path(file_path).name)
        else:
            self.wallpaper_name.set("未选择壁纸")

    def close(self):
        if self.is_open():
            self.window.destroy()
        self.window = None
