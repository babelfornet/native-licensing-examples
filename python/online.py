"""Activation and floating through the same native C ABI used by other languages."""
import ctypes as c
import os
from pathlib import Path
import time
from main import ROOT, read_cstring, runtime_path


def run_online(args):
    if args not in (['activation'], ['floating']):
        raise ValueError('Usage: main.py --online activation|floating')
    mode = args[0]
    def setting(name, default=None):
        value = os.environ.get(name, default)
        if not value or '\0' in value:
            raise ValueError(f'Set {name}')
        return value.encode()
    lib = c.CDLL(str(runtime_path()))
    lib.babel_abi_version.restype = c.c_int
    if lib.babel_abi_version() != 2:
        raise ValueError('This example requires native ABI v2 with the online API')
    lib.babel_online_create.argtypes = [c.c_char_p]*6 + [c.c_int, c.c_uint32, c.POINTER(c.c_void_p)]
    for name in ('activate', 'request_floating'):
        getattr(lib, 'babel_online_'+name).argtypes = [c.c_void_p, c.c_char_p]
    for name in ('validate_activation','heartbeat','check','deactivate','release','free','heartbeat_after_ms'):
        getattr(lib, 'babel_online_'+name).argtypes = [c.c_void_p]
    lib.babel_online_free.restype = None
    lib.babel_online_heartbeat_after_ms.restype = c.c_int64
    lib.babel_online_feature_enabled.argtypes = [c.c_void_p, c.c_char_p]
    lib.babel_hardware_key.argtypes = [c.c_char_p, c.c_void_p, c.c_size_t]
    def success(status, operation):
        if status:
            raise ValueError(f'{operation} failed (status {status})')
    machine = os.environ.get('BABEL_MACHINE_ID')
    if not machine:
        buffer = c.create_string_buffer(4096)
        success(lib.babel_hardware_key(None,buffer,len(buffer)), 'Machine identity')
        machine = buffer.value.decode()
    key = read_cstring(os.environ.get('BABEL_PUBLISHER_KEY_FILE', ROOT/'demo/publisher-key.txt'),16384)
    handle = c.c_void_p()
    success(lib.babel_online_create(setting('BABEL_SERVICE_URL'),setting('BABEL_ALGORITHM','RSA'),key,
        machine.encode(),setting('BABEL_CLIENT_ID','native-example-python'),b'Python integration example',
        15,int(os.environ.get('BABEL_ALLOW_LOOPBACK_HTTP','0')),c.byref(handle)), 'Create online client')
    cleanup = lib.babel_online_deactivate if mode == 'activation' else lib.babel_online_release
    cleaned = False
    try:
        acquire = lib.babel_online_activate if mode == 'activation' else lib.babel_online_request_floating
        success(acquire(handle,setting('BABEL_USER_KEY')), 'Acquire '+mode)
        success(lib.babel_online_check(handle),'Check before protected work')
        if lib.babel_online_feature_enabled(handle,b'Pro') != 1:
            raise ValueError('Signed license does not enable Pro')
        print(f'{mode}: signed license valid; Pro enabled')
        if mode == 'activation':
            success(lib.babel_online_validate_activation(handle),'Validate activation with service')
        else:
            for _ in range(2):
                delay = lib.babel_online_heartbeat_after_ms(handle)
                if delay < 1:
                    raise ValueError('Floating lease is no longer active')
                time.sleep(delay / 1000)
                success(lib.babel_online_heartbeat(handle),'Renew floating lease')
                success(lib.babel_online_check(handle),'Check renewed lease')
                print('floating: heartbeat renewed')
        success(cleanup(handle),'Deactivate' if mode == 'activation' else 'Release floating seat')
        cleaned = True
        print(mode+': cleaned up; protected work is now disabled')
    finally:
        if not cleaned:
            status = cleanup(handle)
            if status not in (0,1):
                print(f'Cleanup failed (status {status}); retry with the service before reusing the seat')
        lib.babel_online_free(handle)
