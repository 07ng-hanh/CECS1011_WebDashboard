from http import HTTPStatus

import asyncpg.pool
from fastapi import APIRouter
from fastapi.params import Depends
from starlette.responses import JSONResponse

from datamodels import ExportOrderMinimal, PortInfo
from dependency_injection import get_pgpool
rt = APIRouter()

@rt.post("/add-shipment")
async def add_shipment(s: ExportOrderMinimal, pgpool = Depends(get_pgpool)):
    # get port lat/lon from port list
    # push order to DB
    pass

@rt.get("/search-port")
async def search_port(q: str, pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):
    if len(q) < 3:
        return JSONResponse({"msg": "query needs to have at least 3 characters."})
    try:
        async with pgpool.acquire() as conn:
            d = await conn.fetch("select id, port_name, port_lat, port_lon from ports where port_name ilike $1 or id ilike $1", q)
            portList = [PortInfo(id=row[0], port_name=row[1], port_lat=row[2], port_lon=row[3]) for row in d]
            return portList
    except:
        return JSONResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR)