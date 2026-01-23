import asyncio
import datetime
import http
import json
from datetime import timezone
import os
from http import HTTPStatus

import aiofiles
import asyncpg.pool
from asyncpg import Pool
import fastapi
from fastapi import BackgroundTasks
from fastapi.params import Depends
from starlette.requests import ClientDisconnect
from starlette.responses import PlainTextResponse, StreamingResponse, JSONResponse, FileResponse

from dependency_injection import get_pgpool
import aiocsv
import os
import aioxlsxstream


rt = fastapi.APIRouter()
client_queues: set[asyncio.Queue] = set()

def remove_file(path: str):
    os.remove(path)

@rt.websocket("/write-sensor-data")
async def write_sensor_data(ws: fastapi.WebSocket):
    # TODO: Add mechanism for admin to rotate sensor API key. Propagate change to DB and valkey. If key changes, force disconnect sensor.
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
            t = int(datetime.datetime.now(timezone.utc).timestamp()) * 1000
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
        for c in client_queues:
            # notify clients that the sensor is disconnected
            try:
                c.put_nowait({"err": "client_disconnected"})
            except:
                pass
        print("CONN CLOSED!")
        await con.close()


async def sensor_yield(interval):
    last_push = 0
    Q = asyncio.Queue(maxsize=100)
    client_queues.add(Q)
    while True:
        try:
            e = await Q.get()

            if "err" in e:
                yield f"event: error_sent\ndata: {json.dumps(e)}\n\n"

            if e["timestamp"] - last_push >= interval:
                last_push = e["timestamp"]
                yield f"event: data_sent\ndata: {json.dumps(e)}\n\n"
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

@rt.get("/sensor-data-historic-v2")
async def sensor_historic_v2(current_time_ms: int, length_ms: int, interval_ms: int, pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):
    try:
        async with pgpool.acquire() as conn:
            start_time_ms = current_time_ms - length_ms
            rows = await conn.fetch("SELECT timestamp, temperature, co2, humidity FROM environmentreading WHERE timestamp >= $1 AND timestamp <= $2 ORDER BY timestamp DESC", start_time_ms, current_time_ms)
            # select elements spaced apart by the specified interval_ms
            prev = None
            row_json = [prev := {"timestamp": row[0],"temperature": row[1], "co2": row[2], "humidity": row[3]} for index, row in enumerate(rows)
                        if index == 0 or prev['timestamp'] - row['timestamp'] >= interval_ms]
            return JSONResponse(row_json)
    except:
        return JSONResponse({"msg": "cannot return historical data"}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)


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

# helper function for aioxlsxstream library
async def row_generator(rows):
    async def cells_generator(r):
        for cell in r:
            yield cell

    for row in rows:
        yield cells_generator(row)

@rt.get("/export-recordings")
async def export_recordings(from_timestamp_ms: int, to_timestamp_ms: int, file_format: str, background_tasks: BackgroundTasks, utc_offset_minutes: int = 0, pgpool : asyncpg.pool.Pool = Depends(get_pgpool)):
    # utc_offset_minutes: difference between the time represented in UTC timezone and local timezone
    if (from_timestamp_ms == None or to_timestamp_ms == None or file_format == None):
        return JSONResponse({}, status_code=HTTPStatus.UNPROCESSABLE_ENTITY)

    async with pgpool.acquire() as conn:
        data: list[list[any]] = await conn.fetch("select timestamp, temperature, humidity, co2 from environmentreading where timestamp >= $1 and timestamp <= $2 order by timestamp", from_timestamp_ms, to_timestamp_ms)
        data_2 = []
        for (timestamp, temperature, humidity, co2) in data:
            # change the UTC milliseconds timestamp to a human-readable form in local time
            data_2.append(
                [
                    (datetime.datetime.fromtimestamp(timestamp / 1000, tz=datetime.UTC) + datetime.timedelta(minutes=-utc_offset_minutes)).strftime("%Y-%m-%d %H:%M:%S"),
                    str(temperature),
                    str(humidity),
                    str(co2)
                ]
            )

        data_2.insert(0, ["Time", "Temperature (C)", "Humidity (%)", "CO2 (PPM)"])
        data.clear()
        if file_format == "csv":
            file_name = f"export_{datetime.datetime.now().timestamp()}.csv"
            async with aiofiles.open(file_name, mode="w") as file:
                csvwriter = aiocsv.AsyncWriter(file)
                await csvwriter.writerows(data_2)
            background_tasks.add_task(remove_file, file_name)
            return FileResponse(path=file_name, filename=file_name, media_type='application/octet-stream',)

        else:
            file_name = f"export_{datetime.datetime.now().timestamp()}.xlsx"
            async with aiofiles.open(file_name, mode="wb") as file:
                xlsx_file = aioxlsxstream.XlsxFile()
                xlsx_file.write_sheet(row_generator(data_2))
                async for chunk in xlsx_file:
                    await file.write(chunk)
            background_tasks.add_task(remove_file, file_name)
            return FileResponse(path=file_name, filename=file_name, media_type='application/octet-stream',)
