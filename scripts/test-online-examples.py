import sys
#!/usr/bin/env python3
"""Compile/run all four bindings against the loopback protocol fixture."""
import importlib.util
import os
from pathlib import Path
import subprocess
import threading

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fixture',ROOT/'scripts/demo-service.py')
fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
server = fixture.make_server(ROOT/'demo',interval=4,faults=True)
thread = threading.Thread(target=server.serve_forever,daemon=True); thread.start()
env = dict(os.environ, BABEL_SERVICE_URL=f'http://127.0.0.1:{server.server_port}/',
    BABEL_ALLOW_LOOPBACK_HTTP='1',BABEL_MACHINE_ID='native-example-machine',BABEL_ALGORITHM='RSA',
    BABEL_PUBLISHER_KEY_FILE=str(ROOT/'demo/publisher-key.txt'))
count = 0
try:
    for language in ['rust','go','cpp','python']:
        for mode,user,accepted,message,machine in [
            ('activation','demo-activation',True,'cleaned up','native-example-machine'),
            ('floating','demo-floating',True,'heartbeat renewed','native-example-machine'),
            ('activation','demo-denied',False,'status 14','native-example-machine'),
            ('activation','demo-activation',False,'status 16','another-machine'),
            ('floating','demo-unsupported-online',False,'status 4','native-example-machine'),
            ('floating','demo-heartbeat-denied',False,'status 15','native-example-machine'),
        ]:
            server.fixture_events.clear()
            runenv=dict(env,BABEL_USER_KEY=user,BABEL_MACHINE_ID=machine,BABEL_CLIENT_ID='example-test-'+language)
            result=subprocess.run([sys.executable,str(ROOT/'scripts/run-example.py'),language,'--online',mode],cwd=ROOT,env=runenv,
                text=True,capture_output=True,timeout=120)
            output=result.stdout+result.stderr
            if (result.returncode==0)!=accepted or message not in output:
                raise SystemExit(f'{language} {mode} {user}: unexpected result {result.returncode}\n{output}')
            events = server.fixture_events
            if accepted:
                expected = ['activate','validate','deactivate'] if mode=='activation' else ['request','heartbeat','heartbeat','release']
                if events != expected or 'cleaned up' not in output:
                    raise SystemExit(f'{language}: incomplete lifecycle: {events}\n{output}')
                if mode=='floating' and output.count('heartbeat renewed')!=2:
                    raise SystemExit(f'{language}: expected exactly two renewals\n{output}')
            elif user=='demo-heartbeat-denied':
                if events!=['request','heartbeat','release'] or 'heartbeat renewed' in output:
                    raise SystemExit(f'{language}: denied renewal was not stopped/cleaned up: {events}\n{output}')
            count+=1
        print(language+': activation, validation, deactivation, floating acquire/renew/release and refusal paths passed')
    print(f'{count} online language example scenarios passed')
finally:
    server.shutdown();server.server_close();thread.join()
