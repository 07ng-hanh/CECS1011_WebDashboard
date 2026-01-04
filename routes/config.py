from fastapi import APIRouter, Depends
import asyncpg
from starlette.responses import PlainTextResponse, JSONResponse

from dependency_injection import get_pgpool
from datamodels import WarehouseConfig
rt = APIRouter()

@rt.get("/get-warehouse-config")
async def get_warehouse_config(keys: list[str], pg: asyncpg.pool.Pool = Depends(get_pgpool)):
    async with pg.acquire() as conn:
        db_out_raw = await conn.fetch("select key, value from configuration where key = any($1::varchar[])", keys)

        # Convert data type from string to the appropriate types using a Pydantic BaseModel
        return WarehouseConfig(**{prop[0]: prop[1] for prop in db_out_raw})