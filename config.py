import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

if os.getenv('CAMPUS_LOAD_DOTENV', '1') == '1':
    load_dotenv(Path(__file__).parent / '.env')


def database_uri():
    """A file secret explicitly selects the isolated container connection."""
    secret_file = os.getenv('DB_PASSWORD_FILE')
    if secret_file:
        password = Path(secret_file).read_text(encoding='utf-8').strip()
        if not password:
            raise RuntimeError('Database secret file is empty.')
        return URL.create('postgresql+pg8000', username=os.environ['DB_USER'],
                          password=password, host=os.environ['DB_HOST'],
                          port=int(os.getenv('DB_PORT', '5432')), database=os.environ['DB_NAME'])
    return os.getenv('DATABASE_URL')


class Config:
    SQLALCHEMY_DATABASE_URI = database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
    MAX_CONTENT_LENGTH = 16 * 1024

