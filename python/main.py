"""Verify a publisher-signed XML license through the Babel native C ABI."""
import ctypes as c
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def read_cstring(path, maximum):
    with open(path, 'rb') as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum or b'\0' in data:
        raise ValueError(f'Invalid or oversized input: {path}')
    return data

def run():
    args = sys.argv[1:]
    if len(args) > 4:
        raise ValueError('Usage: main.py [license.xml [publisher-key.txt [RSA|ECDSA [feature]]]]')
    license_path, key_path, algorithm, feature = (args + [None] * 4)[:4]
    text = read_cstring(license_path or ROOT / 'demo/perpetual.xml', 1024 * 1024)
    key = read_cstring(key_path or ROOT / 'demo/publisher-key.txt', 16384)
    lib = c.CDLL(str(ROOT / '.sdk/lib/libBabelLicensingNative.dylib'))
    lib.babel_abi_version.restype = c.c_int
    lib.babel_license_load.argtypes = [c.c_char_p, c.POINTER(c.c_void_p)]
    lib.babel_license_verify.argtypes = [c.c_void_p, c.c_char_p, c.c_char_p]
    lib.babel_license_validate.argtypes = [c.c_void_p]
    lib.babel_license_feature_enabled.argtypes = [c.c_void_p, c.c_char_p]
    lib.babel_license_free.argtypes = [c.c_void_p]
    lib.babel_license_free.restype = None
    if lib.babel_abi_version() != 2:
        raise ValueError('This example requires native ABI v2')
    handle = c.c_void_p()
    status = lib.babel_license_load(text, c.byref(handle))
    if status:
        raise ValueError(f'License parsing failed (status {status})')
    try:
        status = lib.babel_license_verify(handle, (algorithm or 'RSA').encode(), key)
        if status:
            raise ValueError(f'Publisher signature verification failed (status {status})')
        status = lib.babel_license_validate(handle)
        if status:
            raise ValueError(f'Runtime license validation failed (status {status}; 10=expired, 4=unsupported restriction)')
        name = feature or 'Pro'
        if not lib.babel_license_feature_enabled(handle, name.encode()):
            raise ValueError(f'Feature {name} is absent or expired')
        print(f'License verified. Feature {name} enabled.')
    finally:
        lib.babel_license_free(handle)

if __name__ == '__main__':
    try:
        run()
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
