import abc
import os
import shutil
import sys
import typing
import warnings
from pathlib import Path
from subprocess import run
from typing import Optional, Self

from plumbum import local
from plumbum.commands.processes import CommandNotFound
from rich import print  # noqa: A004

PathLike: typing.TypeAlias = str | Path

DEFAULT_COMPRESSION_LEVEL = 5


def run_ok(command: str) -> bool:
    """
    Executes a command and returns whether it ended successfully (with return code 0).

    Args:
        command (str): The command to run.

    Returns:
        bool: True if the command ended successfully, False otherwise.
    """
    with Path(os.devnull).open("w") as devnull:
        return run(command.split(" "), stdout=devnull, stderr=devnull).returncode == 0


def is_installed(program: str) -> bool:
    """
    Checks if a given program is installed on the system.

    Args:
        program (str): The name of the program to check.

    Returns:
        bool: True if the program is installed, False otherwise.
    """
    return run_ok(f"which {program}")


# FileLike: typing.TypeAlias = PathLike | typing.BinaryIO | typing.TextIO
# def filelike_to_binaryio(fl: FileLike) -> typing.BinaryIO: ...


class Compression(abc.ABC):
    _registrations: dict[tuple[int, str], typing.Type[Self]] = {}
    extension: str | tuple[str, ...]

    def __init_subclass__(cls, extension: str | tuple[str, ...] = "", prio: int = 0):
        if not extension:
            warnings.warn("Defined compression algorithm without extension, it will be ignored.")

        if isinstance(extension, str):
            Compression._registrations[(prio, extension)] = cls
        else:
            for ext in extension:
                Compression._registrations[(prio, ext)] = cls

        cls.extension = extension

    @abc.abstractmethod
    def _compress(
        self, source: Path, target: Path, level: int = DEFAULT_COMPRESSION_LEVEL, overwrite: bool = True
    ) -> bool:
        """
        Compresses the source file or directory to the target location.

        Args:
            source (Path): Path to the source file or directory to compress.
            target (Path): Path where the compressed file will be saved.
            level (int, optional): Compression level (1-9), where higher numbers indicate higher compression.
                                   Defaults to 5.
            overwrite (bool, optional): Whether to overwrite the target file if it already exists. Defaults to True.
        """

    def compress(
        self,
        source: PathLike,
        target: Optional[PathLike] = None,
        level: int = DEFAULT_COMPRESSION_LEVEL,
        overwrite: bool = True,
    ) -> bool:
        source = Path(source).expanduser().absolute()

        if target is None:
            target = self.filepath(source)
            # assert target != source, "Please provide a target file to compress to"
        else:
            target = Path(target)

        try:
            return self._compress(
                source,
                target,
                level=level,
                overwrite=overwrite,
            )
        except Exception as e:
            print("[red] Something went wrong during compression [/red]")
            print(e)
            return False

    @abc.abstractmethod
    def _decompress(self, source: Path, target: Path, overwrite: bool = True) -> bool:
        """
        Decompresses the source file to the target location.

        Args:
            source (str): Path to the compressed file.
            target (str): Path where the decompressed contents will be saved.
            overwrite (bool, optional): Whether to overwrite the target files if they already exist. Defaults to True.
        """

    def decompress(self, source: PathLike, target: Optional[PathLike] = None, overwrite: bool = True) -> bool:
        source = Path(source).expanduser().absolute()

        if target is None and source.suffix in (".tgz", ".tar", ".gz", ".zip"):
            # strip last extension (e.g. .tgz); retain other extension (.txt)
            extension = ".".join(source.suffixes[:-1])
            target = source.with_suffix(f".{extension}" if extension else "")
        elif target is None:
            target = source
        else:
            target = Path(target)

        try:
            return self._decompress(
                source,
                target,
                overwrite=overwrite,
            )
        except Exception as e:
            print("[red] Something went wrong during decompression [/red]")
            print(e)
            return False

    @classmethod
    @abc.abstractmethod
    def is_available(cls) -> bool:
        """
        Checks if the required compression tool is available.

        Returns:
            bool: True if the compression tool is available, False otherwise.
        """

    @classmethod
    def registrations(
        cls, extension_filter: Optional[str] = None
    ) -> list[tuple[tuple[int, str], typing.Type["Compression"]]]:
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
    def available(cls) -> set[str]:
        return set([extension for (_, extension) in cls._registrations])

    @classmethod
    def best(cls) -> Self | None:
        """
        Find the absolute best (by priority) available compression method.
        """
        if registrations := cls.registrations():
            CompressionClass = registrations[0][1]  # noqa: N806
            return typing.cast(Self, CompressionClass())

        return None

    @classmethod
    def for_extension(cls, extension: str) -> Self | None:
        """
        Find the best (by priority) available compression method for a specific extension (zip, gz).
        """
        if registrations := cls.registrations(extension.strip(".").strip()):
            CompressionClass = registrations[0][1]  # noqa: N806
            return typing.cast(Self, CompressionClass())

        return None

    @classmethod
    def filepath(cls, filepath: str | Path) -> Path:
        """
        Generate an output filepath with the right extension
        """
        filepath = Path(filepath)
        extension = f"{filepath.suffix}.{cls.extension}" if filepath.is_file() else f".{cls.extension}"
        return filepath.with_suffix(extension)

    @classmethod
    def filename(cls, filepath: str | Path) -> str:
        """
        Generate an output filename with the right extension
        """
        return cls.filepath(filepath).name


