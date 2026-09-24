"""App configuration"""


class Config:
    """App confs"""

    SECRET_KEY = "123"  # os.environ["SECRET_KEY"]
    DATABASE = "database.db"

    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPOnly = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # NOTE: max upload 42 MiB
    MAX_CONTENT_LENGTH = 42 * 1024 * 1024

    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 256


class DevConfig(Config):
    """Development configurations"""

    SECRET_KEY = "123"

    DEBUG = True
    TESTING = False

    MIN_PASSWORD_LENGTH = 1
    MAX_PASSWORD_LENGTH = 1


class TestConfig(DevConfig):
    """Test configurations"""

    TESTING = True
    DEBUG = False

    DATABASE = "test_database.db"
