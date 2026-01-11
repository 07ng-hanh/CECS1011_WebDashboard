from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse
from http import HTTPStatus
from dependency_injection import get_pgpool
from datamodels import ProduceInfoForm
import asyncpg
rt = APIRouter()

@rt.get("/list-produces")
async def list_produces(page: int = 1, limit: int = 20, query: str = "", pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):
    async with pgpool.acquire() as con:
        try:
            # return JSONResponse([{"username": user["username"], "isadmin": user["is_admin"]} for user in users])
            produces = await con.fetch("select id, harvest_type_name, shelf_life, thresh_temp_lo, thresh_temp_hi, thresh_humidity_lo, thresh_humidity_hi, thresh_co2_lo, thresh_co2_hi from produceinfo where harvest_type_name ilike $1 order by id limit $2 offset $3",
                                       f'%{query}%', limit, (page - 1) * limit)
            produces_json = [[p[0], ProduceInfoForm(harvest_type_name=p[1], shelf_life=p[2], thresh_temp_lo=p[3], thresh_temp_hi=p[4], thresh_humidity_lo=p[5], thresh_humidity_hi=p[6], thresh_co2_lo=p[7], thresh_co2_hi=p[8]).model_dump()] for p in produces]
            return JSONResponse(produces_json)
        except BaseException as e:
            print(e)
            return JSONResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR)


@rt.get("/list-all-produces-simple")
async def list_all_produces_simple(pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):
    async with pgpool.acquire() as con:
        try:
            produces = await con.fetch("select id, harvest_type_name from produceinfo")
            return JSONResponse([(produce, id) for (produce, id) in produces])
        except Exception as e:
            print(e)
            return JSONResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR)


@rt.get("/get-thresholds")
async def get_thresholds(produce_id: int, pgpool = Depends(get_pgpool)):
    async with pgpool.acquire() as conn:
        row = await conn.fetch("select harvest_type_name, shelf_life, thresh_temp_lo, thresh_temp_hi, thresh_humidity_lo, thresh_humidity_hi, thresh_co2_lo, thresh_co2_hi from produceinfo where id = $1", produce_id)
        return ProduceInfoForm.from_list(row[0])
