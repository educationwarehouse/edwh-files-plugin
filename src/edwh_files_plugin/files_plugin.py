import json
import sys

import requests
from invoke import task

from rich import print

# rich.progress is fancier but much slower (100ms import)
# so use simpler progress library (also used by pip, before rich):
from progress.bar import ChargingBar

DEFAULT_TRANSFERSH_SERVER = "https://files.edwh.nl"


def require_protocol(url: str):
    return url if url.startswith(("http://", "https://")) else f"https://{url}"


@task(aliases=("add", "send"))
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

    with open(filename, "rb") as f:
        file = {filename: f}

        url = require_protocol(server)

        response = requests.post(url, files=file, headers=headers)

        download_url = response.text.strip()
        delete_url = response.headers.get('x-url-delete')

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
def download(_, download_url, output_file=None, decrypt=None):
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

    response = requests.get(download_url, headers=headers, stream=True)
    if response.status_code >= 400:
        print("[red] Something went wrong: [/red]", response.status_code, response.content.decode(), file=sys.stderr)
        return

    total = int(response.headers["Content-Length"])
    with (open(output_file, "wb") as f,):  # <- open file when we're sure the status code is successful!
        for chunk in ChargingBar('Processing', max=total).iter(response.iter_content()):
            f.write(chunk)


@task(aliases=("remove",))
def delete(_, deletion_url):
    """
    Delete an uploaded file.

    Args:
        _ (Context)
        deletion_url (str): File url + deletion token (from `x-url-delete`, shown in file.upload output)
    """
    deletion_url = require_protocol(deletion_url)

    response = requests.delete(deletion_url)

    print(
        {
            "status": response.status_code,
            "response": response.text.strip(),
        }
    )
