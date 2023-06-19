import io

import httpx
from invoke import task
from rich import print, progress

DEFAULT_TRANSFERSH_SERVER = "https://files.edwh.nl"


def require_protocol(url: str):
    if not url.startswith("http"):
        return f"https://{url}"
    return url


@task(aliases=("add",))
def upload(_, filename, server=DEFAULT_TRANSFERSH_SERVER, max_downloads=None, max_days=None, encrypt=None):
    """
    Upload a file.

    Args:
        filename (str): path to the file to upload
        server (str): which transfer.sh server to use
        max_downloads (int): how often can the file be downloaded?
        max_days (int): how many days can the file be downloaded?
        encrypt (str): encryption password
    """
    headers = {}

    if max_downloads:
        headers["Max-Downloads"] = max_downloads
    if max_days:
        headers["Max-Days"] = max_days
    if encrypt:
        headers["X-Encrypt-Password"] = encrypt

    with httpx.Client() as session, open(filename, "rb") as f:
        file = {filename: f}

        url = require_protocol(server)

        response = session.post(url, files=file, headers=headers)

        print(
            {
                "status": response.status_code,
                "url": response.text.strip(),
                "delete": response.headers.get('x-url-delete'),
            }
        )


@task(aliases=("get",))
def download(_, download_url, output_file=None, decrypt=None):
    """
    Download a file.

    Args:
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

    with httpx.Client() as session, session.stream("GET", download_url, headers=headers) as response:
        if response.status_code >= 400:
            print("[red] Something went wrong: [/red]", response.status_code, response.read().decode())
            return

        total = int(response.headers["Content-Length"])
        with (
            open(output_file, "wb") as f,  # <- open file when we're sure the status code is successful!
            progress.Progress(
                "[progress.percentage]{task.percentage:>3.0f}%",
                progress.BarColumn(bar_width=None),
                progress.DownloadColumn(),
                progress.TransferSpeedColumn(),
            ) as progress_bar,
        ):
            download_task = progress_bar.add_task("Download", total=total)
            for chunk in response.iter_bytes():
                f.write(chunk)
                progress_bar.update(download_task, completed=response.num_bytes_downloaded)


@task(aliases=("remove",))
def delete(_, deletion_url):
    """
    Delete an uploaded file.

    Args:
        deletion_url (str): File url + deletion token (from `x-url-delete`, shown in file.upload output)
    """
    deletion_url = require_protocol(deletion_url)

    with httpx.Client() as session:
        response = session.delete(deletion_url)

        print(
            {
                "status": response.status_code,
                "response": response.text.strip(),
            }
        )
