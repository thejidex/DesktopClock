import ctypes
import sys
import tkinter as tk
import winsound
from datetime import datetime
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox
from ctypes import wintypes

from config import DEFAULT_CONFIG, load_config, parse_window_geometry, save_config
from settings import SettingsWindow
from themes import THEMES
from time_tools import (
    CountdownTimer,
    StopwatchTimer,
    format_duration,
    is_alarm_due,
)
from wallpaper import create_wallpaper_photo, load_wallpaper


MONITOR_DEFAULTTONULL = 0
MONITOR_DEFAULTTONEAREST = 2
GA_ROOT = 2
GWL_STYLE = -16
GWL_EXSTYLE = -20
HWND_TOPMOST = wintypes.HWND(-1)
HWND_NOTOPMOST = wintypes.HWND(-2)
WS_SYSMENU = 0x00080000
WS_MINIMIZEBOX = 0x00020000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
SW_HIDE = 0
SW_SHOW = 5
APP_USER_MODEL_ID = "DesktopClock.DesktopClock.1.0"


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent

    return base_path / relative_path


def set_windows_app_user_model_id():
    if sys.platform != "win32":
        return

    try:
        set_app_id = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
        set_app_id.argtypes = (wintypes.LPCWSTR,)
        set_app_id.restype = ctypes.c_long
        set_app_id(APP_USER_MODEL_ID)
    except (AttributeError, OSError, ctypes.ArgumentError):
        pass


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


user32 = ctypes.windll.user32
user32.GetAncestor.argtypes = (wintypes.HWND, wintypes.UINT)
user32.GetAncestor.restype = wintypes.HWND
user32.MonitorFromWindow.argtypes = (wintypes.HWND, wintypes.DWORD)
user32.MonitorFromWindow.restype = wintypes.HMONITOR
user32.GetMonitorInfoW.argtypes = (wintypes.HMONITOR, ctypes.POINTER(MONITORINFO))
user32.GetMonitorInfoW.restype = wintypes.BOOL
user32.GetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int)
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t)
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.IsWindowVisible.argtypes = (wintypes.HWND,)
user32.IsWindowVisible.restype = wintypes.BOOL
user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
user32.ShowWindow.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = (
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
)
user32.SetWindowPos.restype = wintypes.BOOL


def get_window_handle(window):
    window.update_idletasks()
    window_handle = wintypes.HWND(window.winfo_id())
    root_handle = user32.GetAncestor(window_handle, GA_ROOT)
    return root_handle or window_handle


def configure_taskbar_window(window):
    window_handle = get_window_handle(window)
    window_style = user32.GetWindowLongPtrW(window_handle, GWL_STYLE)
    minimizable_style = window_style | WS_SYSMENU | WS_MINIMIZEBOX
    extended_style = user32.GetWindowLongPtrW(window_handle, GWL_EXSTYLE)
    taskbar_style = (
        extended_style & ~WS_EX_TOOLWINDOW
    ) | WS_EX_APPWINDOW

    style_changed = (
        minimizable_style != window_style or taskbar_style != extended_style
    )
    if style_changed:
        was_visible = bool(user32.IsWindowVisible(window_handle))
        if was_visible:
            user32.ShowWindow(window_handle, SW_HIDE)

        try:
            if minimizable_style != window_style:
                previous_style = user32.SetWindowLongPtrW(
                    window_handle,
                    GWL_STYLE,
                    minimizable_style,
                )
                if not previous_style:
                    raise ctypes.WinError()

            if taskbar_style != extended_style:
                previous_style = user32.SetWindowLongPtrW(
                    window_handle,
                    GWL_EXSTYLE,
                    taskbar_style,
                )
                if not previous_style:
                    raise ctypes.WinError()
        finally:
            if was_visible:
                user32.ShowWindow(window_handle, SW_SHOW)

    if not user32.SetWindowPos(
        window_handle,
        wintypes.HWND(0),
        0,
        0,
        0,
        0,
        SWP_NOMOVE
        | SWP_NOSIZE
        | SWP_NOZORDER
        | SWP_NOACTIVATE
        | SWP_FRAMECHANGED
        | SWP_SHOWWINDOW,
    ):
        raise ctypes.WinError()


def get_window_geometry(window):
    x = window.winfo_x()
    y = window.winfo_y()
    x_position = f"+{x}" if x >= 0 else str(x)
    y_position = f"+{y}" if y >= 0 else str(y)
    return (
        f"{window.winfo_width()}x{window.winfo_height()}"
        f"{x_position}{y_position}"
    )


def apply_window_geometry(window, geometry):
    width, height, x, y = parse_window_geometry(geometry)
    window.geometry(f"{width}x{height}")
    window.update_idletasks()

    if x is None or y is None:
        return

    window_handle = get_window_handle(window)
    if not user32.SetWindowPos(
        window_handle,
        wintypes.HWND(0),
        x,
        y,
        0,
        0,
        SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE,
    ):
        raise ctypes.WinError()


