import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional, TypedDict

import requests
from invoke import Context, task

# rich.progress is fancier but much slower (100ms import)
# so use simpler progress library (also used by pip, before rich):
from progress.bar import ChargingBar
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
from rich import print
from termcolor import cprint
from threadful import thread
from threadful.bonus import animate

DEFAULT_TRANSFERSH_SERVER = "https://files.edwh.nl"


def require_protocol(url: str):
    """
    Make sure 'url' has an HTTP or HTTPS schema.
    """
    return url if url.startswith(("http://", "https://")) else f"https://{url}"


def create_callback(encoder: MultipartEncoder):
    bar = ChargingBar("Uploading", max=encoder.len)

    def callback(monitor: MultipartEncoderMonitor):
        # goto instead of next because chunk size is unknown
        bar.goto(monitor.bytes_read)

    return callback


def upload_file(url: str, filename: str, filepath: Path, headers: Optional[dict] = None) -> requests.Response:
    """
    Upload a file to an url.
    """
    if headers is None:
        headers = {}

    with filepath.open("rb") as f:
        encoder = MultipartEncoder(
            fields={
                filename: (filename, f, "text/plain"),
            }
        )

        monitor = MultipartEncoderMonitor(encoder, create_callback(encoder))

        return requests.post(url, data=monitor, headers=headers | {"Content-Type": monitor.content_type})  # noqa


@thread()
def _zip_directory(dir_path: str | Path, file_path: str | Path):
    """
    Compress a directory into a .zip file.
    """
    return shutil.make_archive(str(file_path), "zip", str(dir_path))


def zip_directory(dir_path: str | Path, file_path: str | Path):
    """
    Compress a directory into a .zip file and show a spinning animation.
    """
    return animate(_zip_directory(dir_path, file_path), text=f"Zipping directory {dir_path}")


def upload_directory(url: str, filepath: Path, headers: Optional[dict] = None):
    """
    Zip a directory and upload it to an url.
    """
    filename = filepath.resolve().name

    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = zip_directory(filepath, Path(tmpdir) / filename)

        return upload_file(url, f"{filename}.zip", Path(archive_path), headers=headers)


class UploadResult(TypedDict):
    status: int
    url: str
    delete: str
    download_command: str
    delete_command: str


def transfer_upload(
    filename: str | Path,
    server: str = DEFAULT_TRANSFERSH_SERVER,
    max_downloads: Optional[int] = None,
    max_days: Optional[int] = None,
    encrypt: Optional[str] = None,
) -> UploadResult:
    headers: dict[str, str | int] = {}

    if max_downloads:
        headers["Max-Downloads"] = str(max_downloads)
    if max_days:
        headers["Max-Days"] = str(max_days)
    if encrypt:
        headers["X-Encrypt-Password"] = encrypt

    url = require_protocol(server)

    filepath = Path(filename)

    if filepath.is_dir():
        response = upload_directory(url, filepath, headers)
    else:
        response = upload_file(url, str(filename), filepath, headers)

    download_url = response.text.strip()
    delete_url = response.headers.get("x-url-delete", "")

    return {
        "status": response.status_code,
        "url": download_url,
        "delete": delete_url,
        "download_command": f"edwh file.download {download_url}",
        "delete_command": f"edwh file.delete {delete_url}",
    }


@task(aliases=("add", "send"))
def upload(
    _: Context,
    filename: str | Path,
    server: str = DEFAULT_TRANSFERSH_SERVER,
    max_downloads: Optional[int] = None,
    max_days: Optional[int] = None,
    encrypt: Optional[str] = None,
):
    """
    Upload a file.

    Args:
        _: invoke Context
        filename (str): path to the file to upload
        server (str): which transfer.sh server to use
        max_downloads (int): how often can the file be downloaded?
        max_days (int): how many days can the file be downloaded?
        encrypt (str): encryption password
    """
    result = transfer_upload(
        filename,
        server=server,
        max_downloads=max_downloads,
        max_days=max_days,
        encrypt=encrypt,
    )

    print(
        json.dumps(
            result,
            indent=2,
        ),
    )


@task(aliases=("get", "receive"))
def download(_: Context, download_url: str, output_file: Optional[str | Path] = None, decrypt: Optional[str] = None):
    """
    Download a file.

    Args:
        _ (Context)
        download_url (str): file to download
        output_file (str): path to store the file in
        decrypt (str): decryption token
    """
    if output_file is None:
        output_file = download_url.split("/")[-1]

    download_url = require_protocol(download_url)

    headers = {}
    if decrypt:
        headers["X-Decrypt-Password"] = decrypt

    response = requests.get(download_url, headers=headers, stream=True)  # noqa

    if response.status_code >= 400:
        print("[red] Something went wrong: [/red]", response.status_code, response.content.decode(), file=sys.stderr)
        return

    total = int(response.headers["Content-Length"]) // 1024
    with (
        open(output_file, "wb") as f,
    ):  # <- open file when we're sure the status code is successful!
        for chunk in ChargingBar("Downloading", max=total).iter(response.iter_content(chunk_size=1024)):
            f.write(chunk)


@task(aliases=("remove",))
def delete(_: Context, deletion_url: str, quiet: bool = False):
    """
    Delete an uploaded file.

    Args:
        _ (Context)
        deletion_url (str): File url + deletion token (from `x-url-delete`, shown in file.upload output)
    """
    deletion_url = require_protocol(deletion_url)

    response = requests.delete(deletion_url, timeout=15)

    if not quiet:
        print(
            {
                "status": response.status_code,
                "response": response.text.strip(),
            }
        )
    return response.ok


@task(aliases=("evanescent", "tmp"))
def evanescence(
    c: Context,
    filename: str | Path,
    server: str = DEFAULT_TRANSFERSH_SERVER,
    encrypt: Optional[str] = None,
):
    """
    Temporarily upload a file.
    """

    result = transfer_upload(
        filename,
        server=server,
        max_days=1,
        max_downloads=2,
        encrypt=encrypt,
    )

    cprint("\nAnd there's just too much that time cannot erase... unlike this file.", on_color="on_cyan")
    cprint(result["download_command"], "cyan")

    try:
        input("ctrl-c or enter to stop ")
    except EOFError:
        pass
    finally:
        if delete(c, result["delete"], quiet=True):
            cprint("\nI'm going under.", on_color="on_magenta")
            cprint("(temporary file deleted)", color="magenta")
        else:
            cprint("\nThis file lingers on... lost in the shadows", on_color="on_red")
            cprint("(temporary file could not be removed)", color="red")
