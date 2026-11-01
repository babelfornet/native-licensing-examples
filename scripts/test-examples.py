import sys
"""Run each language against accepted and rejected signed files."""
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as temp:
    tampered = Path(temp) / 'tampered.xml'
    tampered.write_text((ROOT / 'demo/perpetual.xml').read_text().replace('Example application developer', 'Changed application developer'))
    wrong_key = Path(temp) / 'wrong-key.txt'
    wrong_key.write_text('AA==')
    count = 0
    for language in ['python', 'cpp', 'go', 'rust']:
        cases = [
            ([], True, 'enabled'),
            (['demo/trial.xml'], True, 'enabled'),
            (['demo/expired.xml'], False, 'status 10'),
            (['demo/no-feature.xml'], False, 'absent'),
            (['demo/restricted.xml'], False, 'status 4'),
            ([str(tampered)], False, 'status 3'),
            (['demo/perpetual.xml', str(wrong_key)], False, 'status 3'),
        ]
        for args, accepted, message in cases:
            result = subprocess.run([sys.executable,str(ROOT/'scripts/run-example.py'),language,*args], cwd=ROOT, text=True, capture_output=True)
            output = result.stdout + result.stderr
            if (result.returncode == 0) != accepted or message not in output:
                raise SystemExit(f'{language} {args}: unexpected result {result.returncode}\n{output}')
            count += 1
        print(f'{language}: 7 license scenarios passed')
print(f'{count} public example scenarios passed')
