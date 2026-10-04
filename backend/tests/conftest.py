import os
import pytest
os.environ.setdefault("DATABASE_URL", "sqlite://")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import Candidate, Hall, PaperSet, SeatPlan
from app.services.seed import seed_if_empty


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = TestingSession()
    seed_if_empty(db)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield db
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    return TestClient(app)


def _paper_a(db_session) -> PaperSet:
    return db_session.scalar(select(PaperSet).where(PaperSet.code == "P-A"))
