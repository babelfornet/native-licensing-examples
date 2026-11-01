#!/usr/bin/env python3
"""Run all language lifecycles against a separately installed Babel Licensing Service.

Use dedicated test licenses enabling Pro. This script activates/deactivates
machines and acquires/releases floating tokens; it never creates licenses or
needs an administrator API key. See the README for environment configuration.
"""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    for name in ('BABEL_SERVICE_URL', 'BABEL_PUBLISHER_KEY_FILE',
                 'BABEL_ACTIVATION_USER_KEY', 'BABEL_FLOATING_USER_KEY'):
        if not os.environ.get(name):
            raise SystemExit(f'Set {name}; use dedicated test licenses enabling Pro')
    timeout = int(os.environ.get('BABEL_TEST_TIMEOUT_SECONDS', '900'))
    count = 0
    for language in ('rust', 'go', 'cpp', 'python'):
        for mode in ('activation', 'floating'):
            user_key = os.environ['BABEL_'+mode.upper()+'_USER_KEY']
            env = dict(os.environ, BABEL_USER_KEY=user_key,
                       BABEL_CLIENT_ID='real-service-example-'+language)
            result = subprocess.run(
                [sys.executable, str(ROOT/'scripts/run-example.py'), language, '--online', mode],
                cwd=ROOT, env=env, text=True, capture_output=True, timeout=timeout)
            output = result.stdout + result.stderr
            # A service/client error must never expose a user key in the test log.
            for field in ('BABEL_ACTIVATION_USER_KEY', 'BABEL_FLOATING_USER_KEY'):
                output = output.replace(os.environ[field], '<redacted-test-user-key>')
            if result.returncode or 'cleaned up' not in output:
                raise SystemExit(f'{language} {mode}: failed ({result.returncode})\n{output}')
            if 'signed license valid; Pro enabled' not in output:
                raise SystemExit(f'{language} {mode}: no verified entitlement\n{output}')
            if mode == 'floating' and output.count('heartbeat renewed') != 2:
                raise SystemExit(f'{language}: expected two successful renewals\n{output}')
            count += 1
            print(f'{language} {mode}: signature, Pro and cleanup passed', flush=True)
    print(f'{count} real-service language lifecycles passed', flush=True)

if __name__ == '__main__':
    main()
