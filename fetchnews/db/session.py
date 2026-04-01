from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from fetchnews.db.base import Base


def create_engine_and_factory(database_url: str) -> tuple[object, sessionmaker[Session]]:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(
        database_url,
        future=True,
        connect_args=connect_args,
        pool_pre_ping=not database_url.startswith("sqlite"),
    )
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return engine, factory


def resolve_database_bootstrap_mode(
    *,
    database_url: str,
    environment: str,
    bootstrap_mode: str,
) -> str:
    if bootstrap_mode != "auto":
        return bootstrap_mode
    if environment == "test":
        return "create_all"
    if database_url.startswith("sqlite"):
        return "create_all"
    return "skip"


def init_database(
    engine: object,
    *,
    database_url: str = "sqlite:///./fetchnews.db",
    environment: str = "development",
    bootstrap_mode: str = "auto",
) -> str:
    resolved_mode = resolve_database_bootstrap_mode(
        database_url=database_url,
        environment=environment,
        bootstrap_mode=bootstrap_mode,
    )
    if resolved_mode == "skip":
        return resolved_mode
    if resolved_mode == "create_all":
        Base.metadata.create_all(bind=engine)
        return resolved_mode
    raise ValueError(f"Unsupported database bootstrap mode: {resolved_mode}")


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = factory()
    try:
        yield session
    finally:
        session.close()
