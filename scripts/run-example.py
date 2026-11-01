#!/usr/bin/env python3
"""Build and run one binding on macOS, Linux or Windows; no runtime downloads."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('language',choices=('python','cpp','go','rust'))
    parser.add_argument('arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    system=platform.system()
    windows=system=='Windows'
    if system not in ('Darwin','Linux','Windows'):
        parser.error('Supported targets: macOS, Linux and Windows')
    runtime=ROOT/'.sdk'/('bin/BabelLicensingNative.dll' if windows else
        'lib/libBabelLicensingNative.dylib' if system=='Darwin' else 'lib/libBabelLicensingNative.so')
    if not runtime.is_file():
        parser.error('Install the matching platform SDK with scripts/setup-sdk.py first')
    build=ROOT/'.build'; build.mkdir(exist_ok=True)
    env=dict(os.environ)
    if windows:
        env['PATH']=str(ROOT/'.sdk/bin')+os.pathsep+env.get('PATH','')
    suffix='.exe' if windows else ''
    output=build/(args.language+'-example'+suffix)
    def invoke(command):
        subprocess.run([str(x) for x in command],cwd=ROOT,env=env,check=True)
    if args.language=='python':
        command=[sys.executable,'python/main.py']
    elif args.language=='cpp':
        compiler=os.environ.get('CXX') or ('cl' if windows and shutil.which('cl') else 'g++' if windows else 'c++')
        if Path(compiler).name.lower() in ('cl','cl.exe'):
            invoke([compiler,'/nologo','/std:c++20','/EHsc','/MT','/Isdk/include','cpp/main.cpp',
                '/Fo'+str(build/'cpp-example.obj'),'/Fe'+str(output),'/link',
                '/LIBPATH:'+str(ROOT/'.sdk/lib'),'BabelLicensingNative.lib'])
        else:
            command=[compiler,'-std=c++20','-Isdk/include','cpp/main.cpp','-L.sdk/lib','-lBabelLicensingNative']
            if windows:
                command+=['-static-libgcc','-static-libstdc++']
            else:
                command+=['-Wl,-rpath,'+str(ROOT/'.sdk/lib')]
            invoke(command+['-o',output])
        command=[output]
    elif args.language=='go':
        env['CGO_ENABLED']='1'
        invoke(['go','build','-o',output,'go/main.go']); command=[output]
    else:
        # Let Cargo identify the executable; CARGO_TARGET_DIR and target config
        # can place it outside rust/target/debug. The SDK location also invalidates
        # cached build-script rpath output when a checkout is moved.
        env['BABEL_NATIVE_SDK_LIB_DIR']=str(ROOT/'.sdk/lib')
        result=subprocess.run(['cargo','build','--quiet','--manifest-path','rust/Cargo.toml',
            '--message-format=json-render-diagnostics'],cwd=ROOT,env=env,check=True,
            stdout=subprocess.PIPE,text=True,encoding='utf-8')
        artifacts=[]
        for line in result.stdout.splitlines():
            if not line.strip(): continue
            record=json.loads(line)
            if (record.get('reason')=='compiler-artifact' and record.get('executable') and
                record.get('target',{}).get('name')=='babel-native-licensing-example'):
                artifacts.append(record['executable'])
        if len(artifacts)!=1:
            parser.error('Cargo did not report exactly one runnable example executable')
        command=[artifacts[0]]
    result=subprocess.run([str(x) for x in command]+args.arguments,cwd=ROOT,env=env)
    return result.returncode

if __name__=='__main__':
    try:
        sys.exit(main())
    except (OSError,ValueError,subprocess.CalledProcessError) as error:
        print(error,file=sys.stderr);sys.exit(1)
