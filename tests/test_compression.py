from edwh_files_plugin.compression import Zip, Compression


def test_zip():
    # Compression.best()
    zip = Compression.for_extension("zip")

    assert zip.is_available()

    zip.compress()
    zip.decompress()
