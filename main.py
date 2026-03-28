# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncpg

# Import your new routers
from routers import combat, characters

DATABASE_URL = "postgresql://admin:password@localhost:5432/dnd_engine"

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Connecting to PostgreSQL...")
    app.state.pool = await asyncpg.create_pool(DATABASE_URL)
    yield
    print("Closing PostgreSQL connection...")
    await app.state.pool.close()

app = FastAPI(lifespan=lifespan, title="D&D AI Physics Engine")

# Mount the routers to the main application
# This automatically prefixes the routes (e.g., /combat/attack)
app.include_router(combat.router, prefix="/combat", tags=["Combat"])
app.include_router(characters.router, prefix="/character", tags=["Characters"])