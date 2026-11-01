#!/usr/bin/env python3
"""Download the pinned native SDK preview, check its SHA-256, and unpack safely."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import sys
import tarfile
import tempfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 64 * 1024 * 1024

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Use a previously downloaded SDK archive offline')
    args = parser.parse_args()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('This preview SDK requires an Apple Silicon Mac. Windows, Linux and Intel builds are not published yet.')
    if int(platform.mac_ver()[0].split('.')[0]) < 15:
        raise ValueError('This preview SDK targets macOS 15 or later.')
    manifest = json.loads((ROOT / 'sdk/manifest.json').read_text())
    destination = ROOT / '.sdk'
    if destination.exists():
        info_path = destination / 'BUILD-INFO.json'
        if info_path.is_file() and json.loads(info_path.read_text()).get('sourceCommit') == manifest['sourceCommit']:
            print(f"SDK {manifest['version']} already installed in {destination}")
            return
        raise ValueError('Move the existing .sdk directory aside before installing this SDK version.')
    if args.archive:
        with args.archive.open('rb') as stream:
            data = stream.read(MAX_BYTES + 1)
    else:
        print(f"Downloading SDK {manifest['version']} for macOS arm64")
        with urlopen(manifest['url'], timeout=60) as stream:
            data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES or hashlib.sha256(data).hexdigest() != manifest['sha256']:
        raise ValueError('SDK archive size or SHA-256 does not match the pinned manifest.')
    with tempfile.TemporaryDirectory(prefix='.native-sdk-', dir=ROOT) as temporary:
        stage = Path(temporary) / 'sdk'
        stage.mkdir()
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            members = archive.getmembers()
            if len(members) > 100 or sum(m.size for m in members) > MAX_BYTES:
                raise ValueError('SDK archive exceeds extraction limits.')
            for member in members:
                path = PurePosixPath(member.name)
                if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                    raise ValueError('SDK archive contains an unsafe entry.')
                target = stage.joinpath(*path.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = archive.extractfile(member)
                    if source is None:
                        raise ValueError('SDK archive entry cannot be read.')
                    with source, target.open('wb') as output:
                        shutil.copyfileobj(source, output)
                    os.chmod(target, member.mode & 0o777)
        info = json.loads((stage / 'BUILD-INFO.json').read_text())
        if info.get('abi') != 2 or info.get('sourceCommit') != manifest['sourceCommit']:
            raise ValueError('SDK build information does not match the manifest.')
        stage.rename(destination)
    print(f"Installed SDK {manifest['version']} in {destination}")

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, tarfile.TarError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
