# Changelog

<!--next-version-placeholder-->

## v1.1.1 (2025-03-07)

### Fix

* Show message if `pigz` is not available, warning the user about missing out on performance (once) ([`976b778`](https://github.com/educationwarehouse/edwh-files-plugin/commit/976b778abfeb79a13b7e9a0b6886b1c1a6dba4ce))

## v1.1.0 (2025-02-28)

### Feature

* Allow specifying compression level on `file.upload` ([`511d1b1`](https://github.com/educationwarehouse/edwh-files-plugin/commit/511d1b19a3a5bcdbeececd3d97751c1376ec0bd0))

## v1.0.0 (2025-02-28)

### Feature

* Allow `--compression none` to explicitly send raw or simple tar files ([`46a23ab`](https://github.com/educationwarehouse/edwh-files-plugin/commit/46a23abe703b715ff80684daa58e984c443267f2))
* Integrate custom (de)compress options with `edwh file` commands ([`8f173fe`](https://github.com/educationwarehouse/edwh-files-plugin/commit/8f173fec844401cc7b8b5bb8daea0f62034dbe1e))
* Add and test different compression options, todo: implement in actual file upload/download ([`739f05c`](https://github.com/educationwarehouse/edwh-files-plugin/commit/739f05c80ac98631297e39f2b5afc9c3829907f0))
* WIP on .zip and pigz (.gz) ([`7d25600`](https://github.com/educationwarehouse/edwh-files-plugin/commit/7d25600d974b1f44451992795727458e71a3d2ac))

### Fix

* Better error handling with missing compression ([`6e2dcba`](https://github.com/educationwarehouse/edwh-files-plugin/commit/6e2dcba34b8e9d204be9d8b80581c52d5b486b32))
* Allow `edwh file.send .` ([`4542a7a`](https://github.com/educationwarehouse/edwh-files-plugin/commit/4542a7af04c06dca560cf8972616e74dde77aa8d))
* Improved error handling on compress/decompress ([`e02e5af`](https://github.com/educationwarehouse/edwh-files-plugin/commit/e02e5af58a5d1ae6c2c5a13eee555d1d8de44d20))

### Documentation

* Added docstring to compression-related functions ([`7d40d1e`](https://github.com/educationwarehouse/edwh-files-plugin/commit/7d40d1e991d38dbeba0ed78115c1701efbb7659f))
* Added docstring to compression-related functions ([`5e7241f`](https://github.com/educationwarehouse/edwh-files-plugin/commit/5e7241faa86d0405025900f72ac1e470f63639c3))

## v0.3.2 (2024-11-21)

### Fix

* Remove unused `yarl` dependency ([`10df86c`](https://github.com/educationwarehouse/edwh-files-plugin/commit/10df86c9a59d91dab00132745261a49d91665f9c))

## v0.3.1 (2024-07-18)

### Fix

* Improved type hints, code style etc ([`1bb1c45`](https://github.com/educationwarehouse/edwh-files-plugin/commit/1bb1c451d8e8ad1fe5b918adbbe022939580d878))

## v0.3.0 (2024-07-02)

### Feature

* Use `requests_toolbelt` to also show progress bar for upload ([`f0880c7`](https://github.com/educationwarehouse/edwh-files-plugin/commit/f0880c75a166594dbd75c97b359661e403053ed3))
* Show spinning animation on slow tasks where progress bar isn't really possible (zip, upload) ([`b6d4ac7`](https://github.com/educationwarehouse/edwh-files-plugin/commit/b6d4ac7607c75bba5e32c2d9f28cfe70bbef51c3))

## v0.2.0 (2024-03-07)

### Feature

* **upload:** Allow sending (zipped) directories ([`ea59803`](https://github.com/educationwarehouse/edwh-files-plugin/commit/ea59803fc417b965d19fa6acb5cba81eec9d3916))

## v0.1.5 (2023-10-03)
### Fix
* **download:** Progress bar was unresponsive, now it works again ([`57283b4`](https://github.com/educationwarehouse/edwh-files-plugin/commit/57283b491f89dcd97956ac5d29cbb0074776e961))

## v0.1.4 (2023-09-20)
### Fix
* Re-add rich as dependency ([`dc6037a`](https://github.com/educationwarehouse/edwh-files-plugin/commit/dc6037ac03f6c897763ccf3d90ec6ecef9b5f525))

## v0.1.3 (2023-09-19)
### Performance
* Replaced rich.progress with simpler progress.Bar ([`e874297`](https://github.com/educationwarehouse/edwh-files-plugin/commit/e8742972bd6dfd3476b23a3fe14aa43fa1bda4f8))

## v0.1.2 (2023-09-19)
### Performance
* **httpx:** Replaced httpx with requests because the import was very slow (150ms) ([`b7f21c9`](https://github.com/educationwarehouse/edwh-files-plugin/commit/b7f21c968e3aa52989a88888dbfabded88a89e7d))

## v0.1.1 (2023-08-02)
### Fix
* Show download_url and delete_url for ease of use, minor refactoring ([`ac28453`](https://github.com/educationwarehouse/edwh-files-plugin/commit/ac28453bebc6769185af6517424f4d58ace566a8))

## v0.1.0 (2023-06-19)
### Feature
* Initial version ([`3d26441`](https://github.com/educationwarehouse/edwh-files-plugin/commit/3d26441ebe3ee538a02731aff8eb1df8fef9a50e))