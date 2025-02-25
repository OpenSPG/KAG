from kag.common.registry import Registrable


class RateLimiter(Registrable):
    """
    A base class for rate limiting implementations. Subclasses should implement the `acquire` method.

    Args:
        name (str): The name of the rate limiter.
        max_calls (int, optional): The maximum number of allowed calls within the specified period.
        period (float, optional): The period in seconds within which the maximum number of calls is allowed.
        **kwargs: Additional keyword arguments passed to the superclass constructor.
    """

    def __init__(self, name, max_calls: int = None, period: float = None, **kwargs):
        super().__init__(**kwargs)
        self.name = name if name is not None else ""
        self.max_calls = max_calls
        self.period = period

    def acquire(self):
        """
        Acquire a call slot from the rate limiter. This method should be implemented by subclasses.

        Raises:
            NotImplementedError: If the method is not overridden in a subclass.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} need to implement `acquire` method."
        )
