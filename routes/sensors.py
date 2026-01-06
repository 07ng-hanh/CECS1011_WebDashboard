import asyncio
import datetime
import http
import json
from datetime import timezone
import os
import time

import asyncpg.pool
from asyncpg import Pool
import fastapi
from fastapi.params import Depends
from glide_shared import GlideClientConfiguration
from starlette.requests import ClientDisconnect
from starlette.responses import PlainTextResponse, StreamingResponse, JSONResponse

from dependency_injection import get_vk, get_pgpool

rt = fastapi.APIRouter()
client_queues: set[asyncio.Queue] = set()

@rt.websocket("/write-sensor-data")
async def write_sensor_data(ws: fastapi.WebSocket):
    # TODO: Add mechanism for admin to rotate sensor API key. Propagate change to DB and valkey. If key changes, force disconnect sensor.
    # TODO: Instead of fanning out responses to the client, send to a Redis Pub/Sub channel to prevent clogging the event loop. The propagation server will pick up on the Pub/Sub messages and distribute them.
    authkey = ws.headers.get("Authorization")
    pgpool: asyncpg.pool.Pool = await get_pgpool()

    if not authkey:
        await ws.send_denial_response(PlainTextResponse("missing api key"))
        return PlainTextResponse("", 404)

    if authkey != os.getenv("SENSOR_API_KEY"):
        await ws.send_denial_response(PlainTextResponse("api key mismatch"))
        return PlainTextResponse("", 404)
    await ws.accept()

    last_t = 0
    con = await pgpool.acquire()
    try:
        while True:
            e = await ws.receive_json()
            t = int(datetime.datetime.now(timezone.utc).timestamp() * 1000)
            if t > last_t:
                # ensure the sensor data is only written once per sec
                last_t = t
                e["timestamp"] = t

                for c in client_queues:
                    try:
                        c.put_nowait(e)
                    except:
                        pass


                await con.execute("insert into environmentreading (timestamp, temperature, co2, humidity) values ($1, $2, $3, $4)", e["timestamp"], e["temperature"], e["co2"], e["humidity"])
    finally:
        # On exit, clean up
        # pass
        print("CONN CLOSED!")
        await con.close()


async def sensor_yield(interval):
    last_push = 0
    Q = asyncio.Queue(maxsize=100)
    client_queues.add(Q)
    while True:
        try:
            # TODO: In a "separate yielding loop" scenario, await for new chunks from the fan-out server and simply yield that chunk
            e = await Q.get()
            if e["timestamp"] - last_push >= interval:
                last_push = e["timestamp"]
                yield f"data: {json.dumps(e)}\n\n"
            Q.task_done()
            # end of replacement
        except (asyncio.QueueFull, BrokenPipeError, ConnectionResetError, ClientDisconnect):
            # Disconnect stale clients
            client_queues.remove(Q)
            Q.empty()
            raise ClientDisconnect


@rt.get("/sensor-data-stream")
async def sensor_push(interval: float):
    return StreamingResponse(sensor_yield(interval), media_type="text/event-stream")


@rt.get("/sensor-data-historic")
async def sensor_historic(period: int, aggregation_range: int = 1, pgpool: Pool = Depends(get_pgpool)):
    # obtain timestamp cutoff
    t = datetime.datetime.now(timezone.utc).timestamp() * 1000 - period


    async with pgpool.acquire() as con:
        try:
            d = await con.fetch("SELECT timestamp, temperature, co2, humidity FROM environmentreading WHERE timestamp >= $1", t)

            if aggregation_range == 1:
                return JSONResponse(
                    [[row[0], {"temperature": row[1], "co2": row[2], "humidity": row[3]}] for row in d]
                )
            elif aggregation_range > 1:
                cur_interval_start = d[0][0]
                cur_interval_temp = []
                cur_interval_co2 = []
                cur_interval_humidity = []
                agg = []
                for (timestamp, temperature, co2, humidity) in d:
                    if timestamp - cur_interval_start >= period:

                        if not cur_interval_temp or not cur_interval_humidity or not cur_interval_co2:
                            agg.append([cur_interval_start, {"temperature": None, "co2": None, "humidity": None}])
                            cur_interval_start = timestamp
                        else:

                            agg.append([cur_interval_start,
                                        {"temperature": round(sum(cur_interval_temp) / len(cur_interval_temp), 1),
                                        "co2": round(sum(cur_interval_co2) / len(cur_interval_co2), 1),
                                         "humidity": round(sum(cur_interval_humidity) / len(cur_interval_humidity), 1)}])
                            cur_interval_humidity.clear()
                            cur_interval_co2.clear()
                            cur_interval_temp.clear()
                            cur_interval_start = timestamp

                    cur_interval_humidity.append(humidity)
                    cur_interval_temp.append(temperature)
                    cur_interval_co2.append(co2)

                agg.append([cur_interval_start,
                            {"temperature": round(sum(cur_interval_temp) / len(cur_interval_temp), 1),
                             "co2": round(sum(cur_interval_co2) / len(cur_interval_co2), 1),
                             "humidity": round(sum(cur_interval_humidity) / len(cur_interval_humidity), 1)}])

                return JSONResponse(agg)


        except:
            return PlainTextResponse("", http.HTTPStatus.INTERNAL_SERVER_ERROR)
