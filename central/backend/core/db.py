from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from core.config import settings

# 1. Use NullPool to prevent event loop connection collisions across tasks/threads
engine = create_async_engine(
    settings.DATABASE_URL, 
    poolclass=NullPool,
    # pool_pre_ping is not needed with NullPool since connections aren't kept alive
)

# 2. Configure the async session maker
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False # CRITICAL for async: prevents lazy-loading crashes after commits
)

Base = declarative_base()

# 3. Async dependency for FastAPI routes
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()