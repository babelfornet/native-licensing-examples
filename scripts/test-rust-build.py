#!/usr/bin/env python3
"""Regression: a custom Cargo target and a relocated checkout run the new binary."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def main(source=ROOT):
    with tempfile.TemporaryDirectory(prefix='babel-rust-build-') as temporary:
        base=Path(temporary);first=base/'checkout';moved=base/'moved-checkout';target=base/'cargo-artifacts'
        (first/'scripts').mkdir(parents=True)
        shutil.copy2(source/'scripts/run-example.py',first/'scripts/run-example.py')
        shutil.copytree(source/'rust',first/'rust',ignore=shutil.ignore_patterns('target'))
        shutil.copytree(source/'.sdk',first/'.sdk')
        shutil.copytree(source/'demo',first/'demo')
        env=dict(os.environ,CARGO_TARGET_DIR=str(target))
        def run(root,label):
            result=subprocess.run([sys.executable,'scripts/run-example.py','rust'],cwd=root,env=env,
                text=True,capture_output=True,timeout=120)
            output=result.stdout+result.stderr
            if result.returncode or 'Feature Pro enabled' not in output:
                raise RuntimeError(label+' failed:\n'+output)
            if (root/'rust/target').exists():
                raise RuntimeError('Runner ignored CARGO_TARGET_DIR')
            print(label+': passed')
        run(first,'Rust custom Cargo target, fresh checkout')
        first.rename(moved)
        run(moved,'Rust moved checkout with the same Cargo cache')

if __name__=='__main__':
    main(Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT)
