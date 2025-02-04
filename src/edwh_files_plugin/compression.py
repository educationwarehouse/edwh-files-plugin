import abc
import os
import typing
import warnings
from pathlib import Path
from subprocess import run
from typing import Self

from plumbum import local
from plumbum.commands.processes import CommandNotFound

PathLike: typing.TypeAlias = str | Path

DEFAULT_COMPRESSION_LEVEL = 5


def run_ok(command: str) -> bool:
    with open(os.devnull, "w") as devnull:
        return run(command.split(" "), stdout=devnull, stderr=devnull).returncode == 0


def is_installed(program: str) -> bool:
    return run_ok(f"which {program}")


# FileLike: typing.TypeAlias = PathLike | typing.BinaryIO | typing.TextIO
# def filelike_to_binaryio(fl: FileLike) -> typing.BinaryIO: ...


class Compression(abc.ABC):
    _registrations: dict[tuple[int, str], typing.Type[Self]] = {}

    def __init_subclass__(cls, extension: str = "", prio: int = 0):
        if not extension:
            warnings.warn("Defined compression algorithm without extension, it will be ignored.")

        Compression._registrations[(prio, extension)] = cls

    @abc.abstractmethod
    def _compress(
        self, source: Path, target: Path, level: int = DEFAULT_COMPRESSION_LEVEL, overwrite: bool = True
    ) -> bool:
        """
        Compresses the source file or directory to the target location.

        Args:
            source (Path): Path to the source file or directory to compress.
            target (Path): Path where the compressed file will be saved.
            level (int, optional): Compression level (1-9), where higher numbers indicate higher compression. Defaults to 5.
            overwrite (bool, optional): Whether to overwrite the target file if it already exists. Defaults to True.
        """

    def compress(
        self, source: PathLike, target: PathLike, level: int = DEFAULT_COMPRESSION_LEVEL, overwrite: bool = True
    ) -> bool:
        # todo: if target is a dir, derive a good name from the source
        #       todo: target should be optional

        return self._compress(
            Path(source),
            Path(target),
            level=level,
            overwrite=overwrite,
        )

    @abc.abstractmethod
    def _decompress(self, source: Path, target: Path, overwrite: bool = True) -> bool:
        """
        Decompresses the source file to the target location.

        Args:
            source (str): Path to the compressed file.
            target (str): Path where the decompressed contents will be saved.
            overwrite (bool, optional): Whether to overwrite the target files if they already exist. Defaults to True.
        """

    def decompress(self, source: PathLike, target: PathLike, overwrite: bool = True):
        return self._decompress(
            Path(source),
            Path(target),
            overwrite=overwrite,
        )

    @classmethod
    @abc.abstractmethod
    def is_available(cls) -> bool:
        """
        Checks if the required compression tool is available.

        Returns:
            bool: True if the compression tool is available, False otherwise.
        """

    @classmethod
    def registrations(cls, extension_filter: str = None) -> list[tuple[tuple[int, str], typing.Type["Compression"]]]:
        return sorted(
            (
                (key, CompressionClass)
                for (key, CompressionClass) in cls._registrations.items()
                if CompressionClass.is_available() and extension_filter in (None, key[1])
            ),
            key=lambda registration: registration[0],
            reverse=True,
        )

    @classmethod
    def best(cls) -> Self | None:
        """
        Find the absolute best (by priority) available compression method.
        """
        if registrations := cls.registrations():
            CompressionClass = registrations[0][1]
            return CompressionClass()

    @classmethod
    def for_extension(cls, extension: str) -> Self | None:
        """
        Find the best (by priority) available compression method for a specific extension (zip, gz).
        """
        if registrations := cls.registrations(extension):
            CompressionClass = registrations[0][1]
            return CompressionClass()


