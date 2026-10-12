import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
    MAX_CONTENT_LENGTH = 16 * 1024

