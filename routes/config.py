import glide
from fastapi import APIRouter, Depends
import asyncpg
from starlette.responses import PlainTextResponse, JSONResponse

from dependency_injection import get_pgpool, get_vk
from datamodels import WarehouseConfig
rt = APIRouter()

@rt.get("/get-warehouse-config")
async def get_warehouse_config(keys: str, vk: glide.GlideClient = Depends(get_vk)):
    # keys: space-delimited keys

    if (keys == "*"):
        d = WarehouseConfig(**{})
        return WarehouseConfig(**{key: await vk.get(f"CONFIG_{key}") for key in d.model_dump().keys()})
    else:
        return WarehouseConfig(**{key: await vk.get(f"CONFIG_{key}") for key in keys.split()})
