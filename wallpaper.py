import math
import threading
import time

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


class VideoWallpaper:
    """Decode video off the Tk thread; draw the newest frame on the clock Canvas."""

    def __init__(self, window, canvas, image_item, on_error):
        self.window = window
        self.canvas = canvas
        self.image_item = image_item
        self.on_error = on_error
        self.thread = None
        self.stop_event = None
        self.poll_job = None
        self.lock = threading.Lock()
        self.frame = None
        self.error = None
        self.photo = None
        self.size = (1, 1)
        self.darkness = DEFAULT_DARKNESS_PERCENT

    def start(self, path, darkness):
        import av
        from av.codec.hwaccel import HWAccel

        # Check the selected file before stopping an existing wallpaper.
        with av.open(path) as container:
            if not container.streams.video:
                raise ValueError("文件中没有视频轨道")
            stream = container.streams.video[0]
            high_resolution = stream.width > 1920 or stream.height > 1080

        hardware_device = None
        if high_resolution:
            for device in ("d3d12va", "d3d11va", "dxva2"):
                try:
                    with av.open(
                        path, hwaccel=HWAccel(device, allow_software_fallback=False)
                    ) as container:
                        if next(container.decode(video=0), None) is not None:
                            hardware_device = device
                            break
                except (OSError, RuntimeError, ValueError):
                    continue
        if hardware_device is None:
            with av.open(path) as container:
                if next(container.decode(video=0), None) is None:
                    raise ValueError("无法解码视频画面")

        self.stop()
        self.darkness = darkness
        self.size = (max(1, self.canvas.winfo_width()),
                     max(1, self.canvas.winfo_height()))
        self.stop_event = threading.Event()
        self.thread = threading.Thread(
            target=self._decode,
            args=(path, self.stop_event, hardware_device), daemon=True,
        )
        self.thread.start()
        self._poll()

    def resize(self, width, height):
        self.size = (max(1, width), max(1, height))

    def set_darkness(self, darkness):
        self.darkness = darkness

    def stop(self):
        if self.poll_job is not None:
            self.window.after_cancel(self.poll_job)
            self.poll_job = None
        if self.stop_event is not None:
            self.stop_event.set()
        if self.thread is not None:
            self.thread.join()
        self.thread = None
        self.stop_event = None
        with self.lock:
            self.frame = None
            self.error = None
        self.photo = None
        self.canvas.itemconfigure(self.image_item, image="")

    def _decode(self, path, stop_event, hardware_device):
        try:
            import av
            from av.codec.hwaccel import HWAccel

            while not stop_event.is_set():
                frame_count = 0
                acceleration = (
                    HWAccel(hardware_device, allow_software_fallback=False)
                    if hardware_device else None
                )
                with av.open(path, hwaccel=acceleration) as container:
                    stream = container.streams.video[0]
                    stream.thread_type = "AUTO"
                    if hardware_device:
                        stream.thread_count = 4
                    rate = float(stream.average_rate) if stream.average_rate else 30.0
                    rate = max(1.0, min(rate, 120.0))
                    first_time = None
                    started = time.monotonic()
                    last_draw = -1.0
                    last_draw_clock = -1.0
                    for frame in container.decode(stream):
                        if stop_event.is_set():
                            return
                        frame_count += 1
                        frame_time = frame.time
                        if frame_time is None:
                            frame_time = (frame_count - 1) / rate
                        if first_time is None:
                            first_time = frame_time
                        target = max(0.0, frame_time - first_time)
                        delay = started + target - time.monotonic()
                        if delay < -1.0:
                            # Recover if decoding itself cannot keep up.
                            started = time.monotonic() - target
                            delay = 0
                        elif delay > 0.25:
                            # Some files contain large timestamp gaps.
                            started = time.monotonic() - target + 0.25
                            delay = 0.25
                        if delay > 0 and stop_event.wait(delay):
                            return
                        # Decode every frame, but limit expensive resizing/Tk updates.
                        now = time.monotonic()
                        if (target - last_draw < 1 / 30 - 0.002 or
                                now - last_draw_clock < 1 / 30 - 0.002):
                            continue
                        last_draw = target
                        last_draw_clock = now
                        size = self.size
                        darkness = self.darkness
                        photo_source = create_video_wallpaper_image(
                            frame, *size, darkness
                        )
                        with self.lock:
                            self.frame = photo_source
                if frame_count == 0:
                    raise ValueError("视频没有可播放的画面")
                # Reopen at EOF for a silent loop; no audio stream is decoded.
                if stop_event.wait(0.03):
                    return
        except Exception as error:
            if not stop_event.is_set():
                with self.lock:
                    self.error = str(error)

    def _poll(self):
        with self.lock:
            frame = self.frame
            error = self.error
            self.frame = None
            self.error = None
        if error is not None:
            self.stop()
            self.on_error(error)
            return
        if frame is not None:
            if self.photo is not None and (
                self.photo.width(), self.photo.height()
            ) == frame.size:
                self.photo.paste(frame)
            else:
                self.photo = ImageTk.PhotoImage(frame, master=self.window)
                self.canvas.itemconfigure(self.image_item, image=self.photo)
                self.canvas.tag_lower(self.image_item)
        self.poll_job = self.window.after(8, self._poll)


def create_video_wallpaper_image(frame, target_width, target_height, darkness_percent):
    """Scale in FFmpeg before converting to a PIL image."""
    scale = max(target_width / frame.width, target_height / frame.height)
    width = max(target_width, math.ceil(frame.width * scale))
    height = max(target_height, math.ceil(frame.height * scale))
    image = frame.reformat(width=width, height=height, format="rgb24").to_image()
    left = (width - target_width) // 2
    top = (height - target_height) // 2
    image = image.crop((left, top, left + target_width, top + target_height))
    if darkness_percent:
        brightness = 1 - darkness_percent / 100
        color_table = [round(value * brightness) for value in range(256)] * 3
        image = image.point(color_table)
    return image
