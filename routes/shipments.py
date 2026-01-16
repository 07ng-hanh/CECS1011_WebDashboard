import datetime
from http import HTTPStatus
from typing import Optional

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
async def list_shipments(shipment_id: Optional[str] = "", port_name_from: Optional[str] = "", port_name_to: Optional[str] = "", departure_start: Optional[int] = 0, departure_end: Optional[int] = 9223372036854775807, produce_type: Optional[str] = "", status: Optional[str] = "status-any", sort_by: Optional[str] = "", sort_ascending: Optional[bool] = True, page: Optional[int] = 1, limit: Optional[int] = 50, pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):
    WCARD = "%{}%"
    order_clause = {
        "": "",
        "sort-default": "",
        "sort-order-id": "order by shipment_id",
        "sort-departure-port": "order by po1.port_name",
        "sort-destination-port": "order by po2.port_name",
        "sort-produce-name": "order by p1.harvest_type_name",
        "sort-quantity": "order by produce_qty",
        "sort-scheduled-departure": "order by planned_departure_timestamp",
        "sort-actual-departure": "order by actual_departure_timestamp"
    }

    dbString = """
        select * from (select shipment_id, source_port_id, po1.port_name, 
        dest_port_id, po2.port_name, shipments.produce_type_id, p1.harvest_type_name, 
        produce_qty, planned_departure_timestamp,
        actual_departure_timestamp, eta_milliseconds, ARRAY_AGG(b.batch_id) as batches, SUM(b.quantity) as cur_quantity
        from shipments
        join produceinfo p1 on p1.id = shipments.produce_type_id
        join ports po1 on po1.id = source_port_id
        join ports po2 on po2.id = dest_port_id
        left join batchinfo b on b.assigned_order_no = shipment_id
        
        where shipment_id::varchar like $1 and po1.port_name ilike $2 and po2.port_name ilike $3
        and p1.harvest_type_name ilike $4 and planned_departure_timestamp >= $5 and planned_departure_timestamp <= $6
        
        group by shipment_id, po1.id, po2.id, p1.id) {}

        """

    # check status
    match status:
        case "status-any":
            dbString = dbString.format("")
        case "status-waiting":
            dbString = dbString.format("where actual_departure_timestamp is null and cur_quantity < produce_qty")
        case "status-waiting-late":
            dbString = dbString.format(f"where actual_departure_timestamp is null and cur_quantity < produce_qty and planned_departure_timestamp < {int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)}")
        case "status-ready":
            dbString = dbString.format(f"where cur_quantity >= produce_qty and actual_departure_timestamp is null")
        case "status-departed":
            dbString += "where actual_departure_timestamp is not null"

    # add order clause
    dbString += order_clause[sort_by] + " "
    if not sort_ascending:
        dbString += "DESC"
    dbString += "limit $7 offset $8"

    try:
        async with pgpool.acquire() as conn:
            r = await conn.fetch(dbString, WCARD.format(shipment_id), WCARD.format(port_name_from), WCARD.format(port_name_to), WCARD.format(produce_type),
                                 departure_start, departure_end, limit, (page - 1) * limit)
            # mapper maps order_id to the detailed list
            retArray: ExportOrderDetails = []
            for shipment in r:
                retArray.append(ExportOrderDetails.from_list(shipment))

        return JSONResponse([v.model_dump() for v in retArray])
    except Exception as e:
        raise e
        return JSONResponse({}, status_code=500)