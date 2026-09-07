import math
import time


def format_duration(total_seconds):
    total_seconds = max(0, int(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def is_alarm_due(alarm_time, current_time, last_trigger_date):
    return (
        current_time.strftime("%H:%M") == alarm_time
        and current_time.date() != last_trigger_date
    )


class CountdownTimer:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.original_seconds = 0
        self.paused_seconds = 0.0
        self.end_time = None
        self.state = "idle"

    def start(self, total_seconds):
        total_seconds = int(total_seconds)
        if total_seconds <= 0:
            raise ValueError("倒计时时间必须大于 0")

        self.original_seconds = total_seconds
        self.paused_seconds = float(total_seconds)
        self.end_time = self.clock() + total_seconds
        self.state = "running"

    def pause(self):
        if self.state != "running":
            return

        self.paused_seconds = max(0.0, self.end_time - self.clock())
        self.end_time = None
        self.state = "paused"

    def resume(self):
        if self.state != "paused" or self.paused_seconds <= 0:
            return

        self.end_time = self.clock() + self.paused_seconds
        self.state = "running"

    def reset(self):
        self.paused_seconds = float(self.original_seconds)
        self.end_time = None
        self.state = "idle"

    def remaining_seconds(self):
        if self.state == "running":
            remaining = self.end_time - self.clock()
            if remaining <= 0:
                self.paused_seconds = 0.0
                self.end_time = None
                self.state = "finished"
                return 0
            return math.ceil(remaining)

        return math.ceil(max(0.0, self.paused_seconds))


class StopwatchTimer:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.elapsed_before_start = 0.0
        self.started_at = None
        self.state = "idle"

    def start(self):
        if self.state == "running":
            return

        self.started_at = self.clock()
        self.state = "running"

    def pause(self):
        if self.state != "running":
            return

        self.elapsed_before_start += self.clock() - self.started_at
        self.started_at = None
        self.state = "paused"

    def reset(self):
        self.elapsed_before_start = 0.0
        self.started_at = None
        self.state = "idle"

    def elapsed_seconds(self):
        elapsed = self.elapsed_before_start
        if self.state == "running":
            elapsed += self.clock() - self.started_at
        return max(0, int(elapsed))
