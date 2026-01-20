import datetime
import time
from http import HTTPStatus
from typing import Optional, Callable
import asyncpg.pool
import datetime

import glide
from fastapi import APIRouter, HTTPException, Depends
from starlette.responses import JSONResponse
from dependency_injection import get_pgpool, get_vk
from datamodels import NewBatchForm, BatchInfo, WarehouseConfig
import zlib
rt = APIRouter()

@rt.post("/new-batch")
async def new_batch(request: NewBatchForm, pg: asyncpg.pool.Pool = Depends(get_pgpool), vk1 = Depends(get_vk)) -> JSONResponse:
    try:
        async with pg.acquire() as conn:

            # check batch compatibility
            # return exception if batch does not fit
            this_batch_threshold = await conn.fetch("select thresh_temp_lo, thresh_temp_hi, thresh_humidity_lo, thresh_humidity_hi, thresh_co2_lo, thresh_co2_hi from produceinfo where id = $1", request.product_type_id)
            batch_temp_lo, batch_temp_hi, batch_humidity_lo, batch_humidity_hi, batch_co2_lo, batch_co2_hi = this_batch_threshold[0]
            print("BATCH", this_batch_threshold[0])
            cur_threshold = await conn.fetch("select max(produceinfo.thresh_temp_lo), min(produceinfo.thresh_temp_hi), max(produceinfo.thresh_co2_lo), min(produceinfo.thresh_co2_hi), max(produceinfo.thresh_humidity_lo), min(produceinfo.thresh_humidity_hi) from batchinfo join produceinfo on produceinfo.id = batchinfo.produce_type_id where batchinfo.is_in_warehouse = TRUE")

            c_temp_lo, c_temp_hi, c_co2_lo, c_co2_hi, c_humid_lo, c_humid_hi = cur_threshold[0]

            if (c_temp_lo != None and c_temp_hi != None and c_co2_hi != None and c_co2_lo!= None and c_humid_hi!= None and c_humid_lo!= None):
                # check by try updating min and max thresholds
                c_temp_lo = max(c_temp_lo, batch_temp_lo)
                c_humid_lo = max(c_humid_lo, batch_humidity_lo)
                c_co2_lo = max(c_co2_lo, batch_co2_lo)

                c_temp_hi = min(c_temp_hi, batch_temp_hi)
                c_humid_hi = min(c_humid_hi, batch_humidity_hi)
                c_co2_hi = min(c_co2_hi, batch_co2_hi)

                compatible = c_temp_lo < c_temp_hi and c_humid_lo < c_humid_hi and c_co2_lo < c_co2_hi
            else:
                compatible = True

            if not compatible:
                return JSONResponse({"msg": "batch_not_compatible"}, HTTPStatus.NOT_ACCEPTABLE)


            hash_target = str(request.product_type_id) + str(request.import_datetime_utc_int) + str(request.quantity) + str(time.time())
            batch_id = zlib.crc32(hash_target.encode())
            # both shelf life and harvest are represented in milliseconds.
            exp_date = (await conn.fetch("select shelf_life from produceinfo where id = $1", request.product_type_id))[0][0] + request.import_datetime_utc_int
            await conn.execute("insert into batchinfo (batch_id, produce_type_id, weight, quantity, import_date, exp_date) values ($1, $2, $3, $4, $5, $6)",
                         batch_id, request.product_type_id, request.weight, request.quantity, request.import_datetime_utc_int, exp_date)

            if await vk1.get("CONFIG_threshold_auto") == b"True":
                c = WarehouseConfig()

                # get new range and write to valkey
                config = WarehouseConfig(**{})
                r = await conn.fetch(
                    "select max(produceinfo.thresh_temp_lo), min(produceinfo.thresh_temp_hi), max(produceinfo.thresh_co2_lo), min(produceinfo.thresh_co2_hi), max(produceinfo.thresh_humidity_lo), min(produceinfo.thresh_humidity_hi) from batchinfo join produceinfo on produceinfo.id = batchinfo.produce_type_id")
                r = r[0]

                if (r[0] == None or r[1] == None or r[2] == None or r[3] == None or r[4] == None or r[5] == None):
                    return

                config.temperature_low = r[0]
                config.temperature_hi = r[1]
                config.co2_low = r[2]
                config.co2_hi = r[3]
                config.humidity_lo = r[4]
                config.humidity_hi = r[5]
                config_dict = config.model_dump()

                for k in ("temperature_low", "temperature_hi", "co2_low", "co2_hi", "humidity_lo", "humidity_hi"):
                    await vk1.set(f"CONFIG_{k}", str(config_dict[k]))
                    await conn.execute("update configuration set value = $1 where key = $2", str(config_dict[k]), k)

            return JSONResponse({"id": batch_id}, HTTPStatus.OK)
    except BaseException as e:
        print(e)
        return JSONResponse({"msg": "error"}, HTTPStatus.INTERNAL_SERVER_ERROR)

