import io
import tempfile
from pathlib import Path

from edwh_files_plugin.compression import Compression, Gzip, Pigz, Zip, run_ok

DATA = "x" * int(1e9)


def run_test_with_file(compressor: Compression, extension: str, decompressor: Compression = None):
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


def run_test_with_folder(compressor: Compression, extension: str, decompressor: Compression = None):
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
    zip = Compression.for_extension("zip")
    assert isinstance(zip, Zip)
    run_test_with_file(zip, "zip")
    run_test_with_folder(zip, "zip")


def test_gzip():
    gz = Gzip()
    assert isinstance(gz, Gzip)
    run_test_with_file(gz, "gz")
    run_test_with_folder(gz, "tgz")
    run_test_with_folder(gz, "tar.gz")


def test_pigz():
    pigz = Compression.for_extension("gz")
    assert isinstance(pigz, Pigz)  # pigz > gz
    run_test_with_file(pigz, "gz")
    run_test_with_folder(pigz, "tgz")
    run_test_with_folder(pigz, "tar.gz")


def test_gzip_pigz_cross():
    gz = Gzip()
    pigz = Pigz()
    run_test_with_file(pigz, "gz", decompressor=gz)
    run_test_with_folder(pigz, "tgz", decompressor=gz)

    run_test_with_file(gz, "gz", decompressor=pigz)
    run_test_with_folder(gz, "tgz", decompressor=pigz)


def test_noop():
    class Noop(Compression, extension="noop"): ...

    # false because it is not available
    assert not Compression.for_extension("noop")
    assert not Noop.is_available()

    assert not Compression.for_extension("fake")


def test_best():
    compressor = Compression.best()
    assert isinstance(compressor, Pigz)
