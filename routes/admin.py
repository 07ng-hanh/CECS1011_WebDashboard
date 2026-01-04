from http import HTTPStatus

import asyncpg.pool
import glide
from fastapi import Depends, APIRouter
from starlette.responses import PlainTextResponse

from dependency_injection import get_vk, get_pgpool
from datamodels import NewUserForm, Credentials, ProduceInfoForm, WarehouseConfig
from fastapi.responses import JSONResponse
from argon2 import PasswordHasher
from fastapi import Request
from fastapi.responses import RedirectResponse
import http.client

rt = APIRouter()
passwordHasher = PasswordHasher(memory_cost=64, time_cost=3, parallelism=1 )

@rt.post("/new-user")
async def add_user(newUser: NewUserForm, pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):
    async with pgpool.acquire() as con:
        try:
            await con.execute("insert into users (username, password_hash, is_admin) values ($1, $2, $3)", newUser.username, passwordHasher.hash(f"{newUser.username}::{newUser.password}"), newUser.isadmin)
            return JSONResponse({"status": "user added"}, 200)
        except:
            return JSONResponse({"status": "adding new user failed. might be duplicating username?"}, HTTPStatus.UNPROCESSABLE_ENTITY)

@rt.get("/list-users")
async def list_users(page: int = 1, limit: int = 20, query: str = "", pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):
    async with pgpool.acquire() as con:
        try:
            users = await con.fetch("select username, is_admin from users where username ilike $1 limit $2 offset $3", f'%{query}%', limit, (page - 1) * limit)
            return JSONResponse([{"username": user["username"], "isadmin": user["is_admin"]} for user in users])
        except BaseException as e:
            print(e)
            return JSONResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR)

@rt.delete("/delete-user")
async def delete_user(username: str, pgpool: asyncpg.pool.Pool = Depends(get_pgpool), vk1 = Depends(get_vk)):
    async with pgpool.acquire() as con:
        try:
            await con.execute("delete from users where username = $1", username)
        except BaseException as e:
            print(e)
            return JSONResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR)

    # Step 2: Invalidate all sessions. At the moment, this does not log out the user yet, but prevents their session from querying APIs further.
    try:
        sessions_toks = await vk1.smembers(username)
        await vk1.delete(list(sessions_toks))
        await vk1.delete([username, ])
    except:
        pass

@rt.post("/change-user-password")
async def change_user_password(u: Credentials, pgpool: asyncpg.pool.Pool = Depends(get_pgpool), vk1: glide.GlideClient = Depends(get_vk)):
    # Step 1: update password on database.
    async with pgpool.acquire() as con:
        try:

            await con.execute("update users set password_hash = $1 where username = $2", passwordHasher.hash(f"{u.username}::{u.password}"), u.username)
        except:
            return JSONResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR)

    # Step 2: Invalidate all sessions. At the moment, this does not log out the user yet, but prevents their session from querying APIs further.
    sessions_toks = await vk1.smembers(u.username)
    await vk1.delete(list(sessions_toks))
    await vk1.delete([u.username, ])


@rt.get("/request-settings-page")
async def request_settings_page(request: Request):
    # This endpoint can only be reached when the user is authenticated via the middleware
    # This endpoint is for redirecting users to their corresponding settings page (admin, non-admin),
    # and does not do strict restriction enforcement.

    # Enforcement is actually done by the middleware when requesting /users or /admin endpoints.
    # Hence, a non-admin user navigating to the admin's settings page would not automatically bypass the restrictions.

    adminID = request.cookies.get("adminID")


    if adminID:
        return RedirectResponse("/static/settings-admin.html", http.client.SEE_OTHER)
    else:
        return RedirectResponse("/static/settings-nonprivileged.html", http.client.SEE_OTHER)

