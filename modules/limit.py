from time import time, sleep
from threading import Lock
from typing import Callable, TypeVar

_R = TypeVar('_R')

class ChronAmRateLimiter:
    """This object keeps track of rate limits for the [loc.gov newspaper API](https://libraryofcongress.github.io/data-exploration/loc.gov%20JSON%20API/Chronicling_America/README.html#rate-limits).

    Attributes:
        burst_times (list[float])        : a list of request timestamps, oldest first; ensures compliance with burst limit.
        crawl_times (list[float])        : a list of request timestamps, oldest first; ensures compliance with crawl limit.
        burst_lock  (Lock)               : provisions access to `burst_times`.
        crawl_lock  (Lock)               : provisions access to `crawl_times`.
    """

    BURST_WINDOW, BURST_MAX = 60, 20
    CRAWL_WINDOW, CRAWL_MAX = 10, 20

    def __init__(self):
        self.burst_times: list[float] = []
        self.crawl_times: list[float] = []
        self.burst_lock = Lock()
        self.crawl_lock = Lock()

    def record(self):
        """Record timestamp when request is made."""
        with self.burst_lock: self.burst_times.append(time())
        with self.crawl_lock: self.crawl_times.append(time())

    def check(self) -> float:
        """Check whether limits are exceeded, return the time to wait."""
        burst_wait, crawl_wait = float(0), float(0)
        with self.burst_lock:
            self.burst_times = [t for t in self.burst_times if time() - t < ChronAmRateLimiter.BURST_WINDOW]
            if len(self.burst_times) > ChronAmRateLimiter.BURST_MAX:
                burst_wait = max(0, self.burst_times[0] + ChronAmRateLimiter.BURST_WINDOW - time())
        with self.crawl_lock:
            self.crawl_times = [t for t in self.crawl_times if time() - t < ChronAmRateLimiter.CRAWL_WINDOW]
            if len(self.crawl_times) > ChronAmRateLimiter.CRAWL_MAX:
                crawl_wait = max(0, self.crawl_times[0] + ChronAmRateLimiter.CRAWL_WINDOW - time())

        return max(burst_wait, crawl_wait)

    def submit(self, f: Callable[..., _R], *args, **kwargs) -> _R:
        """Waits `self.check()` seconds then runs `f(*args, **kwargs)`, recording the timestamp."""
        if (wait := self.check()):
            print(f'INFO: rate limit reached; waiting {wait} seconds.')
            sleep(wait + 0.1)
        
        self.record()
        return f(*args, **kwargs)