def get_monitor_info(window, default_monitor=MONITOR_DEFAULTTONEAREST):
    window_handle = get_window_handle(window)
    monitor = user32.MonitorFromWindow(window_handle, default_monitor)
    if not monitor:
        return None

    monitor_info = MONITORINFO()
    monitor_info.cbSize = ctypes.sizeof(MONITORINFO)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(monitor_info)):
        raise ctypes.WinError()

    return monitor_info


def get_rectangle_bounds(rectangle):
    return (
        rectangle.left,
        rectangle.top,
        rectangle.right - rectangle.left,
        rectangle.bottom - rectangle.top,
    )


def get_monitor_bounds(window):
    monitor_info = get_monitor_info(window)
    return get_rectangle_bounds(monitor_info.rcMonitor)


def get_monitor_work_area(window):
    monitor_info = get_monitor_info(window)
    return get_rectangle_bounds(monitor_info.rcWork)


def is_window_visible_on_a_monitor(window):
    return get_monitor_info(window, MONITOR_DEFAULTTONULL) is not None


def move_window_to_visible_area(window):
    if is_window_visible_on_a_monitor(window):
        return False

    work_left, work_top, work_width, work_height = get_monitor_work_area(window)
    width = min(window.winfo_width(), work_width)
    height = min(window.winfo_height(), work_height)
    new_x = work_left + max(0, (work_width - width) // 2)
    new_y = work_top + max(0, (work_height - height) // 2)

    window_handle = get_window_handle(window)
    if not user32.SetWindowPos(
        window_handle,
        wintypes.HWND(0),
        new_x,
        new_y,
        width,
        height,
        SWP_NOZORDER | SWP_NOACTIVATE,
    ):
        raise ctypes.WinError()

    window.update_idletasks()
    return True


def position_window_near_parent(parent, child):
    child.update_idletasks()
    child_width = child.winfo_width()
    child_height = child.winfo_height()

    work_left, work_top, work_width, work_height = get_monitor_work_area(parent)
    visible_width = min(child_width, work_width)
    visible_height = min(child_height, work_height)
    if visible_width != child_width or visible_height != child_height:
        child.geometry(f"{visible_width}x{visible_height}")
        child.update_idletasks()
        child_width = visible_width
        child_height = visible_height

    parent_center_x = parent.winfo_rootx() + parent.winfo_width() // 2
    parent_center_y = parent.winfo_rooty() + parent.winfo_height() // 2
    ideal_x = parent_center_x - child_width // 2
    ideal_y = parent_center_y - child_height // 2

    maximum_x = max(work_left, work_left + work_width - child_width)
    maximum_y = max(work_top, work_top + work_height - child_height)
    new_x = max(work_left, min(ideal_x, maximum_x))
    new_y = max(work_top, min(ideal_y, maximum_y))

    child_handle = get_window_handle(child)
    if not user32.SetWindowPos(
        child_handle,
        wintypes.HWND(0),
        new_x,
        new_y,
        0,
        0,
        SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE,
    ):
        raise ctypes.WinError()


def main():
    set_windows_app_user_model_id()

    saved_config = load_config()
    saved_theme = saved_config["theme"]
    if saved_theme not in THEMES:
        saved_theme = "dark"

    window = tk.Tk()
    window.title("桌面时钟")
    try:
        icon_path = resource_path("assets/desktop-clock.ico")
        window.iconbitmap(default=str(icon_path))
    except (OSError, tk.TclError):
        pass

    initial_geometry = saved_config["window_geometry"]
    try:
        initial_width, initial_height, _, _ = parse_window_geometry(initial_geometry)
        window.geometry(f"{initial_width}x{initial_height}")
    except (ValueError, tk.TclError):
        initial_geometry = DEFAULT_CONFIG["window_geometry"]
        initial_width, initial_height, _, _ = parse_window_geometry(initial_geometry)
        window.geometry(f"{initial_width}x{initial_height}")
    window.minsize(360, 220)
    is_fullscreen = False
    fullscreen_transition = False
    last_normal_geometry = initial_geometry
    current_theme = saved_theme
    settings_window = None
    wallpaper_original = None
    wallpaper_photo = None
    current_wallpaper_path = None
    wallpaper_resize_job = None
    geometry_save_job = None
    wallpaper_darkness = saved_config["wallpaper_darkness"]
    show_date = saved_config["show_date"]
    show_weekday = saved_config["show_weekday"]
    show_seconds = saved_config["show_seconds"]
    current_mode = "clock"
    alarm_enabled = saved_config["alarm_enabled"]
    alarm_time = saved_config["alarm_time"]
    last_alarm_date = None
    countdown_alert_shown = False
    desktop_mode = saved_config["desktop_mode"]
    always_on_top = saved_config["always_on_top"]
    drag_mouse_x = None
    drag_mouse_y = None
    drag_window_x = None
    drag_window_y = None

    clock_canvas = tk.Canvas(window, borderwidth=0, highlightthickness=0)
    clock_canvas.pack(fill="both", expand=True)

    time_font = tkfont.Font(family="Segoe UI", size=48, weight="normal")
    date_font = tkfont.Font(family="Microsoft YaHei UI", size=13)
    mode_font = tkfont.Font(family="Microsoft YaHei UI", size=13, weight="bold")

    wallpaper_item = clock_canvas.create_image(0, 0, anchor="nw")
    time_item = clock_canvas.create_text(
        0,
        0,
        font=time_font,
        anchor="center",
    )
    date_item = clock_canvas.create_text(
        0,
        0,
        font=date_font,
        anchor="center",
    )
    mode_title_item = clock_canvas.create_text(
        0,
        0,
        font=mode_font,
        anchor="center",
        state="hidden",
    )

    control_frame = None
    control_item = None
    mode_frames = {}
    countdown_timer = CountdownTimer()
    stopwatch_timer = StopwatchTimer()

    countdown_hours = tk.StringVar(master=window, value="00")
    countdown_minutes = tk.StringVar(master=window, value="00")
    countdown_seconds = tk.StringVar(master=window, value="00")
    alarm_hour = tk.StringVar(master=window, value=alarm_time[:2])
    alarm_minute = tk.StringVar(master=window, value=alarm_time[3:])

    weekday_names = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")

    def position_clock_items(width, height):
        center_x = width / 2
        center_y = height / 2

        if current_mode != "clock":
            clock_canvas.coords(mode_title_item, center_x, max(18, height * 0.13))
            clock_canvas.coords(time_item, center_x, height * 0.43)
            if control_item is not None:
                clock_canvas.coords(control_item, center_x, height * 0.76)
            return

        if not show_date:
            clock_canvas.coords(time_item, center_x, center_y)
            return

        time_height = time_font.metrics("linespace")
        date_height = date_font.metrics("linespace")
        gap = max(10, round(date_font.cget("size") * 0.75))

        time_y = center_y - (gap + date_height) / 2
        date_y = center_y + (time_height + gap) / 2

        clock_canvas.coords(time_item, center_x, time_y)
        clock_canvas.coords(date_item, center_x, date_y)

    def save_current_config():
        save_config(
            {
                "theme": current_theme,
                "wallpaper": current_wallpaper_path,
                "wallpaper_darkness": wallpaper_darkness,
                "show_date": show_date,
                "show_weekday": show_weekday,
                "show_seconds": show_seconds,
                "alarm_enabled": alarm_enabled,
                "alarm_time": alarm_time,
                "desktop_mode": desktop_mode,
                "always_on_top": always_on_top,
                "window_geometry": last_normal_geometry,
            }
        )

    def cancel_geometry_save():
        nonlocal geometry_save_job

        if geometry_save_job is not None:
            window.after_cancel(geometry_save_job)
            geometry_save_job = None

    def save_window_geometry():
        nonlocal geometry_save_job, last_normal_geometry

        geometry_save_job = None
        if is_fullscreen or fullscreen_transition or window.state() != "normal":
            return

        last_normal_geometry = get_window_geometry(window)
        save_current_config()

    def schedule_geometry_save():
        nonlocal geometry_save_job

        if is_fullscreen or fullscreen_transition or window.state() != "normal":
            return

        cancel_geometry_save()
        geometry_save_job = window.after(400, save_window_geometry)

    def refresh_taskbar_style(event=None):
        if is_fullscreen or desktop_mode:
            configure_taskbar_window(window)

    def apply_window_style():
        borderless = is_fullscreen or desktop_mode
        window.overrideredirect(borderless)
        window.update_idletasks()
        if borderless:
            configure_taskbar_window(window)
            window.after(0, refresh_taskbar_style)

    def apply_topmost_state():
        window_handle = get_window_handle(window)
        insert_after = HWND_TOPMOST if always_on_top else HWND_NOTOPMOST
        if not user32.SetWindowPos(
            window_handle,
            insert_after,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        ):
            raise ctypes.WinError()

    def set_desktop_mode(value, save_changes=True):
        nonlocal desktop_mode, last_normal_geometry
        nonlocal drag_mouse_x, drag_mouse_y, drag_window_x, drag_window_y

        desktop_mode = bool(value)
        drag_mouse_x = None
        drag_mouse_y = None
        drag_window_x = None
        drag_window_y = None

        if not is_fullscreen:
            if window.winfo_width() <= 1 or window.winfo_height() <= 1:
                current_geometry = last_normal_geometry
            else:
                current_geometry = get_window_geometry(window)
            apply_window_style()
            apply_window_geometry(window, current_geometry)
            last_normal_geometry = get_window_geometry(window)
            apply_topmost_state()

        settings_window.set_desktop_mode(desktop_mode)
        if save_changes:
            save_current_config()

    def set_always_on_top(value, save_changes=True):
        nonlocal always_on_top

        always_on_top = bool(value)
        apply_topmost_state()
        settings_window.set_always_on_top(always_on_top)

        if save_changes:
            save_current_config()

    def apply_control_theme(widget, theme):
        background = theme["background"]
        time_color = theme["time_color"]
        date_color = theme["date_color"]

        if isinstance(widget, tk.Frame):
            widget.configure(bg=background)
        elif isinstance(widget, tk.Label):
            widget.configure(bg=background, fg=date_color)
        elif isinstance(widget, tk.Spinbox):
            widget.configure(
                bg=background,
                fg=time_color,
                buttonbackground=background,
                insertbackground=time_color,
                readonlybackground=background,
            )
        elif isinstance(widget, tk.Button):
            widget.configure(
                bg=background,
                fg=time_color,
                activebackground=date_color,
                activeforeground=background,
            )

        for child in widget.winfo_children():
            apply_control_theme(child, theme)

    def apply_theme(theme_name, save_changes=True):
        nonlocal current_theme

        theme = THEMES[theme_name]
        background = theme["background"]
        current_theme = theme_name

        clock_canvas.configure(bg=background)
        clock_canvas.itemconfigure(time_item, fill=theme["time_color"])
        clock_canvas.itemconfigure(date_item, fill=theme["date_color"])
        clock_canvas.itemconfigure(mode_title_item, fill=theme["date_color"])
        if control_frame is not None:
            apply_control_theme(control_frame, theme)

        if settings_window is not None:
            settings_window.set_current_theme(current_theme)

        if save_changes:
            save_current_config()

    def position_settings_window(settings):
        position_window_near_parent(window, settings)

    def toggle_settings(event=None):
        if settings_window.is_open():
            settings_window.close()
        else:
            settings_window.open(
                current_theme,
                current_wallpaper_path,
                wallpaper_darkness,
                show_date,
                show_weekday,
                show_seconds,
                current_mode,
                desktop_mode,
                always_on_top,
            )
        return "break"

    def start_window_drag(event):
        nonlocal drag_mouse_x, drag_mouse_y, drag_window_x, drag_window_y

        if not desktop_mode or is_fullscreen or fullscreen_transition:
            return

        drag_mouse_x = event.x_root
        drag_mouse_y = event.y_root
        drag_window_x = window.winfo_x()
        drag_window_y = window.winfo_y()

    def drag_window(event):
        nonlocal last_normal_geometry

        if (
            not desktop_mode
            or is_fullscreen
            or fullscreen_transition
            or drag_mouse_x is None
        ):
            return

        new_x = drag_window_x + event.x_root - drag_mouse_x
        new_y = drag_window_y + event.y_root - drag_mouse_y
        window_handle = get_window_handle(window)
        if not user32.SetWindowPos(
            window_handle,
            wintypes.HWND(0),
            new_x,
            new_y,
            0,
            0,
            SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE,
        ):
            raise ctypes.WinError()

        last_normal_geometry = get_window_geometry(window)
        schedule_geometry_save()

    def stop_window_drag(event=None):
        nonlocal drag_mouse_x, drag_mouse_y, drag_window_x, drag_window_y

        drag_mouse_x = None
        drag_mouse_y = None
        drag_window_x = None
        drag_window_y = None

    def update_date_text(current_time=None):
        if current_time is None:
            current_time = datetime.now()

        current_date = current_time.strftime("%Y年%m月%d日")
        if show_weekday:
            weekday = weekday_names[current_time.weekday()]
            current_date = f"{current_date}  {weekday}"

        clock_canvas.itemconfigure(date_item, text=current_date)

    def set_show_date(value, save_changes=True):
        nonlocal show_date

        show_date = bool(value)
        state = "normal" if show_date and current_mode == "clock" else "hidden"
        clock_canvas.itemconfigure(date_item, state=state)
        position_clock_items(
            max(1, clock_canvas.winfo_width()),
            max(1, clock_canvas.winfo_height()),
        )
        settings_window.set_show_date(show_date)

        if save_changes:
            save_current_config()

    def set_show_seconds(value, save_changes=True):
        nonlocal show_seconds

        show_seconds = bool(value)
        settings_window.set_show_seconds(show_seconds)

        if save_changes:
            save_current_config()

    def set_show_weekday(value, save_changes=True):
        nonlocal show_weekday

        show_weekday = bool(value)
        update_date_text()
        settings_window.set_show_weekday(show_weekday)

        if save_changes:
            save_current_config()

    def cancel_wallpaper_resize():
        nonlocal wallpaper_resize_job

        if wallpaper_resize_job is not None:
            window.after_cancel(wallpaper_resize_job)
            wallpaper_resize_job = None

    def show_wallpaper_photo(photo):
        clock_canvas.itemconfigure(wallpaper_item, image=photo)
        clock_canvas.tag_lower(wallpaper_item)

    def render_wallpaper():
        nonlocal wallpaper_photo, wallpaper_resize_job

        wallpaper_resize_job = None
        if wallpaper_original is None:
            return

        try:
            new_photo = create_wallpaper_photo(
                wallpaper_original,
                max(1, clock_canvas.winfo_width()),
                max(1, clock_canvas.winfo_height()),
                master=window,
                darkness_percent=wallpaper_darkness,
            )
        except Exception:
            return

        wallpaper_photo = new_photo
        show_wallpaper_photo(wallpaper_photo)

    def schedule_wallpaper_resize():
        nonlocal wallpaper_resize_job

        if wallpaper_original is None:
            return

        cancel_wallpaper_resize()
        wallpaper_resize_job = window.after(150, render_wallpaper)

    def set_wallpaper_darkness(value):
        nonlocal wallpaper_darkness

        wallpaper_darkness = max(0, min(70, int(value)))
        settings_window.set_wallpaper_darkness(wallpaper_darkness)
        schedule_wallpaper_resize()
        save_current_config()

    def select_wallpaper(file_path, show_error=True, save_changes=True):
        nonlocal wallpaper_original, wallpaper_photo, current_wallpaper_path

        try:
            full_path = str(Path(file_path).expanduser().resolve())
            new_image = load_wallpaper(full_path)
            new_photo = create_wallpaper_photo(
                new_image,
                max(1, clock_canvas.winfo_width()),
                max(1, clock_canvas.winfo_height()),
                master=window,
                darkness_percent=wallpaper_darkness,
            )
        except Exception as error:
            if show_error:
                error_parent = window
                if settings_window is not None and settings_window.window is not None:
                    error_parent = settings_window.window
                messagebox.showerror(
                    "壁纸错误",
                    f"无法打开所选图片。\n\n{error}",
                    parent=error_parent,
                )
            return False

        cancel_wallpaper_resize()
        wallpaper_original = new_image
        wallpaper_photo = new_photo
        current_wallpaper_path = full_path
        show_wallpaper_photo(wallpaper_photo)
        settings_window.set_current_wallpaper(current_wallpaper_path)
        if save_changes:
            save_current_config()
        return True

    def clear_wallpaper():
        nonlocal wallpaper_original, wallpaper_photo, current_wallpaper_path

        cancel_wallpaper_resize()
        clock_canvas.itemconfigure(wallpaper_item, image="")
        wallpaper_original = None
        wallpaper_photo = None
        current_wallpaper_path = None
        apply_theme(current_theme, save_changes=False)
        settings_window.set_current_wallpaper(None)
        save_current_config()

    def enter_fullscreen():
        nonlocal is_fullscreen, fullscreen_transition, last_normal_geometry

        if is_fullscreen:
            fullscreen_transition = False
            return

        stop_window_drag()
        fullscreen_transition = True
        current_state = window.state()
        if current_state == "normal":
            last_normal_geometry = get_window_geometry(window)
        cancel_geometry_save()
        save_current_config()

        monitor_left, monitor_top, monitor_width, monitor_height = get_monitor_bounds(window)
        is_fullscreen = True

        if current_state == "zoomed":
            window.state("normal")
            window.update_idletasks()

        apply_window_style()

        window_handle = get_window_handle(window)
        insert_after = HWND_TOPMOST if always_on_top else HWND_NOTOPMOST
        if not user32.SetWindowPos(
            window_handle,
            insert_after,
            monitor_left,
            monitor_top,
            monitor_width,
            monitor_height,
            SWP_FRAMECHANGED | SWP_SHOWWINDOW,
        ):
            raise ctypes.WinError()

        fullscreen_transition = False
        schedule_wallpaper_resize()

    def toggle_fullscreen(event=None):
        if fullscreen_transition:
            return "break"

        if is_fullscreen:
            exit_fullscreen()
        else:
            enter_fullscreen()
        return "break"

    def exit_fullscreen(event=None):
        nonlocal is_fullscreen, fullscreen_transition

        if not is_fullscreen or fullscreen_transition:
            return "break"

        fullscreen_transition = True
        is_fullscreen = False
        apply_window_style()
        window.state("normal")
        apply_window_geometry(window, last_normal_geometry)

        apply_topmost_state()

        fullscreen_transition = False
        schedule_wallpaper_resize()
        schedule_geometry_save()

    def resize_fonts(event):
        nonlocal fullscreen_transition, last_normal_geometry

        if event.widget != window:
            return

        schedule_wallpaper_resize()

        scale = min(event.width / 520, event.height / 240)
        time_size = max(28, min(140, round(48 * scale)))
        date_size = max(11, min(30, round(13 * scale)))
        time_font.configure(size=time_size)
        date_font.configure(size=date_size)
        mode_font.configure(size=date_size)
        position_clock_items(event.width, event.height)

        if is_fullscreen or fullscreen_transition:
            return

        current_state = window.state()
        if current_state == "normal":
            last_normal_geometry = get_window_geometry(window)
            schedule_geometry_save()
        elif current_state == "zoomed" and not desktop_mode:
            fullscreen_transition = True
            window.after_idle(enter_fullscreen)

    def show_time_tool_error(message):
        messagebox.showerror("时间设置错误", message, parent=window)

    def play_notification(title, message):
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except (AttributeError, OSError, RuntimeError):
            try:
                window.bell()
            except tk.TclError:
                pass

        messagebox.showinfo(title, message, parent=window)

    def get_countdown_input_seconds(show_error=False):
        try:
            hours = int(countdown_hours.get())
            minutes = int(countdown_minutes.get())
            seconds = int(countdown_seconds.get())
        except (TypeError, ValueError):
            if show_error:
                show_time_tool_error("请输入有效的小时、分钟和秒。")
            return None

        if not 0 <= hours <= 99 or not 0 <= minutes <= 59 or not 0 <= seconds <= 59:
            if show_error:
                show_time_tool_error("小时范围是 0～99，分钟和秒范围是 0～59。")
            return None

        total_seconds = hours * 3600 + minutes * 60 + seconds
        if total_seconds <= 0:
            if show_error:
                show_time_tool_error("倒计时时间必须大于 0。")
            return None
        return total_seconds

    def update_countdown_controls():
        state = countdown_timer.state
        running_or_paused = state in ("running", "paused")
        entry_state = "disabled" if running_or_paused or state == "finished" else "normal"
        for entry in countdown_entries:
            entry.configure(state=entry_state)

        countdown_start_button.configure(
            state="normal" if state == "idle" else "disabled"
        )
        countdown_pause_button.configure(
            text="继续" if state == "paused" else "暂停",
            state="normal" if running_or_paused else "disabled",
        )

    def start_countdown():
        nonlocal countdown_alert_shown

        total_seconds = get_countdown_input_seconds(show_error=True)
        if total_seconds is None:
            return

        countdown_timer.start(total_seconds)
        countdown_alert_shown = False
        update_countdown_controls()

    def pause_or_resume_countdown():
        if countdown_timer.state == "running":
            countdown_timer.pause()
        elif countdown_timer.state == "paused":
            countdown_timer.resume()
        update_countdown_controls()

    def reset_countdown():
        nonlocal countdown_alert_shown

        countdown_timer.reset()
        countdown_alert_shown = False
        update_countdown_controls()

    def update_stopwatch_controls():
        state = stopwatch_timer.state
        stopwatch_start_button.configure(
            state="normal" if state == "idle" else "disabled"
        )
        stopwatch_pause_button.configure(
            text="继续" if state == "paused" else "暂停",
            state="normal" if state in ("running", "paused") else "disabled",
        )

    def start_stopwatch():
        stopwatch_timer.start()
        update_stopwatch_controls()

    def pause_or_resume_stopwatch():
        if stopwatch_timer.state == "running":
            stopwatch_timer.pause()
        elif stopwatch_timer.state == "paused":
            stopwatch_timer.start()
        update_stopwatch_controls()

    def reset_stopwatch():
        stopwatch_timer.reset()
        update_stopwatch_controls()

    def get_alarm_input_time(show_error=False):
        try:
            hour = int(alarm_hour.get())
            minute = int(alarm_minute.get())
        except (TypeError, ValueError):
            if show_error:
                show_time_tool_error("请输入有效的闹钟小时和分钟。")
            return None

        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            if show_error:
                show_time_tool_error("闹钟小时范围是 0～23，分钟范围是 0～59。")
            return None
        return f"{hour:02d}:{minute:02d}"

    def update_alarm_controls():
        entry_state = "disabled" if alarm_enabled else "normal"
        for entry in alarm_entries:
            entry.configure(state=entry_state)

        if alarm_enabled:
            alarm_toggle_button.configure(text="关闭闹钟")
            alarm_status_label.configure(text=f"已启用，每天 {alarm_time} 提醒")
        else:
            alarm_toggle_button.configure(text="启用闹钟")
            alarm_status_label.configure(text=f"闹钟已关闭，已保存 {alarm_time}")

    def save_alarm_time(event=None):
        nonlocal alarm_time

        if alarm_enabled:
            return

        new_alarm_time = get_alarm_input_time()
        if new_alarm_time is None or new_alarm_time == alarm_time:
            return

        alarm_time = new_alarm_time
        alarm_hour.set(alarm_time[:2])
        alarm_minute.set(alarm_time[3:])
        update_alarm_controls()
        save_current_config()

    def toggle_alarm():
        nonlocal alarm_enabled, alarm_time

        if alarm_enabled:
            alarm_enabled = False
        else:
            new_alarm_time = get_alarm_input_time(show_error=True)
            if new_alarm_time is None:
                return
            alarm_time = new_alarm_time
            alarm_hour.set(alarm_time[:2])
            alarm_minute.set(alarm_time[3:])
            alarm_enabled = True

        update_alarm_controls()
        save_current_config()

    def check_alarm(current_time):
        nonlocal last_alarm_date

        if not alarm_enabled or not is_alarm_due(
            alarm_time,
            current_time,
            last_alarm_date,
        ):
            return

        today = current_time.date()
        last_alarm_date = today
        window.after_idle(
            lambda: play_notification("闹钟", f"闹钟时间到了：{alarm_time}")
        )

    mode_titles = {
        "countdown": "倒计时",
        "stopwatch": "秒表",
        "alarm": "闹钟",
    }

    def set_mode(mode_name):
        nonlocal current_mode

        if mode_name not in ("clock", "countdown", "stopwatch", "alarm"):
            return "break"

        current_mode = mode_name
        for frame in mode_frames.values():
            frame.pack_forget()

        if current_mode == "clock":
            clock_canvas.itemconfigure(mode_title_item, state="hidden")
            clock_canvas.itemconfigure(control_item, state="hidden")
            clock_canvas.itemconfigure(
                date_item,
                state="normal" if show_date else "hidden",
            )
        else:
            mode_frames[current_mode].pack()
            clock_canvas.itemconfigure(
                mode_title_item,
                text=mode_titles[current_mode],
                state="normal",
            )
            clock_canvas.itemconfigure(control_item, state="normal")
            clock_canvas.itemconfigure(date_item, state="hidden")

        settings_window.set_current_mode(current_mode)
        position_clock_items(
            max(1, clock_canvas.winfo_width()),
            max(1, clock_canvas.winfo_height()),
        )
        return "break"

    control_frame = tk.Frame(clock_canvas, borderwidth=0)

    countdown_frame = tk.Frame(control_frame, borderwidth=0)
    mode_frames["countdown"] = countdown_frame
    countdown_input_frame = tk.Frame(countdown_frame, borderwidth=0)
    countdown_input_frame.pack(pady=(0, 7))
    countdown_entries = []
    for index, (variable, maximum) in enumerate(
        (
            (countdown_hours, 99),
            (countdown_minutes, 59),
            (countdown_seconds, 59),
        )
    ):
        entry = tk.Spinbox(
            countdown_input_frame,
            from_=0,
            to=maximum,
            width=3,
            justify="center",
            textvariable=variable,
            wrap=True,
        )
        entry.pack(side="left")
        countdown_entries.append(entry)
        if index < 2:
            tk.Label(countdown_input_frame, text=" : ").pack(side="left")

    countdown_button_frame = tk.Frame(countdown_frame, borderwidth=0)
    countdown_button_frame.pack()
    countdown_start_button = tk.Button(
        countdown_button_frame,
        text="开始",
        width=6,
        command=start_countdown,
    )
    countdown_start_button.pack(side="left", padx=4)
    countdown_pause_button = tk.Button(
        countdown_button_frame,
        text="暂停",
        width=6,
        command=pause_or_resume_countdown,
    )
    countdown_pause_button.pack(side="left", padx=4)
    tk.Button(
        countdown_button_frame,
        text="重置",
        width=6,
        command=reset_countdown,
    ).pack(side="left", padx=4)

    stopwatch_frame = tk.Frame(control_frame, borderwidth=0)
    mode_frames["stopwatch"] = stopwatch_frame
    stopwatch_start_button = tk.Button(
        stopwatch_frame,
        text="开始",
        width=7,
        command=start_stopwatch,
    )
    stopwatch_start_button.pack(side="left", padx=5)
    stopwatch_pause_button = tk.Button(
        stopwatch_frame,
        text="暂停",
        width=7,
        command=pause_or_resume_stopwatch,
    )
    stopwatch_pause_button.pack(side="left", padx=5)
    tk.Button(
        stopwatch_frame,
        text="重置",
        width=7,
        command=reset_stopwatch,
    ).pack(side="left", padx=5)

    alarm_frame = tk.Frame(control_frame, borderwidth=0)
    mode_frames["alarm"] = alarm_frame
    alarm_input_frame = tk.Frame(alarm_frame, borderwidth=0)
    alarm_input_frame.pack(pady=(0, 6))
    alarm_entries = []
    for index, (variable, maximum) in enumerate(
        ((alarm_hour, 23), (alarm_minute, 59))
    ):
        entry = tk.Spinbox(
            alarm_input_frame,
            from_=0,
            to=maximum,
            width=3,
            justify="center",
            textvariable=variable,
            wrap=True,
        )
        entry.pack(side="left")
        alarm_entries.append(entry)
        entry.bind("<FocusOut>", save_alarm_time)
        entry.bind("<Return>", save_alarm_time)
        if index == 0:
            tk.Label(alarm_input_frame, text=" : ").pack(side="left")
    alarm_toggle_button = tk.Button(
        alarm_input_frame,
        text="启用闹钟",
        width=10,
        command=toggle_alarm,
    )
    alarm_toggle_button.pack(side="left", padx=(12, 0))
    alarm_status_label = tk.Label(alarm_frame, text="", anchor="center")
    alarm_status_label.pack()

    control_item = clock_canvas.create_window(
        0,
        0,
        window=control_frame,
        anchor="center",
        state="hidden",
    )
    update_countdown_controls()
    update_stopwatch_controls()
    update_alarm_controls()

    def update_time():
        nonlocal countdown_alert_shown

        current_time = datetime.now()
        countdown_remaining = countdown_timer.remaining_seconds()
        if countdown_timer.state == "finished" and not countdown_alert_shown:
            countdown_alert_shown = True
            update_countdown_controls()
            window.after_idle(
                lambda: play_notification("倒计时", "倒计时结束")
            )

        check_alarm(current_time)

        if current_mode == "clock":
            time_format = "%H:%M:%S" if show_seconds else "%H:%M"
            time_text = current_time.strftime(time_format)
            update_date_text(current_time)
        elif current_mode == "countdown":
            if countdown_timer.state == "idle":
                input_seconds = get_countdown_input_seconds()
                countdown_remaining = input_seconds or 0
            time_text = format_duration(countdown_remaining)
        elif current_mode == "stopwatch":
            time_text = format_duration(stopwatch_timer.elapsed_seconds())
        else:
            time_text = alarm_time

        time_text = time_text.replace(":", "\u2009:\u2009")
        clock_canvas.itemconfigure(time_item, text=time_text)
        window.after(100, update_time)

    def handle_double_click(event):
        stop_window_drag()
        return toggle_fullscreen(event)

    settings_window = SettingsWindow(
        window,
        apply_theme,
        select_wallpaper,
        clear_wallpaper,
        set_wallpaper_darkness,
        set_show_date,
        set_show_weekday,
        set_show_seconds,
        set_mode,
        set_desktop_mode,
        set_always_on_top,
        position_settings_window,
    )

    window.bind("<Configure>", resize_fonts)
    window.bind("<Map>", refresh_taskbar_style)
    clock_canvas.bind("<ButtonPress-1>", start_window_drag)
    clock_canvas.bind("<B1-Motion>", drag_window)
    clock_canvas.bind("<ButtonRelease-1>", stop_window_drag)
    clock_canvas.bind("<Double-Button-1>", handle_double_click)
    clock_canvas.bind("<Button-3>", toggle_settings)
    window.bind_all("<F11>", toggle_fullscreen)
    window.bind_all("<Escape>", exit_fullscreen)
    window.bind_all("<Control-Key-1>", lambda event: apply_theme("dark"))
    window.bind_all("<Control-Key-2>", lambda event: apply_theme("light"))
    window.bind_all("<Control-Key-3>", lambda event: apply_theme("oled"))
    window.bind_all("<Control-Shift-Key-1>", lambda event: set_mode("clock"))
    window.bind_all("<Control-Shift-Key-2>", lambda event: set_mode("countdown"))
    window.bind_all("<Control-Shift-Key-3>", lambda event: set_mode("stopwatch"))
    window.bind_all("<Control-Shift-Key-4>", lambda event: set_mode("alarm"))
    window.bind_all("<Control-Key-s>", toggle_settings)
    apply_theme(saved_theme, save_changes=False)
    set_show_date(show_date, save_changes=False)
    set_show_weekday(show_weekday, save_changes=False)
    set_show_seconds(show_seconds, save_changes=False)
    set_mode("clock")
    set_desktop_mode(desktop_mode, save_changes=False)
    set_always_on_top(always_on_top, save_changes=False)
    position_clock_items(520, 240)
    window.update_idletasks()
    move_window_to_visible_area(window)
    last_normal_geometry = get_window_geometry(window)
    save_current_config()
    saved_wallpaper = saved_config["wallpaper"]
    if saved_wallpaper is not None:
        restored = select_wallpaper(
            saved_wallpaper,
            show_error=False,
            save_changes=False,
        )
        if not restored:
            save_current_config()
    update_time()
    window.mainloop()


if __name__ == "__main__":
    main()
