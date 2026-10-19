"""Run defense integration checks in a disposable, low-memory native PostgreSQL.

Does not read or modify the application database. Stops its own cluster on exit.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser()
parser.add_argument('--postgres-bin', type=Path, default=Path('C:/Program Files/PostgreSQL/15/bin'))
parser.add_argument('--ui', action='store_true', help='Serve an isolated UI pilot on port 8000 until stopped')
parser.add_argument('--suite', choices=['defense','documents','release','preparation'], default='defense')
args = parser.parse_args()
repo = Path(__file__).resolve().parents[2]
backend = repo/'backend'
python = backend/'.venv/Scripts/python.exe' if os.name == 'nt' else backend/'.venv/bin/python'
assert python.is_file(), 'Backend environment is required.'
for name in ['initdb', 'pg_ctl']:
    assert (args.postgres_bin/(name + ('.exe' if os.name == 'nt' else ''))).is_file()
root = Path(tempfile.mkdtemp(prefix='socratia-defense-test-'))
data = root/'data'
password = secrets.token_hex(24)
pwfile = root/'password.txt'
pwfile.write_text(password, encoding='ascii')
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
flags = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
def pg(name, *arguments):
    binary = args.postgres_bin/(name + ('.exe' if os.name == 'nt' else ''))
    # Native Windows PostgreSQL descendants can retain inherited pipe handles.
    # A regular log file prevents communicate() waiting for those descendants.
    with (root/'launcher.log').open('a', encoding='utf-8') as log:
        result = subprocess.run([str(binary), *map(str, arguments)],
            stdout=log, stderr=log, timeout=60, **flags)
    if result.returncode:
        print((root/'launcher.log').read_text(encoding='utf-8', errors='replace')[-2500:])
        raise RuntimeError(f'{name} failed. Log directory: {root}')

started = False
result = None
try:
    pg('initdb', '-D', data, '-U', 'socratia', '--pwfile', pwfile,
       '--auth', 'scram-sha-256', '--encoding', 'UTF8', '--locale', 'C')
    pwfile.unlink()
    pg('pg_ctl', 'start', '-D', data, '-l', root/'postgres.log', '-w', '-o',
       f'-h 127.0.0.1 -p {port} -c shared_buffers=32MB -c max_connections=15 -c work_mem=2MB')
    started = True
    env = os.environ.copy()
    # Only newly generated credentials for this dedicated test cluster.
    env['SOCRATIA_TEST_PASSWORD'] = password
    env['SOCRATIA_TEST_PORT'] = str(port)
    setup = """import os, psycopg
password=os.environ['SOCRATIA_TEST_PASSWORD']; port=int(os.environ['SOCRATIA_TEST_PORT'])
with psycopg.connect(host='127.0.0.1',port=port,user='socratia',password=password,dbname='postgres',autocommit=True) as db:
    db.execute('CREATE DATABASE socratia_defense_test')
with psycopg.connect(host='127.0.0.1',port=port,user='socratia',password=password,dbname='socratia_defense_test',autocommit=True) as db:
    db.execute('CREATE DOMAIN vector AS text')
"""
    subprocess.run([str(python), '-c', setup], env=env, cwd=backend, check=True, **flags)
    env['TEST_DATABASE_URL'] = f'postgresql+psycopg://socratia:{password}@127.0.0.1:{port}/socratia_defense_test'
    env.pop('SOCRATIA_TEST_PASSWORD')
    env.pop('SOCRATIA_TEST_PORT')
    output = repo/'artifacts/defense-validation'
    output.mkdir(parents=True, exist_ok=True)
    print('Isolated test cluster ready; 32 MB shared buffers. No paid providers.', flush=True)
    if args.ui:
        ui_setup = setup.replace('socratia_defense_test', 'socratia_ui_test')
        ui_env = os.environ.copy()
        ui_env['SOCRATIA_TEST_PASSWORD'] = password
        ui_env['SOCRATIA_TEST_PORT'] = str(port)
        subprocess.run([str(python), '-c', ui_setup], cwd=backend, env=ui_env, check=True, **flags)
        runtime = root/'ui-runtime.json'
        runtime.write_text(json.dumps({'root':str(root),'port':port,'password':password}))
        ui_env['LOCAL_TTS_ENABLED'] = 'false'
        ui_env['VOICE_TTS_ENABLED'] = 'false'
        print(f'UI pilot input document: {root / "tesis-validacion.docx"}',flush=True)
        result = subprocess.run([str(python), 'scripts/validation_server.py', '--runtime', str(runtime)],
            cwd=backend, env=ui_env, **flags)
    else:
        selected = (['tests/test_documents.py','tests/test_presentation_materials.py','tests/test_presentation_export.py']
            if args.suite == 'documents' else [
                'tests/test_simulation_sessions.py', 'tests/test_simulation_closure.py',
                'tests/test_voice_cancellation.py', 'tests/test_local_voice.py',
                'tests/test_voice_session_flow.py','tests/test_gemini_transcription.py', 'tests/test_voice_pipeline.py'])
        if args.suite == 'preparation':
            selected = ['tests/test_preparation_tasks.py','tests/test_documents.py','tests/test_evaluation_resume.py']
        if args.suite == 'release':
            selected = [str(path.relative_to(backend)) for path in sorted((backend/'tests').glob('test_*.py'))
                if '_real' not in path.name]
            selected += ['tests/modules/p4_gestion_evaluacion_resultados']
        result = subprocess.run([str(python), '-m', 'pytest',
            *selected, '-q', '-ra', f'--junitxml={output / (args.suite+"-tests.xml")}'], cwd=backend, env=env, **flags)
    (output/('ui-run.json' if args.ui else args.suite+'-run.json')).write_text(json.dumps({'exit_code':result.returncode,
        'isolated_database':True,'external_providers':'test doubles','cluster_directory':str(root)},indent=2))
    report = output/(args.suite+'-tests.xml')
    if report.exists() and not args.ui:
        for suite in ET.parse(report).getroot().iter('testsuite'):
            print({key:suite.get(key) for key in ['tests','failures','errors','skipped','time']},flush=True)
finally:
    if pwfile.exists(): pwfile.unlink()
    if started:
        pg('pg_ctl', 'stop', '-D', data, '-m', 'fast', '-w')
        print('Temporary PostgreSQL stopped.', flush=True)
sys.exit(result.returncode if result else 1)
