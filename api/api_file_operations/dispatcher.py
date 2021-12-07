from abc import abstractmethod


class BaseDispatcher:
    """Base class for all dispatcher implementations."""

    @abstractmethod
    def execute(self, *args, **kwds):
        raise NotImplementedError