@rt.get("/list-batches")
async def list_batches(name_or_id_query: Optional[str] = "", harvest_timestamp_from: Optional[int] = 0, harvest_timestamp_to: int = 9223372036854775807 , status: Optional[str] = "", sortBy: Optional[str] = "", sortAscending: Optional[bool] = True, almostExpiredOnly: Optional[bool] = False, pg: asyncpg.pool.Pool = Depends(get_pgpool), page: int=1, limit: int=50) -> JSONResponse:
    """

    :param name_or_id_query: a string
    :param harvest_timestamp_from: UTC timestamp by milliseconds
    :param harvest_timestamp_to: UTC timestamp by milliseconds
    :param status: accepts: any, available, marked, exported, discarded, instore
    :param sortBy: accepts: any, batch_id, harvest_type_name, weight, quantity, harvest_date, remaining_shelf_life
    :return:
    """
    try:

        async with pg.acquire() as conn:
            # need to get produce-name, batch-id, batch-quantity, batch-weight, harvest-at, expiration-date, assigned_order_no, is-in-warehouse, discard-reason
            if status == "any" or not status:
                dbString = "select batch_id, produceinfo.harvest_type_name, produce_type_id, quantity, weight, import_date, exp_date, export_date, assigned_order_no, is_in_warehouse, discard_reason from batchinfo inner join produceinfo on batchinfo.produce_type_id = produceinfo.id where (batch_id::varchar ilike $1 or produceinfo.harvest_type_name ilike $1) and (import_date >= $2 and import_date <= $3)"
            elif status == "discarded":
                dbString = "select batch_id, produceinfo.harvest_type_name, produce_type_id, quantity, weight, import_date, exp_date, export_date, assigned_order_no, is_in_warehouse, discard_reason from batchinfo inner join produceinfo on batchinfo.produce_type_id = produceinfo.id where (batch_id::varchar ilike $1 or produceinfo.harvest_type_name ilike $1) and (import_date >= $2 and import_date <= $3) and discard_reason is not null and is_in_warehouse = false"
            elif status == "available":
                dbString = "select batch_id, produceinfo.harvest_type_name, produce_type_id, quantity, weight, import_date, exp_date, export_date, assigned_order_no, is_in_warehouse, discard_reason from batchinfo inner join produceinfo on batchinfo.produce_type_id = produceinfo.id where (batch_id::varchar ilike $1 or produceinfo.harvest_type_name ilike $1) and (import_date >= $2 and import_date <= $3) and assigned_order_no is null and is_in_warehouse = true"
            elif status == "marked":
                dbString = "select batch_id, produceinfo.harvest_type_name, produce_type_id, quantity, weight, import_date, exp_date, export_date, assigned_order_no, is_in_warehouse, discard_reason from batchinfo inner join produceinfo on batchinfo.produce_type_id = produceinfo.id where (batch_id::varchar ilike $1 or produceinfo.harvest_type_name ilike $1) and (import_date >= $2 and import_date <= $3) and assigned_order_no is not null and is_in_warehouse = true"
            elif status == "exported":
                dbString = "select batch_id, produceinfo.harvest_type_name, produce_type_id, quantity, weight, import_date, exp_date, export_date, assigned_order_no, is_in_warehouse, discard_reason from batchinfo inner join produceinfo on batchinfo.produce_type_id = produceinfo.id where (batch_id::varchar ilike $1 or produceinfo.harvest_type_name ilike $1) and (import_date >= $2 and import_date <= $3) and assigned_order_no is not null and is_in_warehouse = false"
            elif status == "instore":
                dbString = "select batch_id, produceinfo.harvest_type_name, produce_type_id, quantity, weight, import_date, exp_date, export_date, assigned_order_no, is_in_warehouse, discard_reason from batchinfo inner join produceinfo on batchinfo.produce_type_id = produceinfo.id where (batch_id::varchar ilike $1 or produceinfo.harvest_type_name ilike $1) and (import_date >= $2 and import_date <= $3) and is_in_warehouse = true"
            else:
                return JSONResponse({}, HTTPStatus.UNPROCESSABLE_ENTITY)

            match sortBy:
                case "batch_id":
                    # retLst.sort(key=lambda x: x.batch_id, reverse=not sortAscending)
                    dbString += " order by batch_id"
                case "harvest_type_name":
                    # retLst.sort(key=lambda x: x.harvest_type_name, reverse=not sortAscending)
                    dbString += " order by produceinfo.harvest_type_name"
                case "weight":
                    # retLst.sort(key=lambda x: x.weight, reverse=not sortAscending)
                    dbString += " order by weight"
                case "quantity":
                    # retLst.sort(key=lambda x: x.quantity, reverse=not sortAscending)
                    dbString += " order by quantity"
                case "harvest_date":
                    # retLst.sort(key=lambda x: x.import_date, reverse=not sortAscending)
                    dbString += " order by import_date"
                case "remaining_shelf_life":
                    # retLst.sort(key=lambda x: x.exp_date - x.import_date, reverse=not sortAscending)
                    dbString += " order by remaining_shelf_life"
                case _:
                    dbString += " order by batch_id"

            if sortAscending:
                dbString += " asc"
            else:
                dbString += " desc"

            dbString += f' limit $4 offset $5'
            ret = await conn.fetch(dbString, f'%{name_or_id_query}%', harvest_timestamp_from, harvest_timestamp_to, limit, limit * (page - 1))

            if almostExpiredOnly:
                # List items that expire in 30 days or less.
                timestamp_now_utc = datetime.datetime.now(datetime.UTC).timestamp() * 1000
                # show batches with less than 20% of lifespan left.
                retLst: list[BatchInfo] = [BatchInfo.from_list(row) for row in ret if (row[6] - timestamp_now_utc) / (row[6] - row[5]) <= 0.2]
            else:
                retLst: list[BatchInfo] = [BatchInfo.from_list(row) for row in ret]

            return retLst

    except BaseException as e:
        print(e)
        return JSONResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR)


