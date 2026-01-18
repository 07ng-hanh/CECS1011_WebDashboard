import json
import os
import time
import secrets

import aiofiles
from fastapi import APIRouter, Depends, BackgroundTasks
from starlette.responses import PlainTextResponse, JSONResponse

from dependency_injection import get_pgpool
import asyncpg
from MLHandler import MLHandler

rt = APIRouter()

def background_runner(id, shipment_lst, batch_lst):
    MLHandler.caller(id, shipment_lst, batch_lst)

@rt.get("/retrieve-results")
async def retrieve_results(task_id: str, background_tasks: BackgroundTasks):

    if not os.path.exists(f"{task_id}.json"):
        return JSONResponse({})
    j = None
    async with aiofiles.open(f"{task_id}.json", "r") as o:
        j = await o.read()
        if j == "ERROR":
            return JSONResponse({}, status_code=500)
        j = json.loads(j)

    background_tasks.add_task(os.remove, f"{task_id}.json")
    return JSONResponse(j)

@rt.get("/suggestion-full")
async def suggestion_full(background_tasks: BackgroundTasks, pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):
    # mapping: shipments: shipment_id, produce_id, remaining_quantity_needed, scheduled_departure, eta
    # available batches: batch_id, produce_id, quantity, exp_date

    async with pgpool.acquire() as conn:
        batch_lst = await conn.fetch("select batch_id, produce_type_id, quantity, exp_date from batchinfo where assigned_order_no is null and is_in_warehouse = true")
        shipment_lst = await conn.fetch(
            """
            select shipment_id, shipments.produce_type_id, produce_qty, 
                   planned_departure_timestamp, eta_milliseconds 
            from shipments;
            """
        )

        assigned_quantity_by_shipment = await conn.fetch(
            """
            select SUM(quantity), assigned_order_no from batchinfo where assigned_order_no is not null group by assigned_order_no;
            """
        )

        assigned_quantity_by_shipment = {order_no: quantity for (quantity, order_no) in assigned_quantity_by_shipment}

        batch_lst = [MLHandler.Batch(batch_id=b[0], produce_id=b[1], quantity=b[2], exp_date_timestamp=b[3]) for b in batch_lst]
        shipment_lst = [MLHandler.Shipment(shipment_id=s[0], produce_id=s[1], remaining_quantity_needed=s[2] - assigned_quantity_by_shipment.get(s[0], 0), schedule_departure=s[3], eta=s[4], schedule_arrival=s[3]+s[4]) for s in shipment_lst]

    task_id = f'{str(time.time()).replace('.', '')}_{secrets.randbits(32)}'
    background_tasks.add_task(background_runner, task_id, shipment_lst, batch_lst)

    return PlainTextResponse(task_id)