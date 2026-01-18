import datetime
from http import HTTPStatus
from typing import Optional, List

import asyncpg.pool
from fastapi import APIRouter
from fastapi.params import Depends
from starlette.responses import JSONResponse, PlainTextResponse
import math
from datamodels import ExportOrderMinimal, PortInfo, ExportOrderDetails, BatchMinimal
from dependency_injection import get_pgpool
rt = APIRouter()

def estimate_length(lat_a, lon_a, lat_b, lon_b):
    """
    Calculate the Haversine distance (the "great circle") distance between two points.
    Suitable for estimating port-to-port navigation.

    Ref: https://en.wikipedia.org/wiki/Haversine_formula, https://www.geeksforgeeks.org/dsa/haversine-formula-to-find-distance-between-two-points-on-a-sphere/

    :param lat_a: latitude of point A in degrees
    :param lon_a: longitude of point A in degrees
    :param lat_b: latitude of point B in degrees
    :param lon_b: longitude of point B in degrees
    :return: Nautical miles distance between A and B.
    """

    _lat_a = math.radians(lat_a)
    _lat_b = math.radians(lat_b)

    _lon_a = math.radians(lon_a)
    _lon_b = math.radians(lon_b)

#     Calculating the square of half-chord length
    diff_lat = _lat_b - _lat_a
    diff_lon = _lon_b - _lon_a
    a = (math.sin(diff_lat / 2) ** 2) + math.cos(_lat_a) * math.cos(_lat_b) * (math.sin(diff_lon / 2) ** 2)
    # Calculating the distance d
    EARTH_RADIUS_NAUTICAL_MILES = 3443.92 # or 6371 km
    d = 2 * math.asin(math.sqrt(a)) * EARTH_RADIUS_NAUTICAL_MILES
    return d

def estimate_transport_time(dist, speed = 9.25):
    """
    Estimate transport time given distance and speed
    :param dist: distance in nautical miles
    :param speed: speed in nautical miles. an average cargo ship travels at 9.25 nautical miles/hour.
    Ref: https://desteia.com/blog/container-ship#:~:text=To%20put%20this%20into%20perspective%2C%20while%20a%20container%20ship%20travels%20at%20an%20average%20speed%20of%2014.2%20nautical%20miles%20per%20hour%2C%20a%20general%20cargo%20ship%20travels%20at%209.25%20nautical%20miles%20per%20hour.
    :return: estimated transport time in hours.
    """
    return dist / speed

@rt.post("/add-shipment")
async def add_shipment(s: ExportOrderMinimal, pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):
    try:
        # get port lat/lon from port list
        lat_a, lon_a, lat_b, lon_b = 0, 0, 0, 0
        async with pgpool.acquire() as conn:
            departure_port = await conn.fetch("select (port_lat, port_lon) from ports where id = $1", s.departure_port_id)
            lat_a, lon_a = departure_port[0][0]
            destination_port = await conn.fetch("select (port_lat, port_lon) from ports where id = $1", s.destination_port_id)
            lat_b, lon_b = destination_port[0][0]

        # push order to DB
        estimate_transport_time_ms = estimate_transport_time(estimate_length(lat_a, lon_a, lat_b, lon_b)) * 3600000

        async with pgpool.acquire() as conn:
            await conn.execute("insert into shipments (source_port_id, dest_port_id, planned_departure_timestamp, produce_type_id, produce_qty, eta_milliseconds) values ($1, $2, $3, $4, $5, $6)",
                         s.departure_port_id, s.destination_port_id, s.planned_departure_day_utc_int, s.produce_id, s.produce_qty, estimate_transport_time_ms )

    except Exception as e:
        print(e)
        return JSONResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR)

@rt.get("/search-port")
async def search_port(q: str, pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):
    if len(q) < 3:
        return JSONResponse({"msg": "query needs to have at least 3 characters."})
    try:
        async with pgpool.acquire() as conn:
            d = await conn.fetch("select id, port_name, port_lat, port_lon from ports where port_name ilike $1 or id ilike $1", f"%{q}%")
            print(d)
            port_list = [PortInfo(id=row[0], port_name=row[1], port_lat=row[2], port_lon=row[3]) for row in d]
            return port_list
    except:
        return JSONResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR)

@rt.get("/estimate-eta")
async def estimate_eta(port_id_from: str, port_id_to: str, pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):
    try:
        async with pgpool.acquire() as conn:
            d = await conn.fetch("select id, port_lat, port_lon from ports where id = $1 or id = $2", port_id_from, port_id_to)
            _, lat_a, lon_a = d[0]
            _, lat_b, lon_b = d[1]
            return PlainTextResponse(str( 3600000 * estimate_transport_time(estimate_length(lat_a, lon_a, lat_b, lon_b))))
    except Exception as e:
        return PlainTextResponse(e, HTTPStatus.INTERNAL_SERVER_ERROR)

