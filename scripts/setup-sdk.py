#!/usr/bin/env python3
"""Install a SHA-256-pinned platform SDK archive safely. Downloads stay disabled until release."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import stat
import sys
import tarfile
import tempfile
from urllib.request import urlopen
import zipfile

ROOT=Path(__file__).resolve().parents[1]
MAX_BYTES=64*1024*1024

def target():
    system={'Darwin':'macos','Linux':'linux','Windows':'windows'}.get(platform.system())
    architecture={'x86_64':'x64','amd64':'x64','arm64':'arm64','aarch64':'arm64'}.get(platform.machine().lower())
    if not system or not architecture:raise ValueError('Unsupported OS or architecture')
    return system+'-'+architecture

def safe_path(stage,name):
    if '\\' in name or ':' in name:raise ValueError('Unsafe archive path')
    path=PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe archive path')
    return stage.joinpath(*path.parts)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,help='Use the matching supplied SDK archive offline')
    args=parser.parse_args()
    manifest=json.loads((ROOT/'sdk/manifest.json').read_text())
    platform_id=target()
    package=manifest.get('packages',{}).get(platform_id)
    if not package or package.get('pending',False):
        raise ValueError(f'No tested SDK archive is prepared for {platform_id} yet')
    if not manifest.get('available',False) and not args.archive:
        raise ValueError('The native ABI is unreleased; automatic downloads are disabled. Use the matching supplied archive with --archive.')
    if platform.system()=='Darwin' and int(platform.mac_ver()[0].split('.')[0])<int(package.get('minimumMacOS','15').split('.')[0]):
        raise ValueError('SDK requires macOS '+package['minimumMacOS']+' or later')
    if platform.system()=='Linux':
        libc,version=platform.libc_ver()
        minimum=package.get('minimumGlibc')
        if libc!='glibc' or (minimum and tuple(map(int,version.split('.')))<tuple(map(int,minimum.split('.')))):
            raise ValueError('This Linux SDK requires glibc '+str(minimum)+' or later; musl is not supported')
    destination=ROOT/'.sdk'
    if destination.exists():
        receipt=destination/'.archive-sha256'
        if receipt.is_file() and receipt.read_text().strip()==package['sha256']:
            print(f'SDK already installed for {platform_id}');return
        raise ValueError('Move the existing .sdk aside before installing another SDK package')
    if args.archive:
        with args.archive.open('rb') as stream:data=stream.read(MAX_BYTES+1)
    else:
        with urlopen(package['url'],timeout=60) as stream:data=stream.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES or hashlib.sha256(data).hexdigest()!=package['sha256']:
        raise ValueError('SDK size or SHA-256 does not match the pinned platform manifest')
    with tempfile.TemporaryDirectory(prefix='.native-sdk-',dir=ROOT) as temporary:
        stage=Path(temporary)/'sdk';stage.mkdir()
        names=set()
        def name(path):
            canonical=str(path.relative_to(stage)).casefold()
            if canonical in names:raise ValueError('Duplicate archive path')
            names.add(canonical)
        if zipfile.is_zipfile(io.BytesIO(data)):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                members=archive.infolist()
                if len(members)>100 or sum(m.file_size for m in members)>MAX_BYTES:
                    raise ValueError('SDK extraction limits exceeded')
                for member in members:
                    path=safe_path(stage,member.filename);name(path)
                    mode=member.external_attr>>16
                    if stat.S_ISLNK(mode):raise ValueError('SDK symlinks are not permitted')
                    if member.is_dir():path.mkdir(parents=True,exist_ok=True)
                    else:
                        path.parent.mkdir(parents=True,exist_ok=True)
                        with archive.open(member) as source,path.open('wb') as output:shutil.copyfileobj(source,output)
        else:
            with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
                members=archive.getmembers()
                if len(members)>100 or sum(m.size for m in members)>MAX_BYTES:
                    raise ValueError('SDK extraction limits exceeded')
                for member in members:
                    path=safe_path(stage,member.name);name(path)
                    if not (member.isfile() or member.isdir()):raise ValueError('Unsafe SDK entry type')
                    if member.isdir():path.mkdir(parents=True,exist_ok=True)
                    else:
                        path.parent.mkdir(parents=True,exist_ok=True)
                        source=archive.extractfile(member)
                        if source is None:raise ValueError('Unreadable SDK entry')
                        with source,path.open('wb') as output:shutil.copyfileobj(source,output)
                        os.chmod(path,member.mode&0o777)
        info=json.loads((stage/'BUILD-INFO.json').read_text())
        if any(info.get(field)!=package.get(field) for field in ('abi','sourceCommit','platform','packageVersion')):
            raise ValueError('SDK metadata does not match the pinned platform manifest')
        runtime=[p for p in stage.rglob('*') if p.is_file() and (p.suffix in ('.dylib','.dll') or '.so' in p.name)]
        if len(runtime)!=1 or [runtime[0].name]!=package['runtimeLibraries']:
            raise ValueError('SDK must contain exactly one runtime library; Botan is embedded')
        if not (stage/'include/babel/babel_licensing.h').is_file():raise ValueError('SDK public header is absent')
        (stage/'.archive-sha256').write_text(package['sha256']+'\n')
        stage.rename(destination)
    print('Installed SDK for '+platform_id)

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,tarfile.TarError,zipfile.BadZipFile) as error:
        print(error,file=sys.stderr);sys.exit(1)
