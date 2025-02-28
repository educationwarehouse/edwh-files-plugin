import json
import sys
import tempfile
import typing
from pathlib import Path
from typing import Optional

import requests
from edwh import improved_task as task
from invoke import Context

# rich.progress is fancier but much slower (100ms import)
# so use simpler progress library (also used by pip, before rich):
from progress.bar import ChargingBar
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
from rich import print  # noqa: A004
from threadful import thread
from threadful.bonus import animate

from edwh_files_plugin.compression import DEFAULT_COMPRESSION_LEVEL, Compression

DEFAULT_TRANSFERSH_SERVER = "https://files.edwh.nl"


def require_protocol(url: str) -> str:
    """
    Make sure 'url' has an HTTP or HTTPS schema.
    """
    return url if url.startswith(("http://", "https://")) else f"https://{url}"


def create_callback(encoder: MultipartEncoder) -> typing.Callable[[MultipartEncoderMonitor], None]:
    """
    Creates a callback function for monitoring the progress of an upload.

    Args:
        encoder (MultipartEncoder): The multipart encoder that is uploading the data.

    Returns:
        A callback function that updates a progress bar based on the amount of data that has been read by the encoder.

    Example:

        import requests
        from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor

        def my_callback(monitor: MultipartEncoder):
            print('bytes sent: {0}'.format(monitor.bytes_read))

        filename = 'my_file.txt'

        with open(filename, 'rb') as f:
            encoder = MultipartEncoder(
                fields={
                    'file': (filename, f, "text/plain"),
                }
            )

        monitor = MultipartEncoderMonitor(encoder, my_callback)
        result = requests.post('http://some-url.com/upload',
                               data=monitor,
                               headers={'Content-Type': monitor.content_type})

    """
    bar = ChargingBar("Uploading", max=encoder.len)

    def callback(monitor: MultipartEncoderMonitor) -> None:
        # goto instead of next because chunk size is unknown
        bar.goto(monitor.bytes_read)

    return callback


# auto = best for directory; none for files
# gzip: .tgz for directory; .gz for files. Pigz or Gzip based on availability
FullCompressionTypes: typing.TypeAlias = typing.Literal["auto", "gzip", "zip", "tgz", "gz", "none"]
CliCompressionTypes: typing.TypeAlias = typing.Literal["auto", "gzip", "zip", "none"]


def upload_file(
    url: str,
    filename: str,
    filepath: Path,
    headers: Optional[dict[str, typing.Any]] = None,
    compression: FullCompressionTypes = "auto",
    compression_level: int = DEFAULT_COMPRESSION_LEVEL,
) -> requests.Response:
    """
    Upload a file to an url.
    """
    if headers is None:
        headers = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        if compression != "auto":
            new_filepath = Path(tmpdir) / filepath.name
            filename = compress_directory(
                filepath,
                new_filepath,
                extension="gz" if compression == "gzip" else compression,
                compression_level=compression_level,
            )
            filepath = new_filepath

        with filepath.open("rb") as f:
            encoder = MultipartEncoder(
                fields={
                    filename: (filename, f, "text/plain"),
                }
            )

            monitor = MultipartEncoderMonitor(encoder, create_callback(encoder))
            return requests.post(url, data=monitor, headers=headers | {"Content-Type": monitor.content_type})


@thread()
def _compress_directory(
    dir_path: str | Path,
    file_path: str | Path,
    extension: FullCompressionTypes = "auto",
    compression_level: int = DEFAULT_COMPRESSION_LEVEL,
) -> str:
    """
    Compress a directory into a compressed (zip, gz) file.
    """
    compressor = Compression.best() if extension == "auto" else Compression.for_extension(extension)

    if not compressor:
        print(f"[red] No compression available for {extension} [/red]")
        print(f"[blue] Please choose one of : {Compression.available()}[/blue]")
        raise RuntimeError("Something went wrong during compression!")

    if compressor.compress(dir_path, file_path, level=compression_level):
        return compressor.filename(dir_path)
    else:
        raise RuntimeError("Something went wrong during compression!")


def compress_directory(
    dir_path: str | Path,
    file_path: str | Path,
    extension: FullCompressionTypes = "auto",
    compression_level: int = DEFAULT_COMPRESSION_LEVEL,
) -> str:
    """
    Compress a directory into a compressed file (zip, gz) and show a spinning animation.
    """
    return animate(
        _compress_directory(dir_path, file_path, extension, compression_level=compression_level),
        text=f"Compressing directory {dir_path}",
    )


def upload_directory(
    url: str,
    filepath: Path,
    headers: Optional[dict[str, typing.Any]] = None,
    upload_filename: Optional[str] = None,
    compression: FullCompressionTypes = "auto",
    compression_level: int = DEFAULT_COMPRESSION_LEVEL,
) -> requests.Response:
    """
    Zip a directory and upload it to an url.

    Args:
        url: which transfer.sh server to use
        filepath: which directory to upload
        headers: upload options
        upload_filename: by default, the directory name with compression extension (e.g. .gz, .zip) will be used
        compression: which method for compression to use (or best available by default)
        compression_level: The compression level is a measure of the compression quality (file size; int 0 - 9).
    """
    filepath = filepath.expanduser().absolute()
    filename = filepath.resolve().name

    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = Path(tmpdir) / filename
        compressed_filename = compress_directory(
            filepath,
            archive_path,
            extension="tgz" if compression == "gzip" else compression,
            compression_level=compression_level,
        )  # -> filename.zip e.g.

        upload_filename = upload_filename or compressed_filename

        return upload_file(
            url, upload_filename, Path(archive_path), headers=headers, compression_level=compression_level
        )


