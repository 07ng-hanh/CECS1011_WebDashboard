import json
import os
import time
import secrets
from typing import List

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
async def retrieve_results(task_id: str, dry_run: bool, background_tasks: BackgroundTasks, pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):

    if not os.path.exists(f"{task_id}.json"):
        return JSONResponse({})
    j = None
    async with aiofiles.open(f"{task_id}.json", "r") as o:
        j = await o.read()
        if j == "ERROR":
            return JSONResponse({}, status_code=500)
        j = json.loads(j)

        # list all shipment and batch ids to fetch
        shipment_ids = set()
        batch_ids = set()

        # need to show: shipment id, route, estimated start & eta.
        # for the batch: batch ID + batch quantity + batch EXP
        for entry in j["results"]:
            shipment_ids.add(entry["shipment_id"])
            batch_ids.add(entry["batch_id"])

        async with pgpool.acquire() as conn:
            shipment_info = await conn.fetch("""select shipment_id, p0.port_name, p1.port_name, planned_departure_timestamp, eta_milliseconds 
                                    from shipments left join ports p0 on p0.id = source_port_id
                                    left join ports p1 on p1.id = dest_port_id
                                    where shipment_id = any($1)""", tuple(shipment_ids))
            produce_info = await conn.fetch("""
                select batch_id, quantity, exp_date, produceinfo.harvest_type_name from batchinfo 
                    inner join produceinfo on produceinfo.id = batchinfo.produce_type_id
                    where batch_id = any($1)
            """, tuple(batch_ids))
            j["shipments"] = {}
            for shipment in shipment_info:
                shipment_id, port_from, port_to, planned_departure_time, eta_milliseconds = shipment
                j["shipments"][int(shipment_id)] = {
                    "port_from": port_from,
                    "port_to": port_to,
                    "planned_departure_time": planned_departure_time,
                    "eta_milliseconds": eta_milliseconds
                }
            j["batches"] = {}
            for produce in produce_info:
                batch_id, quantity, exp_date, produce_name = produce
                j["batches"][int(batch_id)] = {
                    "batch_id": batch_id,
                    "quantity": quantity,
                    "exp_timestamp": exp_date,
                    "produce_name": produce_name

                }


    if not dry_run:
        background_tasks.add_task(os.remove, f"{task_id}.json")
    return JSONResponse(j)

@rt.get("/suggestion-full")
async def suggestion_full(background_tasks: BackgroundTasks, pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):
    # mapping: shipments: shipment_id, produce_id, remaining_quantity_needed, scheduled_departure, eta
    # available batches: batch_id, produce_id, quantity, exp_date

    async with pgpool.acquire() as conn:
        batch_lst = await conn.fetch("select batch_id, produce_type_id, quantity, exp_date from batchinfo where assigned_order_no is null and is_in_warehouse = true")
        # fetch all pending shipments
        shipment_lst = await conn.fetch(
            """
            select shipment_id, shipments.produce_type_id, produce_qty, 
                   planned_departure_timestamp, eta_milliseconds 
            from shipments where actual_departure_timestamp is null;
            """
        )

        # fetch all available batches
        assigned_quantity_by_shipment = await conn.fetch(
            """
            select SUM(quantity), assigned_order_no from batchinfo where assigned_order_no is not null group by assigned_order_no;
            """
        )

        assigned_quantity_by_shipment = {order_no: quantity for (quantity, order_no) in assigned_quantity_by_shipment}

        batch_lst = [MLHandler.Batch(batch_id=b[0], produce_id=b[1], quantity=b[2], exp_date_timestamp=b[3]) for b in batch_lst]
        shipment_lst: List[MLHandler.Shipment] = [MLHandler.Shipment(shipment_id=s[0], produce_id=s[1], remaining_quantity_needed=s[2] - assigned_quantity_by_shipment.get(s[0], 0), schedule_departure=s[3], eta=s[4], schedule_arrival=s[3]+s[4]) for s in shipment_lst]

        shipment_lst = list(filter(lambda x: x.remaining_quantity_needed > 0 , shipment_lst))

    task_id = f'{str(time.time()).replace('.', '')}_{secrets.randbits(32)}'
    background_tasks.add_task(background_runner, task_id, shipment_lst, batch_lst)

    return PlainTextResponse(task_id)