import math

from PIL import Image, ImageOps, ImageTk


DEFAULT_DARKNESS_PERCENT = 30


def load_wallpaper(file_path):
    with Image.open(file_path) as image:
        image.load()
        corrected_image = ImageOps.exif_transpose(image)
        return corrected_image.convert("RGB")


def create_wallpaper_photo(
    image,
    target_width,
    target_height,
    master=None,
    darkness_percent=DEFAULT_DARKNESS_PERCENT,
):
    if target_width <= 0 or target_height <= 0:
        raise ValueError("壁纸目标尺寸必须大于 0")

    darkness_percent = max(0, min(70, int(darkness_percent)))

    scale = max(target_width / image.width, target_height / image.height)
    resized_width = max(target_width, math.ceil(image.width * scale))
    resized_height = max(target_height, math.ceil(image.height * scale))

    resized_image = image.resize(
        (resized_width, resized_height),
        Image.Resampling.LANCZOS,
    )

    left = (resized_width - target_width) // 2
    top = (resized_height - target_height) // 2
    cropped_image = resized_image.crop(
        (left, top, left + target_width, top + target_height)
    )

    display_image = cropped_image.convert("RGBA")
    if darkness_percent > 0:
        dark_overlay = Image.new(
            "RGBA",
            cropped_image.size,
            (0, 0, 0, round(255 * darkness_percent / 100)),
        )
        display_image = Image.alpha_composite(display_image, dark_overlay)

    return ImageTk.PhotoImage(display_image, master=master)