@rt.post("/add-produce")
async def add_produce(n: ProduceInfoForm, pg: asyncpg.pool.Pool = Depends(get_pgpool)):

    # thresh_temp_lo: Optional[float] = float('-inf')
    # thresh_temp_hi: Optional[float] = float('inf')
    # thresh_humidity_lo: Optional[float] = float('-inf')
    # thresh_humidity_hi: Optional[float] = float('inf')
    # thresh_co2_lo: Optional[float] = float('-inf')
    # thresh_co2_hi: Optional[float] = float('inf')
    _n = n
    if not _n.thresh_temp_lo:
        _n.thresh_temp_lo = float('-inf')
    if not _n.thresh_co2_lo:
        _n.thresh_co2_lo = float('-inf')
    if not _n.thresh_humidity_lo:
            _n.thresh_humidity_lo = float('-inf')

    if not _n.thresh_temp_hi:
        _n.thresh_temp_hi = float('inf')
    if not _n.thresh_co2_hi:
        _n.thresh_co2_hi = float('inf')
    if not _n.thresh_humidity_hi:
            _n.thresh_humidity_hi = float('inf')

    async with pg.acquire() as con:
        try:
            d = await con.fetch("insert into produceinfo (harvest_type_name, shelf_life, thresh_temp_lo, thresh_temp_hi, thresh_humidity_lo, thresh_humidity_hi, thresh_co2_lo, thresh_co2_hi) values ($1, $2, $3, $4, $5, $6, $7, $8) returning id",
                        _n.harvest_type_name,
                        _n.shelf_life,
                        _n.thresh_temp_lo,
                        _n.thresh_temp_hi,
                        _n.thresh_humidity_lo,
                        _n.thresh_humidity_hi,
                        _n.thresh_co2_lo,
                        _n.thresh_co2_hi)
            return JSONResponse({"id": d[0]['id']}, 200)
        except Exception as e:
            print(e)
            return JSONResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR)

@rt.delete("/delete-produce")
async def delete_produce(produceId: int, pg = Depends(get_pgpool)):
    try:
        async with pg.acquire() as con:
            await con.execute("delete from produceinfo where id = $1", produceId)
        return PlainTextResponse("")
    except:
        return JSONResponse("cannot remove item or item does not exist", status_code=422)

@rt.post("/edit-produce")
async def edit_produce(produceId: int, n: ProduceInfoForm, pg: asyncpg.pool.Pool = Depends(get_pgpool)):
    _n = n
    if not _n.thresh_temp_lo:
        _n.thresh_temp_lo = float('-inf')
    if not _n.thresh_co2_lo:
        _n.thresh_co2_lo = float('-inf')
    if not _n.thresh_humidity_lo:
            _n.thresh_humidity_lo = float('-inf')

    if not _n.thresh_temp_hi:
        _n.thresh_temp_hi = float('inf')
    if not _n.thresh_co2_hi:
        _n.thresh_co2_hi = float('inf')
    if not _n.thresh_humidity_hi:
            _n.thresh_humidity_hi = float('inf')

    async with pg.acquire() as con:
        try:
            d = await con.fetch("update produceinfo set harvest_type_name = $1, shelf_life = $2, thresh_temp_lo = $3, thresh_temp_hi = $4, thresh_humidity_lo = $5, thresh_humidity_hi = $6, thresh_co2_lo = $7, thresh_co2_hi = $8 where id = $9",
                        _n.harvest_type_name,
                        _n.shelf_life,
                        _n.thresh_temp_lo,
                        _n.thresh_temp_hi,
                        _n.thresh_humidity_lo,
                        _n.thresh_humidity_hi,
                        _n.thresh_co2_lo,
                        _n.thresh_co2_hi,
                        produceId)
            return JSONResponse({"id": d[0]['id']}, 200)
        except Exception as e:
            print(e)
            return JSONResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR)



@rt.post("/set-warehouse-config")
async def set_warehouse_config(config: WarehouseConfig, pg: asyncpg.pool.Pool = Depends(get_pgpool)):
    async with pg.acquire() as conn:
        # iterate each key
        for key, val in config:
            if val == None:
                continue
            # Check if key exists
            if (await conn.fetch("select 1 from configuration where key = $1", key)):
                print(key, "key exists")
                # Routine for updating existing key
                await conn.execute("update configuration set value = $1 where key = $2", str(val), key)
            else:
                print(key, "key not exists")
                # Routine for adding new key
                await conn.execute("insert into configuration (value, key) values ($1, $2)", str(val), key)
