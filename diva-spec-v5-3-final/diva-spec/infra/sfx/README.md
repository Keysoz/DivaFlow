# 7-Zip SFX module

`7zSD.sfx` is the installer self-extractor from the LZMA SDK 25.01 published by
Igor Pavlov at https://www.7-zip.org/sdk.html. The SDK is public domain; see
`LZMA-SDK.txt`.

It is vendored so the installer can be built offline and byte-for-byte
reproducibly. `scripts/build-installer.sh` prepends `config.txt` and appends the
payload archive:

    cat 7zSD.sfx config.txt payload.7z > DivaStore-Setup-<version>.exe

The module extracts the payload to a temporary folder, runs `setup.cmd` there and
waits for it to exit. `setup.cmd` copies the large files to `C:\DivaStore`
before returning, because the temporary folder is removed afterwards.
