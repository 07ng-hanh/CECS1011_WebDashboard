from http import HTTPStatus

import asyncpg.pool
from fastapi import APIRouter
from fastapi.params import Depends
from starlette.responses import JSONResponse, PlainTextResponse
import math
from datamodels import ExportOrderMinimal, PortInfo
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