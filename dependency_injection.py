# Dependency Injection allows sharing the database connection pool and session store
# client from the main module to the submodules
from glide import GlideClient
import asyncpg

vk1: GlideClient = None
pgpool: asyncpg.pool.Pool = None

async def get_vk():
    return vk1

async def get_pgpool():
    return pgpool