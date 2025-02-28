import tempfile
import typing as t
from contextlib import chdir
from pathlib import Path

from edwh_files_plugin.compression import Compression, Gzip, Nocompression, Pigz, Zip

DATA = "x" * int(1e9)


def run_test_with_file(compressor: Compression, extension: str, decompressor: t.Optional[Compression] = None):
    decompressor = decompressor or compressor
    assert compressor.is_available()
    assert decompressor.is_available()

    with tempfile.TemporaryDirectory(prefix="pytest_file") as d:
        dir_path = Path(d)
        bigfile = dir_path / "myfile.txt"
        bigfile.write_text(DATA)

        lilfile = dir_path / f"myfile.{extension}"

        assert compressor.compress(bigfile, lilfile)

        assert lilfile.exists()
        assert lilfile.stat().st_size < bigfile.stat().st_size

        unzipped = dir_path / "unzipped.txt"
        assert decompressor.decompress(lilfile, unzipped)

        assert unzipped.read_text() == DATA


def run_test_with_folder(compressor: Compression, extension: str, decompressor: t.Optional[Compression] = None):
    decompressor = decompressor or compressor
    assert compressor.is_available()
    assert decompressor.is_available()

    with tempfile.TemporaryDirectory(prefix="pytest_folder") as d:
        parent_d = Path(d)
        child_d = parent_d / "somefolder"
        child_d.mkdir()

        bigfile = child_d / "raw.txt"
        bigfile.write_text(DATA)

        file2 = child_d / "small.txt"
        file2.write_text("-")

        lilfile = parent_d / f"compressed.{extension}"

        assert compressor.compress(child_d, lilfile)

        assert lilfile.exists()
        assert lilfile.stat().st_size < bigfile.stat().st_size

        unzipped_d = parent_d / "somefolder2"
        unzipped_d.mkdir()
        assert decompressor.decompress(lilfile, unzipped_d)

        unzipped = unzipped_d / "raw.txt"
        assert unzipped.read_text() == DATA


def test_zip():
    zip_compression = Compression.for_extension("zip")
    assert isinstance(zip_compression, Zip)
    run_test_with_file(zip_compression, "zip")
    run_test_with_folder(zip_compression, "zip")


def test_gzip():
    gzip_compression = Gzip()
    assert isinstance(gzip_compression, Gzip)
    run_test_with_file(gzip_compression, "gz")
    run_test_with_folder(gzip_compression, "tgz")
    run_test_with_folder(gzip_compression, "tar.gz")


def test_pigz():
    pigz_compression = Compression.for_extension("gz")
    assert isinstance(pigz_compression, Pigz)  # pigz > gz
    run_test_with_file(pigz_compression, "gz")
    run_test_with_folder(pigz_compression, "tgz")
    run_test_with_folder(pigz_compression, "tar.gz")


def test_gzip_pigz_cross():
    gz_compression = Gzip()
    pigz_compression = Pigz()
    run_test_with_file(pigz_compression, "gz", decompressor=gz_compression)
    run_test_with_folder(pigz_compression, "tgz", decompressor=gz_compression)

    run_test_with_file(gz_compression, "gz", decompressor=pigz_compression)
    run_test_with_folder(gz_compression, "tgz", decompressor=pigz_compression)


def test_noop():
    class Noop(Compression, extension="noop"): ...

    # false because it is not available
    assert not Compression.for_extension("noop")
    assert not Noop.is_available()

    assert not Compression.for_extension("fake")


def test_nocompression():
    compressor = Nocompression()

    # test file:
    assert compressor.is_available()

    with tempfile.TemporaryDirectory(prefix="pytest_file") as d:
        dir_path = Path(d)
        bigfile = dir_path / "myfile.txt"
        bigfile.write_text(DATA)

        lilfile = dir_path / f"myfile.txt"

        assert compressor.compress(bigfile)

        assert lilfile.exists()
        assert lilfile.stat().st_size == bigfile.stat().st_size

        unzipped = dir_path / "myfile.txt"
        assert compressor.decompress(lilfile)

        assert unzipped.read_text() == DATA

    # test folder:
    with tempfile.TemporaryDirectory(prefix="pytest_folder") as d:
        parent_d = Path(d)
        child_d = parent_d / "somefolder"
        child_d.mkdir()

        bigfile = child_d / "raw.txt"
        bigfile.write_text(DATA)

        file2 = child_d / "small.txt"
        file2.write_text("-")

        lilfile = parent_d / f"somefolder.tar"

        assert compressor.compress(child_d)

        assert lilfile.exists()

        unzipped_d = parent_d / "somefolder"
        assert compressor.decompress(lilfile)

        unzipped = unzipped_d / "raw.txt"
        assert unzipped.read_text() == DATA


def test_best():
    compressor = Compression.best()
    assert isinstance(compressor, Pigz)


def test_compress_decompress_without_filename():
    c = Compression.best()

    with tempfile.TemporaryDirectory() as d, chdir(d):
        p = Path(d)
        t = p / "file.txt"
        t.write_text("--------------------")

        assert c.compress(".")
        assert c.compress(t)

        assert c.decompress(p.with_suffix(".tgz"))
        assert c.decompress(t.with_suffix(".txt.gz"))