@task(aliases=("add", "send"))
def upload(
    _: Context,
    filename: str | Path,
    server: str = DEFAULT_TRANSFERSH_SERVER,
    max_downloads: Optional[int] = None,
    max_days: Optional[int] = None,
    encrypt: Optional[str] = None,
    rename: Optional[str] = None,
    compression: CliCompressionTypes = "auto",  # auto | pigz | gzip | zip
    compression_level: int = DEFAULT_COMPRESSION_LEVEL,
) -> None:
    """
    Upload a file.

    Args:
        _: invoke Context
        filename (str): path to the file to upload
        server (str): which transfer.sh server to use
        max_downloads (int): how often can the file be downloaded?
        max_days (int): how many days can the file be downloaded?
        encrypt (str): encryption password
        rename (str): upload the file/folder with a different name than it currently has
        compression (str): by default files are not compressed.
                           For folders it will try pigz (.tgz), gzip (.tgz) then .zip.
                           You can also explicitly specify a compression method for files and directory,
                           and nothing else will be tried.
        compression_level (int): The compression level is a measure of the compression quality (file size).
                                 It is expressed as an integer in the range 1 - 9.
                                 Compression quality and performance are conflicting goals.
                                 Compression level 1 provides best performance at the expense of quality.
                                 Compression level 9 provides the smallest file size.
    """
    headers: dict[str, str | int] = {}

    if max_downloads:
        headers["Max-Downloads"] = max_downloads
    if max_days:
        headers["Max-Days"] = max_days
    if encrypt:
        headers["X-Encrypt-Password"] = encrypt

    url = require_protocol(server)

    filepath = Path(filename)

    try:
        if filepath.is_dir():
            response = upload_directory(
                url,
                filepath,
                headers,
                upload_filename=rename,
                compression=compression,
                compression_level=compression_level,
            )
        else:
            response = upload_file(
                url,
                rename or str(filename),
                filepath,
                headers,
                compression=compression,
                compression_level=compression_level,
            )
    except RuntimeError as e:
        print(f"[red] {e} [/red]")
        exit(1)

    download_url = response.text.strip()
    delete_url = response.headers.get("x-url-delete")

    print(
        json.dumps(
            {
                "status": response.status_code,
                "url": download_url,
                "delete": delete_url,
                "download_command": f"edwh file.download {download_url}",
                "delete_command": f"edwh file.delete {delete_url}",
            },
            indent=2,
        ),
    )


@task(aliases=("get", "receive"))
def download(
    _: Context,
    download_url: str,
    output_file: Optional[str | Path] = None,
    decrypt: Optional[str] = None,
    unpack: bool = False,
) -> None:
    """
    Download a file.

    Args:
        _ (Context)
        download_url (str): file to download
        output_file (str): path to store the file in
        decrypt (str): decryption token
        unpack (bool): unpack archive to file(s), removing the archive afterwards
    """
    if output_file is None:
        output_file = download_url.split("/")[-1]
    output_path = Path(output_file)

    download_url = require_protocol(download_url)

    headers = {}
    if decrypt:
        headers["X-Decrypt-Password"] = decrypt

    response = requests.get(download_url, headers=headers, stream=True)

    if response.status_code >= 400:
        print("[red] Something went wrong: [/red]", response.status_code, response.content.decode(), file=sys.stderr)
        return

    total = int(response.headers["Content-Length"]) // 1024
    with (
        output_path.open("wb") as f,
    ):  # <- open file when we're sure the status code is successful!
        for chunk in ChargingBar("Downloading", max=total).iter(response.iter_content(chunk_size=1024)):
            f.write(chunk)

    if unpack:
        do_unpack(_, str(output_path), remove=True)


@task(aliases=("remove",))
def delete(_: Context, deletion_url: str) -> None:
    """
    Delete an uploaded file.

    Args:
        _ (Context)
        deletion_url (str): File url + deletion token (from `x-url-delete`, shown in file.upload output)
    """
    deletion_url = require_protocol(deletion_url)

    response = requests.delete(deletion_url, timeout=15)

    print(
        {
            "status": response.status_code,
            "response": response.text.strip(),
        }
    )


@task(name="unpack")
def do_unpack(_: Context, filename: str, remove: bool = False) -> None:
    """
    Decompress a given file.

    Args:
        _: invoke Context
        filename (str): Path of the file to be decompressed
        remove (bool, optional): If True, original compressed file will be deleted after decompression.
                                 Defaults to False.

    Returns:
        None
    """
    filepath = Path(filename)
    ext = filepath.suffix

    compressor = Compression.for_extension(ext)

    if compressor and compressor.decompress(filepath, filepath.with_suffix("")):
        if remove:
            filepath.unlink()
    else:
        print("[red] Something went wrong unpacking! [/red]")