@rt.get("/list-shipments")
async def list_shipments(shipment_id: Optional[str] = "", port_name_from: Optional[str] = "", port_name_to: Optional[str] = "", departure_start: Optional[int] = 0, departure_end: Optional[int] = 9223372036854775807, produce_type: Optional[str] = "", status: Optional[str] = "status-any", sort_by: Optional[str] = "", sort_ascending: Optional[bool] = True, page: Optional[int] = 1, limit: Optional[int] = 50, pgpool: asyncpg.pool.Pool = Depends(get_pgpool), restrict_product_id: Optional[int | None] = None):
    WCARD = "%{}%"
    order_clause = {
        "": "",
        "sort-default": "",
        "sort-order-id": "order by shipment_id",
        "sort-departure-port": "order by source_port_name",
        "sort-destination-port": "order by dest_port_name",
        "sort-produce-name": "order by p_harvest_type",
        "sort-quantity": "order by produce_qty",
        "sort-scheduled-departure": "order by planned_departure_timestamp",
        "sort-actual-departure": "order by actual_departure_timestamp"
    }


    dbString = """
        select * from (select shipment_id, source_port_id, po1.port_name as source_port_name, 
        dest_port_id, po2.port_name as dest_port_name, shipments.produce_type_id, p1.harvest_type_name as p_harvest_type, 
        produce_qty, planned_departure_timestamp,
        actual_departure_timestamp, eta_milliseconds, COALESCE(ARRAY_AGG(b.batch_id), null) as batches, SUM(COALESCE(b.quantity, 0)) as cur_quantity
        from shipments
        join produceinfo p1 on p1.id = shipments.produce_type_id
        join ports po1 on po1.id = source_port_id
        join ports po2 on po2.id = dest_port_id
        left join batchinfo b on b.assigned_order_no = shipment_id
        
        where shipment_id::varchar like $1 and (po1.port_name ilike $2 or source_port_id ilike $2) and (po2.port_name ilike $3 or dest_port_id ilike $3)
        and p1.harvest_type_name ilike $4 and planned_departure_timestamp >= $5 and planned_departure_timestamp <= $6
        
        group by shipment_id, po1.id, po2.id, p1.id) {}

        """

    # check status
    match status:
        case "status-any":
            dbString = dbString.format("")
        case "status-waiting":
            _q = "where actual_departure_timestamp is null and cur_quantity < produce_qty"
            if restrict_product_id:
                _q += f" and produce_type_id = {restrict_product_id}"
            dbString = dbString.format(_q)



        case "status-waiting-late":
            dbString = dbString.format(f"where actual_departure_timestamp is null and cur_quantity < produce_qty and planned_departure_timestamp < {int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)}")
        case "status-ready":
            dbString = dbString.format(f"where cur_quantity >= produce_qty and actual_departure_timestamp is null")
        case "status-departed":
            dbString = dbString.format("where actual_departure_timestamp is not null")
        case "status-ready-late":
            dbString = dbString.format(f"where cur_quantity >= produce_qty and actual_departure_timestamp is null and planned_departure_timestamp < {int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)} ")



    # add order clause
    dbString += order_clause[sort_by] + " "
    if not sort_ascending and order_clause[sort_by]:
        dbString += "DESC "
    dbString += "limit $7 offset $8"

    try:
        async with pgpool.acquire() as conn:
            r = await conn.fetch(dbString, WCARD.format(shipment_id), WCARD.format(port_name_from), WCARD.format(port_name_to), WCARD.format(produce_type),
                                 departure_start, departure_end, limit, (page - 1) * limit)
            # mapper maps order_id to the detailed list
            retArray: List[ExportOrderDetails] = []
            for shipment in r:
                e = ExportOrderDetails.from_list(shipment)
                if len(e.batches) == 1 and e.batches[0] == None:
                    e.batches.clear()
                retArray.append(e)

        return JSONResponse([v.model_dump() for v in retArray])
    except Exception as e:
        raise e

@rt.post("/initiate-export")
async def initiate_export(shipment_id: Optional[int], dry_run: bool = True, pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):
    # 1st step: check if anything cannot survive the trip and is exactly what's ordered
    # 2nd step: if all clear: return 200. if not: return a list of batches that won't survive the trip or misplaced.
    async with pgpool.acquire() as conn:
        shipment_record = await conn.fetch("select eta_milliseconds, produce_type_id from shipments where shipment_id = $1", shipment_id)
        print(shipment_record)
        eta = int(shipment_record[0][0])
        produce_type_id = shipment_record[0][1]
        # eta + time.now <= exp_date
        time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
        r = await conn.fetch("select batch_id, ($2 >= exp_date), (produce_type_id != $3) from batchinfo where assigned_order_no = $1 and ($2 >= exp_date or produce_type_id != $3)"
                               ,shipment_id, eta + time_now, produce_type_id)
        problematicBatches = []
        for record in r:
            batch_id, past_exp_date, wrong_prod_type = record
            problematicBatches.append({"id": batch_id, "past_exp_date": past_exp_date, "wrong_prod_type": wrong_prod_type})

        if problematicBatches:
            return JSONResponse(problematicBatches)
        else:
            if not dry_run:
                await conn.execute("update shipments set actual_departure_timestamp = $1 where shipment_id = $2", time_now, shipment_id)
                await conn.execute("update batchinfo set export_date = $1, is_in_warehouse = FALSE where assigned_order_no = $2", time_now, shipment_id)

            return JSONResponse([])

@rt.delete("/cancel-shipment")
async def cancel_shipment(shipment_id: int, pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):
    async with pgpool.acquire() as conn:
        await conn.execute("update batchinfo set assigned_order_no = NULL where assigned_order_no = $1", shipment_id)
        await conn.execute("delete from shipments where shipment_id = $1", shipment_id)