import asyncio
import time
from collections import deque


class AsyncSlidingWindowCounter:
    def __init__(self, window_seconds: int) -> None:
        self.window = window_seconds
        self.timestamps: deque[float] = deque()
        self.lock = asyncio.Lock()

    async def record_operation(self) -> None:
        now = time.monotonic()
        async with self.lock:
            self.timestamps.append(now)
            self._cleanup(now)

    def _cleanup(self, current_time: float) -> None:
        while self.timestamps and self.timestamps[0] < current_time - self.window:
            self.timestamps.popleft()

    async def get_count(self) -> int:
        now = time.monotonic()
        async with self.lock:
            self._cleanup(now)
            return len(self.timestamps)
