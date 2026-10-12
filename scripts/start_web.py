"""Read-only schema gate: this entry point NEVER runs migrations."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from app import create_app, db


def require_current_schema():
    app = create_app()
    with app.app_context():
        expected = set(ScriptDirectory(str(ROOT / 'migrations')).get_heads())
        with db.engine.connect() as connection:
            actual = set(MigrationContext.configure(connection).get_current_heads())
        db.engine.dispose()
    if not expected or actual != expected:
        raise RuntimeError('Schema is not current')


if __name__ == '__main__':
    try:
        require_current_schema()
    except Exception:
        sys.exit('Startup refused: database unavailable or migrations pending. Run the explicit migrate service first.')
    os.execvp('gunicorn', ['gunicorn', '--bind', '0.0.0.0:8000', '--workers', '2',
                          '--worker-tmp-dir', '/tmp', '--error-logfile', '-', 'run:app'])
