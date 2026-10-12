"""Run PostgreSQL tests in a uniquely named, disposable Docker container.

No existing container, volume, .env, or database is used. No password is printed.
"""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import uuid

from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[1]


def main():
    name = 'campus-ci-' + uuid.uuid4().hex
    password = secrets.token_hex(32)
    created = False

    def docker(*args, check=True):
        result = subprocess.run(['docker', *args], capture_output=True, text=True)
        if check and result.returncode:
            raise RuntimeError('Docker command failed; output suppressed')
        return result

    with tempfile.TemporaryDirectory(prefix='campus-ci-') as directory:
        secret_file = Path(directory) / 'db-password'
        secret_file.write_text(password, encoding='ascii')
        secret_file.chmod(0o444)  # readable by postgres UID; parent remains private
        try:
            docker('run', '--detach', '--name', name, '--label', 'campus.purpose=ci',
                   '--mount', f'type=bind,source={secret_file},target=/run/secrets/db_password,readonly',
                   '--tmpfs', '/var/lib/postgresql:rw',
                   '--publish', '127.0.0.1::5432',
                   '--env', 'POSTGRES_DB=campus_ci', '--env', 'POSTGRES_USER=campus_ci',
                   '--env', 'POSTGRES_PASSWORD_FILE=/run/secrets/db_password',
                   'postgres:18')
            created = True
            for _ in range(90):
                result = docker('exec', name, 'pg_isready', '-h', '127.0.0.1',
                                '-U', 'campus_ci', '-d', 'campus_ci', check=False)
                if result.returncode == 0:
                    break
                time.sleep(1)
            else:
                raise RuntimeError('CI PostgreSQL readiness timeout')
            info = json.loads(docker('inspect', name).stdout)[0]
            port = int(info['NetworkSettings']['Ports']['5432/tcp'][0]['HostPort'])
            url = URL.create('postgresql+pg8000', username='campus_ci', password=password,
                             host='127.0.0.1', port=port, database='campus_ci').render_as_string(hide_password=False)
            env = dict(os.environ, DATABASE_URL=url, TEST_DATABASE_URL=url,
                       PYTHONIOENCODING='utf-8', PYTHONPATH=str(ROOT), CAMPUS_LOAD_DOTENV='0')
            # Never inherit another application's file-based configuration.
            for key in ('DB_PASSWORD_FILE', 'DB_HOST', 'DB_PORT', 'DB_USER', 'DB_NAME'):
                env.pop(key, None)
            for args in (['-m', 'flask', '--app', 'run', 'db', 'upgrade'],
                         ['-m', 'flask', '--app', 'run', 'db', 'check'],
                         ['-m', 'pytest', '-q', '--postgres', '-p', 'no:cacheprovider',
                          '--basetemp', str(Path(directory) / 'pytest')]):
                result = subprocess.run([sys.executable, *args], cwd=ROOT, env=env,
                                        capture_output=True, text=True, encoding='utf-8', errors='replace')
                print((result.stdout + result.stderr).replace(url, '[DATABASE_URL]').replace(password, '[REDACTED]'), flush=True)
                if result.returncode:
                    raise RuntimeError('CI verification failed')
            print('Isolated PostgreSQL CI checks passed.')
        finally:
            if created:
                # Only this invocation's new UUID-named container; no named volumes exist.
                docker('rm', '--force', name)
            secret_file.chmod(0o600)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'CI PostgreSQL failed: {type(error).__name__}; sensitive details suppressed.')
        sys.exit(1)
