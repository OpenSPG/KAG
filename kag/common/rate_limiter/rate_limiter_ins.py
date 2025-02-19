import time
import threading

from kag.interface.common.rate_limiter import RateLimiter


class RateLimiterInstance:
    def __init__(self, max_calls: int, period: float):
        """
        初始化速率限制器。

        :param max_calls: 每个时间段内允许的最大调用次数。
        :param period: 时间段的长度（秒）。
        """
        self._max_calls = max_calls
        self._period = period
        self._tokens = max_calls
        self._lock = threading.Lock()
        self._last = time.monotonic()

    def acquire(self):
        """
        获取一个令牌，如果没有令牌则等待直到下一个时间段。
        """
        if self._max_calls is None or self._period is None:
            return
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last

                # 如果一个周期已经过去，重置令牌
                if elapsed >= self._period:
                    self._tokens = self._max_calls
                    self._last = now

                if self._tokens > 0:
                    self._tokens -= 1
                    return  # 成功获取令牌

                # 计算需要等待的时间
                wait_time = self._period - elapsed
            time.sleep(wait_time if wait_time > 0 else self._period)


class RateLimitContainer:
    # 用于存储所有单例对象的字典
    _instances = {}

    # 创建一个锁对象，用于线程安全
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, name, max_calls: int = None, period: float = None):
        """
        通过名字获取单例对象。如果对象不存在，则创建并返回。
        使用线程锁确保线程安全。
        """
        with cls._lock:  # 加锁，确保线程安全
            if name not in cls._instances:
                # 创建新的实例并存储在字典中
                cls._instances[name] = RateLimiterInstance(max_calls=max_calls, period=period)
            else:
                print(f"Returning existing instance for '{name}'")

        # 返回对应名字的实例
        return cls._instances[name]


@RateLimiter.register("rate_limiter")
class PeriodRateLimiter(RateLimiter):
    def __init__(self, name, max_calls: int = None, period: float = None, **kwargs):
        super().__init__(name, max_calls, period, **kwargs)
        self.instance: RateLimiterInstance = RateLimitContainer.get_instance(name, max_calls, period)

    def acquire(self):
        self.instance.acquire()