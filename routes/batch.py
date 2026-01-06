from http import HTTPStatus
from typing import Optional
import asyncpg.pool
from fastapi import APIRouter, HTTPException, Depends
from starlette.responses import JSONResponse
from dependency_injection import get_pgpool
from datamodels import NewBatchForm, BatchInfo
import zlib
rt = APIRouter()

@rt.post("/new-batch")
async def new_batch(request: NewBatchForm, pg: asyncpg.pool.Pool = Depends(get_pgpool)) -> JSONResponse:
    try:
        async with pg.acquire() as conn:
            # todo: hash input to get 32-bit batch id
            hash_target = str(request.product_type_id) + str(request.import_datetime_utc_int) + str(request.quantity)
            batch_id = zlib.crc32(hash_target.encode())
            # todo: get expiration date from produce database
            # both shelf life and harvest are represented in milliseconds.
            exp_date = (await conn.fetch("select shelf_life from produceinfo where id = $1", request.product_type_id))[0][0] + request.import_datetime_utc_int
            await conn.execute("insert into batchinfo (batch_id, produce_type_id, weight, quantity, import_date, exp_date) values ($1, $2, $3, $4, $5, $6)",
                         batch_id, request.product_type_id, request.weight, request.quantity, request.import_datetime_utc_int, exp_date)
            return JSONResponse({"id": batch_id}, HTTPStatus.OK)
    except BaseException as e:
        print(e)
        return JSONResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR)

@rt.get("/list-batches")
async def list_batches(name_or_id_query: Optional[str] = "", harvest_timestamp_from: Optional[int] = 0, harvest_timestamp_to: int = 9223372036854775807 , status: Optional[str] = "", sortBy: Optional[str] = "", sortAscending: Optional[bool] = True, pg: asyncpg.pool.Pool = Depends(get_pgpool)) -> JSONResponse:
    """

    :param name_or_id_query: a string
    :param harvest_timestamp_from: UTC timestamp by milliseconds
    :param harvest_timestamp_to: UTC timestamp by milliseconds
    :param status: accepts: any, available, marked, exported, discarded
    :param sortBy: accepts: any, batch_id, produce_id, weight, quantity, harvest_date, remaining_shelf_life
    :return:
    """
    try:
        async with pg.acquire() as conn:
            # need to get produce-name, batch-id, batch-quantity, batch-weight, harvest-at, expiration-date, assigned_order_no, is-in-warehouse, discard-reason
            if status == "any" or not status:
                dbString = "select batch_id, produceinfo.harvest_type_name, quantity, weight, import_date, exp_date, export_date, assigned_order_no, is_in_warehouse, discard_reason from batchinfo inner join produceinfo on batchinfo.produce_type_id = produceinfo.id where (batch_id::varchar ilike $1 or produceinfo.harvest_type_name ilike $1) and (import_date >= $2 and import_date <= $3)"
            elif status == "discarded":
                dbString = "select batch_id, produceinfo.harvest_type_name, quantity, weight, import_date, exp_date, export_date, assigned_order_no, is_in_warehouse, discard_reason from batchinfo inner join produceinfo on batchinfo.produce_type_id = produceinfo.id where (batch_id::varchar ilike $1 or produceinfo.harvest_type_name ilike $1) and (import_date >= $2 and import_date <= $3) and discard_reason is not null and is_in_warehouse = false"
            elif status == "available":
                dbString = "select batch_id, produceinfo.harvest_type_name, quantity, weight, import_date, exp_date, export_date, assigned_order_no, is_in_warehouse, discard_reason from batchinfo inner join produceinfo on batchinfo.produce_type_id = produceinfo.id where (batch_id::varchar ilike $1 or produceinfo.harvest_type_name ilike $1) and (import_date >= $2 and import_date <= $3) and assigned_order_no is null and is_in_warehouse = true"
            elif status == "marked":
                dbString = "select batch_id, produceinfo.harvest_type_name, quantity, weight, import_date, exp_date, export_date, assigned_order_no, is_in_warehouse, discard_reason from batchinfo inner join produceinfo on batchinfo.produce_type_id = produceinfo.id where (batch_id::varchar ilike $1 or produceinfo.harvest_type_name ilike $1) and (import_date >= $2 and import_date <= $3) and assigned_order_no is not null and is_in_warehouse = true"
            elif status == "exported":
                dbString = "select batch_id, produceinfo.harvest_type_name, quantity, weight, import_date, exp_date, export_date, assigned_order_no, is_in_warehouse, discard_reason from batchinfo inner join produceinfo on batchinfo.produce_type_id = produceinfo.id where (batch_id::varchar ilike $1 or produceinfo.harvest_type_name ilike $1) and (import_date >= $2 and import_date <= $3) and assigned_order_no is not null and is_in_warehouse = false"
            else:
                return JSONResponse({}, HTTPStatus.UNPROCESSABLE_ENTITY)

            ret = await conn.fetch(dbString, f'%{name_or_id_query}%', harvest_timestamp_from, harvest_timestamp_to)
            retLst = [BatchInfo.from_list(row) for row in ret]
            return retLst


    except BaseException as e:
        print(e)
        return JSONResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR)