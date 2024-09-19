import abc
import warnings
from typing import Self


class Compression(abc.ABC):
    def __init_subclass__(cls, extension: str = "", prio: int = 0):
        if not extension:
            warnings.warn("Defined compression algorithm without extension, it will be ignored.")

    @abc.abstractmethod
    def compress(self):
        ...

    @abc.abstractmethod
    def decompress(self):
        ...

    @abc.abstractmethod
    def is_available(self) -> bool:
        ...

    @classmethod
    def best(cls) -> Self:
        return Zip()

    @classmethod
    def for_extension(cls, extension: str) -> Self:
        return Zip()


class Zip(Compression, extension="zip"):
    def is_available(self) -> bool:
        try:
            import zlib
            return True
        except ImportError:
            return False

    def compress(self):
        ...

    def decompress(self):
        ...


class Noop(Compression):
    ...
