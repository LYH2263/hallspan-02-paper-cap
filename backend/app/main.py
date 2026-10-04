from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.router import api_router
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.services.seed import seed_if_empty


def ensure_paper_set_columns() -> None:
    """create_all 不会给已存在的表补列; 这里为旧库补齐试卷套规则列。"""
    insp = inspect(engine)
    if "paper_sets" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("paper_sets")}
    ddl = {
        "is_main": "ALTER TABLE paper_sets ADD COLUMN is_main BOOLEAN NOT NULL DEFAULT FALSE",
        "max_seated": "ALTER TABLE paper_sets ADD COLUMN max_seated INTEGER NOT NULL DEFAULT 0",
        "min_seated": "ALTER TABLE paper_sets ADD COLUMN min_seated INTEGER NOT NULL DEFAULT 0",
    }
    with engine.begin() as conn:
        for col, stmt in ddl.items():
            if col not in existing:
                conn.execute(text(stmt))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_paper_set_columns()
    if settings.seed_on_empty:
        db = SessionLocal()
        try:
            seed_if_empty(db)
        finally:
            db.close()
    yield


app = FastAPI(title="HallSpan", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")