class Nocompression(Compression, extension=("none", "tar"), prio=0):
    def _compress(
        self, source: Path, target: Path, level: int = DEFAULT_COMPRESSION_LEVEL, overwrite: bool = True
    ) -> bool:
        if source.is_dir():
            tar = local["tar"]
            cmd = tar["-cf", "-", "-C", source.parent, source.name] > str(target)
            cmd()
        elif source != target:
            shutil.copyfile(source, target)
        # else: nothing to do

        return True

    def _decompress(self, source: Path, target: Path, overwrite: bool = True) -> bool:
        if source.suffix == ".tar":
            target.mkdir(exist_ok=True)
            tar = local["tar"]
            cmd = tar["-xvf", source, "--strip-components=1", "-C", target]
            cmd()
        elif source != target:
            shutil.copyfile(source, target)
        # else: nothing to do

        return True

    @classmethod
    def is_available(cls) -> bool:
        return True

    @classmethod
    def filepath(cls, filepath: str | Path) -> Path:
        filepath = Path(filepath)
        if filepath.is_dir():
            return filepath.with_suffix(".tar")
        else:
            return filepath


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
            import zipfile  # noqa: F401

            return True
        except ImportError:
            return False


class Gzip(Compression, extension=("tgz", "gz"), prio=1):
    def gzip_compress(
        self, source: Path, target: Path, level: int = DEFAULT_COMPRESSION_LEVEL, _tar: str = "tar", _gzip: str = "gzip"
    ) -> bool:
        """
        Compress data using gzip.

        This function compresses data from a source to a target path using the gzip tool.

        Args:
            source (Path): Path to the file or data to be compressed.
            target (Path): Path where the compressed data will be saved.
            level (int): compression level, where 0 is fastest and 9 is strongest but slowest.
                Defaults to DEFAULT_COMPRESSION_LEVEL.
            _tar (str): For internal usage
            _gzip (str): For internal usage

        Returns:
            bool: True if compression was successful, False on any failure.
        """
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

    def gzip_decompress(self, source: Path, target: Path, _tar: str = "tar", _gunzip: str = "gunzip") -> bool:
        """
        Decompresses a gzipped file and extracts it into the specified target directory.

        Args:
            source (Path): The path to the gzipped file.
            target (Path): The directory to extract the decompressed file(s) to.

        Returns:
            bool: True if the decompression and extraction were successful, False otherwise.
        """
        gunzip = local[_gunzip]
        tar = local[_tar]

        if ".tar" in source.suffixes or ".tgz" in source.suffixes:
            # tar gz
            target.mkdir(parents=True, exist_ok=True)
            cmd = tar["-xvf", source, "--strip-components=1", f"--use-compress-program={_gunzip}", "-C", target]
        else:
            # assume just a .gz
            cmd = gunzip["-c", source] > str(target)

        cmd()
        return True

    def _decompress(self, source: Path, target: Path, overwrite: bool = True) -> bool:
        if target.exists() and not overwrite:
            return False

        self.gzip_decompress(source, target)
        return True

    @classmethod
    def is_available(cls) -> bool:
        """
        Check if 'gzip' and 'gunzip' are available in the local context.

        Returns:
            bool: The return value is True if 'gzip' and 'gunzip' are found,
                  False otherwise.
        """
        try:
            assert local["gzip"] and local["gunzip"]
            return True
        except CommandNotFound:
            return False

    @classmethod
    def filepath(cls, filepath: str | Path) -> Path:
        """
        Return a Path object with either '.gz' or '.tgz' appended as file extension based on whether
        the provided file path is a file or not.

        Args:
            filepath (str | Path): The input file path in string or Path format.

        Returns:
            Path: The updated file path with appended file extension.
        """
        filepath = Path(filepath)
        extension = f"{filepath.suffix}.gz" if filepath.is_file() else ".tgz"
        return filepath.with_suffix(extension)


def print_once(msg: str, _seen=set(), **print_kwargs):
    """
    Print out a message and remember which messages you've seen
    to prevent duplicate messages from being printed.
    """
    if msg in _seen:
        return

    print(msg, **print_kwargs)
    _seen.add(msg)


class Pigz(Gzip, extension=("tgz", "gz"), prio=2):
    """
    The Pigz class inherits from the Gzip base class.

    Its priority is higher than that of the base class, as indicated by the value 2.

    Pigz (Parallel Implementation of GZip) is a fully functional replacement for gzip
    that exploits multiple processors and multiple cores to the hilt when compressing data.
    Pigz can be a good choice when you're handling large amounts of data,
    and your machine has multiple cores/processors.

    Advantages of pigz over classic gzip:
    - Multithreading: Pigz can split the input data into chunks and process them in parallel.
                      This utilizes multiple cores on your machine,
    leading to faster compression times.
    - Compatibility: Pigz maintains backward compatibility with gzip, so it can handle any file that gzip can.
    - Speed: In multi-core systems, pigz can be significantly faster than gzip
             because of its ability to process different parts of the data simultaneously.
    """

    def _compress(
        self, source: Path, target: Path, level: int = DEFAULT_COMPRESSION_LEVEL, overwrite: bool = True
    ) -> bool:
        if target.exists() and not overwrite:
            return False

        self.gzip_compress(source, target, level=level, _gzip="pigz")
        return True

    def _decompress(self, source: Path, target: Path, overwrite: bool = True) -> bool:
        if target.exists() and not overwrite:
            return False

        self.gzip_decompress(source, target, _gunzip="unpigz")
        return True

    @classmethod
    def is_available(cls) -> bool:
        """
        Check if 'pigz' and 'unpigz' commands are available in the local environment.

        Returns:
            bool: The return value. True for success, False otherwise.
        """
        try:
            assert local["pigz"] and local["unpigz"]
            return True
        except CommandNotFound:
            print_once(
                "[yellow]WARN: pigz isn't available! You're missing out on performance[/yellow]", file=sys.stderr
            )
            return False
