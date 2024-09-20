import io
import tempfile
from pathlib import Path

from edwh_files_plugin.compression import Compression, Zip

DATA = "x" * int(1e9)


def test_zip():
    # Compression.best()
    zip = Compression.for_extension("zip")

    assert zip.is_available()

    with tempfile.TemporaryDirectory(prefix="pytest_zip") as d:
        dir_path = Path(d)
        bigfile = dir_path / "myfile.txt"
        bigfile.write_text(DATA)

        lilfile = dir_path / "myfile.zip"

        assert zip.compress(bigfile, lilfile)

        assert lilfile.exists()
        assert lilfile.stat().st_size < bigfile.stat().st_size

        holder = io.StringIO()
        assert zip.decompress(lilfile, holder)

        assert holder.read() == DATA