class Zip(Compression, extension="zip"):
    def _compress(
        self, source: Path, target: Path, level: int = DEFAULT_COMPRESSION_LEVEL, overwrite: bool = True
    ) -> bool:
        from zipfile import ZIP_DEFLATED, ZipFile

        if target.exists() and not overwrite:
            return False

        with ZipFile(target, "w", compression=ZIP_DEFLATED, compresslevel=level) as zip_object:
            if source.is_dir():
                # shutil.make_archive(str(target), "zip", str(source))
                # Traverse all files in directory
                for file_path in source.rglob("*"):
                    if file_path.is_file():
                        # Add files to zip file with the correct relative path
                        arcname = file_path.relative_to(source)
                        zip_object.write(file_path, arcname)
            else:
                zip_object.write(source, source.name)

        return True

    def _decompress(self, source: Path, target: Path, overwrite: bool = True) -> bool:
        if not source.exists() or not source.is_file():
            return False

        from zipfile import ZipFile

        with ZipFile(source, "r") as zip_object:
            namelist = zip_object.namelist()

            # Check if the archive contains exactly one file
            if len(namelist) == 1 and not namelist[0].endswith("/"):
                # The archive contains a single file; treat target as a file
                first_file = namelist[0]

                # If the target is a directory, ensure we create the file inside
                if target.is_dir():
                    target = target / Path(first_file).name

                # Handle overwrite behavior
                if target.exists() and not overwrite:
                    return False

                # Ensure the parent directory exists
                target.parent.mkdir(parents=True, exist_ok=True)

                # Extract the single file directly to the target
                with target.open("wb") as f:
                    f.write(zip_object.read(first_file))

            else:
                # Treat target as a directory and extract all files
                target.mkdir(parents=True, exist_ok=True)

                for member in namelist:
                    # Resolve full path of the extracted file
                    file_path = target / member

                    # Check if file already exists and handle overwrite
                    if file_path.exists() and not overwrite:
                        continue

                    # Ensure parent directories exist
                    file_path.parent.mkdir(parents=True, exist_ok=True)

                    # Extract the file
                    zip_object.extract(member, target)

        return True

    @classmethod
    def is_available(cls) -> bool:
        try:
            import zipfile

            return True
        except ImportError:
            return False


class Gzip(Compression, extension="gz", prio=1):
    def gzip_compress(
        self, source: Path, target: Path, level: int = DEFAULT_COMPRESSION_LEVEL, _tar="tar", _gzip="gzip"
    ):
        tar = local[_tar]
        gzip = local[_gzip]

        if source.is_dir():
            # .tar.gz
            # cmd = tar["-cf", "-", source] | gzip[f"-{level}"] > str(target)
            # ↑ stores whole path in tar; ↓ stores only folder name
            cmd = tar["-cf", "-", "-C", source.parent, source.name] | gzip[f"-{level}"] > str(target)
        else:
            cmd = gzip[f"-{level}", "-c", source] > str(target)

        cmd()
        return True

    def _compress(
        self, source: Path, target: Path, level: int = DEFAULT_COMPRESSION_LEVEL, overwrite: bool = True
    ) -> bool:
        if target.exists() and not overwrite:
            return False

        try:
            self.gzip_compress(source, target, level=level)
            return True
        except Exception:
            return False

    def gzip_decompress(self, source: Path, target: Path, _tar="tar", _gunzip="gunzip"):
        gunzip = local[_gunzip]
        tar = local[_tar]

        if ".tar" in source.suffixes or ".tgz" in source.suffixes:
            # tar gz
            target.mkdir(parents=True, exist_ok=True)
            cmd = tar[f"-xvf", source, "--strip-components=1", f"--use-compress-program={_gunzip}", "-C", target]
        else:
            # assume just a .gz
            cmd = gunzip[f"-c", source] > str(target)

        cmd()

    def _decompress(self, source: Path, target: Path, overwrite: bool = True) -> bool:
        if target.exists() and not overwrite:
            return False

        try:
            self.gzip_decompress(source, target)
            return True
        except Exception:
            return False

    @classmethod
    def is_available(cls) -> bool:
        try:
            assert local["gzip"] and local["gunzip"]
            return True
        except CommandNotFound:
            return False


class Pigz(Gzip, extension="gz", prio=2):
    def _compress(
        self, source: Path, target: Path, level: int = DEFAULT_COMPRESSION_LEVEL, overwrite: bool = True
    ) -> bool:
        if target.exists() and not overwrite:
            return False

        try:
            self.gzip_compress(source, target, _gzip="pigz")
            return True
        except Exception:
            return False

    def _decompress(self, source: Path, target: Path, overwrite: bool = True) -> bool:
        if target.exists() and not overwrite:
            return False

        try:
            self.gzip_decompress(source, target, _gunzip="unpigz")
            return True
        except Exception:
            return False

    @classmethod
    def is_available(cls) -> bool:
        try:
            assert local["pigz"] and local["unpigz"]
            return True
        except CommandNotFound:
            return False
