"""Start/stop an isolated development PostgreSQL cluster on Windows.

No existing PostgreSQL service or database is modified.
"""
import argparse
import os
from pathlib import Path
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
DATA = LOCAL / 'postgres-data'
PORT = '55432'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'stop'])
    parser.add_argument('--bin', type=Path, default=Path('C:/Program Files/PostgreSQL/18/bin'))
    args = parser.parse_args()
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

    def run(tool, *arguments, check=True, env=None, capture_output=False):
        executable = args.bin / (tool + ('.exe' if os.name == 'nt' else ''))
        return subprocess.run([str(executable), *map(str, arguments)], check=check,
                              creationflags=flags, env=env, capture_output=capture_output)

    if args.action == 'stop':
        if (DATA / 'PG_VERSION').exists():
            run('pg_ctl', '-D', DATA, '-m', 'fast', '-w', 'stop')
        return
    LOCAL.mkdir(exist_ok=True)
    password_file = LOCAL / 'db-password'
    if not (DATA / 'PG_VERSION').exists():
        if not password_file.exists():
            password_file.write_text(secrets.token_hex(24), encoding='ascii')
        run('initdb', '-D', DATA, '-U', 'university', '-A', 'scram-sha-256',
            '--pwfile', password_file, '--encoding=UTF8')
    if not password_file.exists():
        raise SystemExit('Missing .local/db-password. Restore it before starting this cluster.')
    status = run('pg_ctl', '-D', DATA, 'status', check=False, capture_output=True)
    if status.returncode != 0:
        run('pg_ctl', '-D', DATA, '-l', LOCAL / 'postgres.log',
            '-o', f'-h 127.0.0.1 -p {PORT}', '-w', 'start')
    password = password_file.read_text(encoding='ascii').strip()
    env = dict(os.environ, PGPASSWORD=password)
    connection = ['-h', '127.0.0.1', '-p', PORT, '-U', 'university', '-d', 'postgres']
    result = run('psql', *connection, '-tAc', "SELECT 1 FROM pg_database WHERE datname='university'",
                 env=env, capture_output=True)
    if result.stdout.strip() != b'1':
        run('createdb', '-h', '127.0.0.1', '-p', PORT, '-U', 'university', 'university', env=env)
    dotenv = ROOT / '.env'
    if not dotenv.exists():
        dotenv.write_text(f'DATABASE_URL=postgresql+pg8000://university:{password}@127.0.0.1:{PORT}/university\n', encoding='utf-8')
    print(f'Local PostgreSQL is ready at 127.0.0.1:{PORT}. Existing .env is preserved.')


if __name__ == '__main__':
    main()
