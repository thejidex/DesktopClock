import json
import os
import re
import tempfile
from pathlib import Path


DEFAULT_CONFIG = {
    "config_version": 3,
    "theme": "dark",
    "wallpaper": None,
    "wallpaper_darkness": 30,
    "show_date": True,
    "show_weekday": True,
    "show_seconds": True,
    "alarm_enabled": False,
    "alarm_time": "07:30",
    "desktop_mode": False,
    "always_on_top": False,
    "window_geometry": "520x240",
}

DATA_DIRECTORY_ENVIRONMENT_VARIABLE = "DESKTOP_CLOCK_DATA_DIR"
APPLICATION_DIRECTORY_NAME = "DesktopClock"
# 仅用于迁移旧版本配置，不是应用的默认数据目录。
LEGACY_D_DRIVE_CONFIG_PATH = Path(r"D:\DesktopClockData\config.json")
WINDOW_GEOMETRY_PATTERN = re.compile(
    r"^(?P<width>[1-9]\d*)x(?P<height>[1-9]\d*)"
    r"(?:(?P<x>[+-]\d+)(?P<y>[+-]\d+))?$"
)
ALARM_TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def get_absolute_directory(value):
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        directory = Path(value.strip()).expanduser()
    except (OSError, RuntimeError, ValueError):
        return None

    if not directory.is_absolute():
        return None

    return directory


def create_directory(directory):
    try:
        directory.mkdir(parents=True, exist_ok=True)
        return directory.is_dir()
    except (OSError, RuntimeError, ValueError):
        return False


def get_default_data_directory():
    local_app_data = get_absolute_directory(os.environ.get("LOCALAPPDATA"))
    if local_app_data is not None:
        return local_app_data / APPLICATION_DIRECTORY_NAME

    try:
        return Path.home() / "AppData" / "Local" / APPLICATION_DIRECTORY_NAME
    except (OSError, RuntimeError):
        return Path(tempfile.gettempdir()) / APPLICATION_DIRECTORY_NAME


def get_data_directory():
    custom_directory = get_absolute_directory(
        os.environ.get(DATA_DIRECTORY_ENVIRONMENT_VARIABLE)
    )
    if custom_directory is not None and create_directory(custom_directory):
        return custom_directory

    default_directory = get_default_data_directory()
    create_directory(default_directory)
    return default_directory


def parse_window_geometry(value):
    if not isinstance(value, str):
        raise ValueError("无效的窗口 geometry")

    match = WINDOW_GEOMETRY_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError("无效的窗口 geometry")

    width = int(match.group("width"))
    height = int(match.group("height"))
    x = match.group("x")
    y = match.group("y")
    return (
        width,
        height,
        int(x) if x is not None else None,
        int(y) if y is not None else None,
    )


def is_valid_window_geometry(value):
    try:
        width, height, x, y = parse_window_geometry(value)
    except ValueError:
        return False

    if width > 100000 or height > 100000:
        return False
    if x is not None and abs(x) > 2000000000:
        return False
    if y is not None and abs(y) > 2000000000:
        return False
    return True


def is_valid_alarm_time(value):
    return isinstance(value, str) and ALARM_TIME_PATTERN.fullmatch(value) is not None


def get_config_path():
    return get_data_directory() / "config.json"


def get_old_appdata_config_path():
    appdata_root = get_absolute_directory(os.environ.get("APPDATA"))
    if appdata_root is not None:
        return appdata_root / "DesktopClock" / "config.json"

    try:
        fallback_root = Path.home() / "AppData" / "Roaming"
    except (OSError, RuntimeError):
        return None
    return fallback_root / "DesktopClock" / "config.json"


def paths_are_same(first_path, second_path):
    try:
        return first_path.resolve(strict=False) == second_path.resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return first_path == second_path


def migrate_old_config():
    try:
        config_path = get_config_path()
        if config_path.exists():
            return False
    except (OSError, RuntimeError, ValueError):
        return False

    legacy_config_paths = (
        LEGACY_D_DRIVE_CONFIG_PATH,
        get_old_appdata_config_path(),
    )
    for old_config_path in legacy_config_paths:
        try:
            if old_config_path is None:
                continue
            if paths_are_same(config_path, old_config_path):
                continue
            if not old_config_path.is_file():
                continue

            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_bytes(old_config_path.read_bytes())
            return True
        except (OSError, RuntimeError, ValueError):
            continue

    return False


