from functools import lru_cache
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings

class Base(DeclarativeBase):
    pass

@lru_cache
def engine():
    url = settings().database_url
    result = create_engine(url, pool_pre_ping=True)
    if url.startswith('sqlite'):
        @event.listens_for(result, 'connect')
        def sqlite_fk(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    return result

def get_db():
    with sessionmaker(bind=engine(), expire_on_commit=False)() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
