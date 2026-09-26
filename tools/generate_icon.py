"""Draw crisp clock icons at each Windows taskbar size (requires Pillow)."""

import io
import struct
from pathlib import Path

from PIL import Image, ImageDraw


def draw_clock(size):
    # Render each size separately so small icons keep bold, readable details.
    scale = 4
    image = Image.new("RGBA", (size * scale, size * scale))
    draw = ImageDraw.Draw(image)

    def box(values):
        return tuple(round(value * size * scale) for value in values)

    draw.rounded_rectangle(
        box((0.035, 0.035, 0.965, 0.965)),
        radius=round(size * scale * 0.20),
        fill="#f3eee3",
        outline="#bcb4a4",
        width=max(scale, round(size * scale * 0.025)),
    )
    draw.ellipse(box((0.14, 0.14, 0.86, 0.86)), fill="#fffcf5",
                 outline="#c7bead", width=max(scale, round(size * scale * 0.02)))

    def line(points, color, width):
        pixels = [box(point) for point in points]
        thickness = max(scale, round(size * scale * width))
        draw.line(pixels, fill=color, width=thickness)
        radius = thickness / 2
        for x, y in pixels:
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

    for points in (
        ((0.5, 0.205), (0.5, 0.255)),
        ((0.5, 0.745), (0.5, 0.795)),
        ((0.205, 0.5), (0.255, 0.5)),
        ((0.745, 0.5), (0.795, 0.5)),
    ):
        line(points, "#373b38", 0.045)
    line(((0.5, 0.5), (0.305, 0.355)), "#292e2d", 0.06)
    line(((0.5, 0.5), (0.715, 0.335)), "#292e2d", 0.055)
    line(((0.5, 0.5), (0.5, 0.705)), "#e96616", 0.028)
    draw.ellipse(box((0.455, 0.455, 0.545, 0.545)), fill="#ef7419")
    return image.resize((size, size), Image.Resampling.LANCZOS)


def main():
    sizes = (16, 20, 24, 28, 32, 40, 48, 64, 96, 128, 256)
    frames = []
    for size in sizes:
        stream = io.BytesIO()
        # Tk's Windows icon loader needs classic bitmap frames at small sizes.
        draw_clock(size).save(stream, format="ICO", sizes=[(size, size)],
                              bitmap_format="bmp")
        frames.append(stream.getvalue()[22:])

    # Store independently drawn frames, rather than resizing one large bitmap.
    output = bytearray(struct.pack("<HHH", 0, 1, len(sizes)))
    offset = 6 + 16 * len(sizes)
    for size, frame in zip(sizes, frames):
        dimension = 0 if size == 256 else size
        output.extend(struct.pack("<BBBBHHII", dimension, dimension, 0, 0,
                                  1, 32, len(frame), offset))
        offset += len(frame)
    output.extend(b"".join(frames))
    icon_path = Path(__file__).resolve().parents[1] / "assets" / "desktop-clock.ico"
    icon_path.write_bytes(output)
    print(f"Generated {icon_path}")


if __name__ == "__main__":
    main()
