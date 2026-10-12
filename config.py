"""App configuration"""

import os


class Config:
    """App confs"""

    try:
        SECRET_KEY = os.environ["SECRET_KEY"]
    except KeyError:
        raise KeyError("SECRET_KEY missing from env")

    DATABASE = "database.db"

    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # NOTE: max upload 42 MiB
    MAX_PDF_SIZE = 42 * 1024 * 1024

    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 256

    MIN_USERNAME_LENGTH = 2
    MAX_USERNAME_LENGTH = 20


class DevConfig(Config):
    """Development configurations"""

    SECRET_KEY = "123"

    DEBUG = True
    TESTING = False

    MIN_PASSWORD_LENGTH = 1


class TestConfig(DevConfig):
    """Test configurations"""

    TESTING = True
    DEBUG = False

    DATABASE = "test_database.db"