@rt.get("/list-batches-for-order")
async def list_batches_for_order(assigned_order_no: int, produce_type_id: int, pg: asyncpg.pool.Pool = Depends(get_pgpool), page: int=1, limit: int=50) -> JSONResponse:
    """

    :param name_or_id_query: a string
    :param harvest_timestamp_from: UTC timestamp by milliseconds
    :param harvest_timestamp_to: UTC timestamp by milliseconds
    :param status: accepts: any, available, marked, exported, discarded, instore
    :param sortBy: accepts: any, batch_id, harvest_type_name, weight, quantity, harvest_date, remaining_shelf_life
    :return:
    """
    try:

        async with pg.acquire() as conn:


            dbString = """select batch_id, produceinfo.harvest_type_name, produce_type_id, quantity, weight, import_date, 
                                 exp_date, export_date, assigned_order_no, is_in_warehouse, discard_reason 
                          from batchinfo inner join produceinfo on batchinfo.produce_type_id = produceinfo.id
                        where (assigned_order_no = $1 and is_in_warehouse = TRUE and produce_type_id = $2)
                        or (produce_type_id = $2 and is_in_warehouse = TRUE and assigned_order_no is null)
                        order by batch_id limit $3 offset $4
                       """
            ret = await conn.fetch(dbString, assigned_order_no, produce_type_id, limit, (page - 1) * limit)

            retLst: list[BatchInfo] = [BatchInfo.from_list(row) for row in ret]

            return retLst

    except BaseException as e:
        print(e)
        return JSONResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR)


