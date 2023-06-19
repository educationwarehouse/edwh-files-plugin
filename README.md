# edwh-files-plugin

[![PyPI - Version](https://img.shields.io/pypi/v/edwh-files-plugin.svg)](https://pypi.org/project/edwh-files-plugin)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/edwh-files-plugin.svg)](https://pypi.org/project/edwh-files-plugin)

-----

**Table of Contents**

- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Installation

```console
pip install edwh-files-plugin
```

But probably you want to install the whole edwh package:

```console
pipx install edwh[files]
# or
pipx install edwh[plugins,omgeving]
```

## Usage

(Arguments between `< >` are required, arguments between `[ ]` are optional)

### Upload

```bash
edwh file.upload <path_to_file> --server [str]  --max-downloads [int] --max-days [int] --encrypt [str]
```

- `path_to_file`: which file to upload
- `server` is `files.edwh.nl` by default, but can be any `transfer.sh` instance.
- `max-downloads`: how often can the file be downloaded?
- `max-days`: for how long can the file be downloaded?
- `encrypt`: secret to encrypt the file with

This command outputs the upload status code, file url and deletion url.

### Download

```bash
edwh file.upload <url> --decrypt [str] --output-file [str]
```

- `url`: file url from `file.upload`
- `decrypt`: if `--encrypt` is used in `file.upload`, the same secret can be used to decrypt the file.
- `output-file`: where to store the download

### Delete

```bash
edwh file.upload <url>
```

- `url`: deletion url from `file.upload`

## License

`edwh-files-plugin` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