def load_config():
    config = DEFAULT_CONFIG.copy()
    migrate_old_config()
    config_path = get_config_path()

    try:
        saved_config = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return config
    except (OSError, UnicodeError, json.JSONDecodeError):
        return config

    if not isinstance(saved_config, dict):
        return config

    theme = saved_config.get("theme")
    if isinstance(theme, str):
        config["theme"] = theme

    wallpaper = saved_config.get("wallpaper")
    if wallpaper is None or isinstance(wallpaper, str):
        config["wallpaper"] = wallpaper

    wallpaper_darkness = saved_config.get("wallpaper_darkness")
    if isinstance(wallpaper_darkness, int) and not isinstance(
        wallpaper_darkness,
        bool,
    ):
        config["wallpaper_darkness"] = max(0, min(70, wallpaper_darkness))

    show_date = saved_config.get("show_date")
    if isinstance(show_date, bool):
        config["show_date"] = show_date

    show_weekday = saved_config.get("show_weekday")
    if isinstance(show_weekday, bool):
        config["show_weekday"] = show_weekday

    show_seconds = saved_config.get("show_seconds")
    if isinstance(show_seconds, bool):
        config["show_seconds"] = show_seconds

    alarm_time = saved_config.get("alarm_time")
    if is_valid_alarm_time(alarm_time):
        config["alarm_time"] = alarm_time

    alarm_enabled = saved_config.get("alarm_enabled")
    if isinstance(alarm_enabled, bool):
        config["alarm_enabled"] = alarm_enabled and is_valid_alarm_time(alarm_time)

    desktop_mode = saved_config.get("desktop_mode")
    if isinstance(desktop_mode, bool):
        config["desktop_mode"] = desktop_mode

    always_on_top = saved_config.get("always_on_top")
    if isinstance(always_on_top, bool):
        config["always_on_top"] = always_on_top

    window_geometry = saved_config.get("window_geometry")
    if is_valid_window_geometry(window_geometry):
        config["window_geometry"] = window_geometry

    return config


def save_config(config):
    config_to_save = DEFAULT_CONFIG.copy()

    if isinstance(config, dict):
        theme = config.get("theme")
        if isinstance(theme, str):
            config_to_save["theme"] = theme

        wallpaper = config.get("wallpaper")
        if wallpaper is None or isinstance(wallpaper, str):
            config_to_save["wallpaper"] = wallpaper

        wallpaper_darkness = config.get("wallpaper_darkness")
        if isinstance(wallpaper_darkness, int) and not isinstance(
            wallpaper_darkness,
            bool,
        ):
            config_to_save["wallpaper_darkness"] = max(
                0,
                min(70, wallpaper_darkness),
            )

        show_date = config.get("show_date")
        if isinstance(show_date, bool):
            config_to_save["show_date"] = show_date

        show_weekday = config.get("show_weekday")
        if isinstance(show_weekday, bool):
            config_to_save["show_weekday"] = show_weekday

        show_seconds = config.get("show_seconds")
        if isinstance(show_seconds, bool):
            config_to_save["show_seconds"] = show_seconds

        alarm_time = config.get("alarm_time")
        if is_valid_alarm_time(alarm_time):
            config_to_save["alarm_time"] = alarm_time

        alarm_enabled = config.get("alarm_enabled")
        if isinstance(alarm_enabled, bool):
            config_to_save["alarm_enabled"] = (
                alarm_enabled and is_valid_alarm_time(alarm_time)
            )

        desktop_mode = config.get("desktop_mode")
        if isinstance(desktop_mode, bool):
            config_to_save["desktop_mode"] = desktop_mode

        always_on_top = config.get("always_on_top")
        if isinstance(always_on_top, bool):
            config_to_save["always_on_top"] = always_on_top

        window_geometry = config.get("window_geometry")
        if is_valid_window_geometry(window_geometry):
            config_to_save["window_geometry"] = window_geometry

    config_path = get_config_path()
    try:
        config_path.write_text(
            json.dumps(config_to_save, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except (OSError, TypeError, ValueError):
        return False

    return True