@rt.delete("/discard-batch")
async def discard_batch(batch_id: int, reason: str, pg = Depends(get_pgpool), vk1: glide.GlideClient = Depends(get_vk)):
    dbstring = "update batchinfo set is_in_warehouse = false, discard_reason = $1, assigned_order_no = null where batch_id = $2"
    async with pg.acquire() as conn:
        await conn.execute(dbstring, reason, batch_id)

    async with pg.acquire() as conn:

        # check auto-threshold and update accordingly

        if await vk1.get("CONFIG_threshold_auto") == b"True":
            print("AUTO_THRESH")
            # get new range and write to valkey
            config = WarehouseConfig(**{})
            r = await conn.fetch(
                "select max(produceinfo.thresh_temp_lo), min(produceinfo.thresh_temp_hi), max(produceinfo.thresh_co2_lo), min(produceinfo.thresh_co2_hi), max(produceinfo.thresh_humidity_lo), min(produceinfo.thresh_humidity_hi) from batchinfo join produceinfo on produceinfo.id = batchinfo.produce_type_id where batchinfo.is_in_warehouse = true")
            r = r[0]

            print(r)

            if not (r[0] != None and r[1] != None and r[2]!= None and r[3]!= None and r[4]!= None and r[5]!= None):
                return

            config.temperature_low = r[0]
            config.temperature_hi = r[1]
            config.co2_low = r[2]
            config.co2_hi = r[3]
            config.humidity_lo = r[4]
            config.humidity_hi = r[5]
            config_dict = config.model_dump()

            for k in ("temperature_low", "temperature_hi", "co2_low", "co2_hi", "humidity_lo", "humidity_hi"):
                await vk1.set(f"CONFIG_{k}", str(config_dict[k]))
                await conn.execute("update configuration set value = $1 where key = $2", str(config_dict[k]), k)


@rt.post("/assign-order-to-batch")
async def assign_order_to_batch(batch_id: int, order_id: int, pg = Depends(get_pgpool)):
    dbstring = "update batchinfo set assigned_order_no = $1 where batch_id = $2"
    async with pg.acquire() as conn:
        await conn.execute(dbstring, order_id, batch_id)

@rt.post("/assign-order-to-batch-multi")
async def assign_order_to_batch_multi(batch_ids: str, order_ids: str, pg = Depends(get_pgpool)):

    batch_ids_lst = batch_ids.split(",")
    order_ids_lst= order_ids.split(",")

    async with pg.acquire() as conn:
        async with conn.transaction():
            for batch_id, order_id in zip(batch_ids_lst, order_ids_lst):
                dbstring = "update batchinfo set assigned_order_no = $1 where batch_id = $2"
                await conn.execute(dbstring, int(order_id), int(batch_id))



@rt.delete("/remove-order-from-batch")
async def remove_order_from_batch(batch_id: int, pg = Depends(get_pgpool)):
    dbstring = "update batchinfo set assigned_order_no = null where batch_id = $1"
    async with pg.acquire() as conn:
        await conn.execute(dbstring, batch_id)

@rt.get("/simple-stats")
async def get_simple_stats(current_time_ms: int, pg = Depends(get_pgpool)):
    async with pg.acquire() as conn:
        a_month_in_ms = 30 * 86400 * 1000
        db_row = await conn.fetch("select sum(quantity), sum(( (exp_date - $1) / (exp_date - import_date)::float <= 0.20)::int) from batchinfo where is_in_warehouse = true;", current_time_ms)
        return JSONResponse({"total_quantity": db_row[0][0], "has_expired": db_row[0][1]})