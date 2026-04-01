import os

os.environ.setdefault("APP_DATABASE_URL", "sqlite:///./test_import_bootstrap.db")
os.environ.setdefault("APP_DATABASE_BOOTSTRAP_MODE", "create_all")
os.environ.setdefault("APP_AUTH_ENABLED", "false")
