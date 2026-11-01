#!/usr/bin/env python3
"""Loopback-only REST protocol fixture. Not a licensing server or license issuer.

Signed payloads are read from --fixtures. No signing private key is required.
Only disposable demo user keys are accepted. Do not enter customer credentials.
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import time


def make_server(fixtures, port=0, interval=4, faults=False):
    fixtures = Path(fixtures)
    lock = threading.Lock()
    events = []
    leases = {}
    activations = set()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log credentials or tokens.

        def answer(self, value, status=200):
            data = value if isinstance(value, bytes) else json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 32768:
                    return self.answer({}, 400)
                value = json.loads(self.rfile.read(length))
                if self.path == '/v1/auth/login':
                    user = value.get('password', '')
                    if value.get('username') != '' or not user.startswith('demo-'):
                        return self.answer({}, 401)
                    return self.answer({'token': 'fixture-' + user, 'expiresIn': {'seconds': 60, 'nanos': 0}})
                bearer = self.headers.get('Authorization', '')
                if not bearer.startswith('Bearer fixture-demo-'):
                    return self.answer({}, 401)
                user = bearer.removeprefix('Bearer fixture-')
                identity = (value['machineId'], value['clientId'])
                if not all(identity) or not isinstance(value.get('clientName'), str):
                    return self.answer({}, 400)
                endpoint = self.path.removeprefix('/v1/license/')
                if endpoint in ('activate', 'validate', 'request', 'deactivate') and value.get('userKey') != user:
                    return self.answer({}, 403)
                with lock:
                    events.append(endpoint)
                    now = int(time.time())
                    if endpoint in ('activate', 'validate', 'request'):
                        activation = endpoint != 'request'
                        if user == 'demo-denied':
                            return self.answer({'success': False, 'granted': False})
                        if endpoint == 'validate' and identity not in activations:
                            return self.answer({}, 403)
                        if not activation and any(expiry > time.time() for _, expiry, _ in leases.values()):
                            return self.answer({}, 409)
                        kind = 'activation' if activation else 'floating'
                        if faults and user in ('demo-wrong-machine', 'demo-unsupported-online'):
                            kind = user.removeprefix('demo-')
                        payload = (fixtures / (kind + '.key')).read_bytes()
                        if faults and user == 'demo-tampered':
                            payload = payload[:-4] + b'!!!!'
                        token = 'fixture-seat-' + str(time.monotonic_ns())
                        if activation:
                            activations.add(identity)
                        else:
                            leases[token] = (identity, time.time() + interval, user)
                        result = {
                            'success' if activation else 'granted': True,
                            'licenseToken': token, 'tokenExpireAt': {'seconds': now + interval, 'nanos': 0},
                            'heartbeatInterval': {'seconds': interval, 'nanos': 0},
                            'activeClientCount': 1, 'maxClientCount': 1,
                            'license': {'licenseId': 'native-demo-' + kind, 'licensingMode': 1 if activation else 2,
                                        'licenseKey': list(payload)},
                        }
                        if faults:
                            if user == 'demo-missing-license':
                                del result['license']
                            elif user == 'demo-expired-token':
                                result['tokenExpireAt']['seconds'] = now - 1
                            elif user == 'demo-huge-interval':
                                result['heartbeatInterval']['seconds'] = 2**63 - 1
                            elif user == 'demo-deep-json':
                                return self.answer(b'{"a":' * 40 + b'0' + b'}' * 40)
                            elif user == 'demo-duplicate-json':
                                return self.answer(b'{"granted":true,"granted":false}')
                            elif user == 'demo-large-json':
                                return self.answer(b' ' * (2*1024*1024+1))
                            elif user == 'demo-bad-byte':
                                result['license']['licenseKey'] = [2**63 + 60]
                        return self.answer(result)
                    if endpoint == 'deactivate':
                        activations.discard(identity)
                        return self.answer({'licenseId': 'native-demo-activation'})
                    token = value.get('licenseToken', '')
                    lease = leases.get(token)
                    if not lease or lease[0] != identity:
                        return self.answer({}, 403)
                    if endpoint == 'release':
                        del leases[token]
                        return self.answer({'licenseId': 'native-demo-floating'})
                    if endpoint == 'heartbeat':
                        active = lease[1] > time.time() and lease[2] != 'demo-heartbeat-denied'
                        leases[token] = (identity, time.time() + interval, lease[2])
                        return self.answer({'active': active, 'tokenExpireAt': {'seconds': now + interval, 'nanos': 0},
                                            'heartbeatInterval': {'seconds': interval, 'nanos': 0}})
                    return self.answer({}, 404)
            except (KeyError, ValueError, OSError, TypeError):
                return self.answer({}, 400)

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.fixture_events = events  # Local test instrumentation, never an HTTP endpoint.
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=Path(__file__).resolve().parents[1] / 'demo')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = make_server(args.fixtures, args.port)
    print(f'Demo protocol fixture: http://127.0.0.1:{server.server_port}/', flush=True)
    print('Demo only: activation=demo-activation; floating=demo-floating; machine=native-example-machine', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
