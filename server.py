import os
from http import HTTPStatus

import glide
from fastapi.params import Depends

from routes.users import rt as users_api_route
from routes.admin import rt as admin_api_route
from routes.sensors import rt as sensors_api_route
from routes.produce import rt as produce_api_route
from routes.config import rt as config_api_route
from routes.batch import rt as batch_api_route
from routes.shipments import rt as shipments_api_route
from routes.suggestion import rt as suggestion_api_route
from dependency_injection import get_vk, get_pgpool

import argon2.exceptions
import asyncpg.pool
import uvicorn
# from dependency_injection import vk1, pgpool
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

# use asyncpg instead of psycopg2 to prevent event loop blocking when doing DB calls
# import psycopg2.pool as psycopg_pool
import asyncpg

import dotenv
from argon2 import PasswordHasher
from fastapi.responses import JSONResponse
from fastapi import Response, FastAPI
from secrets import token_urlsafe

from starlette.requests import Request

# glide is the asynchronous client for valkey
from glide import GlideClient, GlideClientConfiguration, NodeAddress, ExpirySet, ExpiryType

from datamodels import Credentials

# Load environment variables (dev env only)
try:
    dotenv.load_dotenv("private_production.env")
except:
    pass

#TODO: Change to True in production dotenv
secure_cookie = True if os.getenv("SECURE_COOKIE") == "true" else False
session_exp = 2 * 60 * 60

app = FastAPI()
# argon2 password hasher with optimal settings
passwordHasher = PasswordHasher(memory_cost=64, time_cost=3, parallelism=1 )

# Mount the web dashboard interface
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize DB and session storage
@app.on_event("startup")
async def startup_event():
    # assign new valkey client and database pool directly to dependency_injection.py globals
    # this allows FastAPI's Dependency Injection to expose those things in routes
    import dependency_injection as di
    # global vk1, pgpool
    # Connect to session cache
    vk1_conf = GlideClientConfiguration([NodeAddress(os.getenv("VALKEY_HOST"), 6379)], request_timeout=1000)
    di.vk1 = await GlideClient.create(vk1_conf)

    # Connect to DB
    # print(f"postgres://{os.getenv("PG_USER")}:{os.getenv("PG_PASSWORD")}@{os.getenv("PG_HOST")}:{os.getenv("PG_PORT")}/{os.getenv("PG_DATABASE")}")

    di.pgpool = await asyncpg.create_pool(f"postgresql://{os.getenv("PG_USER")}:{os.getenv("PG_PASSWORD")}@{os.getenv("PG_HOST")}:{os.getenv("PG_PORT")}/{os.getenv("PG_DATABASE")}", min_size=5, max_size=30)
    # Load configs into valkey
    conf = await di.pgpool.fetch("select key, value from configuration")
    for key, value in conf:
        await di.vk1.set(f"CONFIG_{key}", str(value))

    app.include_router(users_api_route, prefix="/api/users")
    app.include_router(admin_api_route, prefix="/admin")
    app.include_router(sensors_api_route, prefix="/api/sensors")
    app.include_router(produce_api_route, prefix="/api/produce")
    app.include_router(config_api_route, prefix="/api/config")
    app.include_router(batch_api_route, prefix="/api/batch")
    app.include_router(shipments_api_route, prefix="/api/shipments")
    app.include_router(suggestion_api_route, prefix="/api/suggestion")

# Session Checker Middleware for APIs
@app.middleware("http")
async def check_session_validity(request: Request, call_next):

    vk1 = await get_vk()
    # If the request targets /api endpoints or /admin endpoints, check cookie against server store for validity
    if request.url.path.startswith("/api") or (request.url.path.startswith("/static") and not request.url.path.startswith("/static/login")):
        sent_cookie_token = request.cookies.get("sessionID")

        # No session cookie, no proceeding
        if sent_cookie_token == None:
            return RedirectResponse("/static/login.html", status_code=HTTPStatus.SEE_OTHER)

        username = request.cookies.get("username")
        # Check if the key is valid AND the user owns that key
        # For invalid or expired ttl-bound keys, valkey returns a value <= 0.

        if (await vk1.ttl(sent_cookie_token)) <= 0 or (await vk1.get(sent_cookie_token)).decode() != username:
            # Reject access and redirect to Session Expired page
            return RedirectResponse("/static/login.html", status_code=HTTPStatus.UNAUTHORIZED)
        else:
            # Not requesting admin API access - can pass to the actual request
            # For each server-side request, we reset the inactivity timeout.
            # await vk1.setex("sessionID", session_exp, sent_cookie_token)
            await vk1.set(sent_cookie_token, username, conditional_set=None, expiry=ExpirySet(ExpiryType.SEC, session_exp))

            # Create a reverse map of user to list of available session tokens for easier mass revocation
            await vk1.sadd(username, [sent_cookie_token, ])

            return await call_next(request)


    # Fix a bug where the admin endpoint cant be accessed because the program was looking for both adminID and sessionID, the latter of which aren't sent with requests to admin APIs.
    elif request.url.path.startswith("/admin"):
        sent_cookie_token = request.cookies.get("adminID")

        # No session cookie, no proceeding
        if sent_cookie_token == None:
            # Since this is to block non-admins from accessing admin features, there's no point in showing the "Session Invalid/Expired" Screen here.
            return JSONResponse({}, HTTPStatus.UNAUTHORIZED)

        username = request.cookies.get("username")
        # Check if the key is valid AND the user owns that key
        # For invalid or expired ttl-bound keys, valkey returns a value <= 0.
        if (await vk1.ttl(sent_cookie_token)) <= 0 or (await vk1.get(sent_cookie_token)).decode() != username:
            # Reject access and redirect to Session Expired page
            return JSONResponse({}, HTTPStatus.UNAUTHORIZED)
        else:
            # Check with database if it's actual administrator.

            pgpool = await get_pgpool()
            async with pgpool.acquire() as con:
                is_admin = await con.fetchval("select is_admin from users where username = $1", username, )
                if is_admin:
                    return await call_next(request)
                else:
                    return JSONResponse({}, HTTPStatus.UNAUTHORIZED)

    else:
        # DO NOT capture other requests (for login, dashboard HTMLs, etc.)
        print(str(request))
        return await call_next(request)


@app.post("/session")
async def create_session(credentials: Credentials, response: Response, vk1 = Depends(get_vk), pgpool = Depends(get_pgpool)):
    print(type(pgpool), type(vk1))
    async with pgpool.acquire() as con:
        # Get the provided credentials and compare them to the one in the database via hashing

        db_return = await con.fetchrow("select password_hash, is_admin from users where username = $1", credentials.username)
        if db_return == None:
            return JSONResponse({"status": "failed"}, HTTPStatus.UNAUTHORIZED)
        correct_p_hash, is_admin = db_return
        try:
            # If the password and the hash matches, issue a session cookie that lasts until the browser is closed.
            # Otherwise, handle the exception raised by PasswordHasher

            if passwordHasher.verify(correct_p_hash, f"{credentials.username}::{credentials.password}"):
                cookie_token = f"{credentials.username}_{token_urlsafe(32)}"
                response.set_cookie(
                    key="sessionID",
                    value= cookie_token,
                    path="/",
                    secure=secure_cookie,
                    httponly=True,
                    samesite="strict",
                )

                # Username cookie for representing user across UI pages - not for authentication.
                response.set_cookie(
                    key="username",
                    value= credentials.username,
                    path="/",
                    secure=secure_cookie,
                    httponly=False,
                )
                # Save the Session ID server-side with inactivity timeout of 2 hours.
                # await vk1.set(name=cookie_token, time=session_exp, value=credentials.username)
                await vk1.set(cookie_token, credentials.username, conditional_set=None, expiry=ExpirySet(ExpiryType.SEC, session_exp))

                if is_admin:
                    # If user is admin, provide an additional session cookie to allow access to admin panel
                    response.set_cookie(
                        key="adminID",
                        value= cookie_token,
                        path="/admin",
                        secure=secure_cookie,
                        httponly=True,
                        samesite="strict"
                    )

                return {"status": "success", "isadmin": is_admin}

        except argon2.exceptions.VerifyMismatchError:
            return JSONResponse({"status": "failed"}, HTTPStatus.UNAUTHORIZED)

@app.get("/")
async def reroute_to_dashboard_ui(request: Request, vk1: glide.GlideClient = Depends(get_vk)):
    """
    If the session cookie is present, redirect user to dashboard or admin page.
    Otherwise, redirect to the login page
    """

    # Check session validity
    # If session is valid, redirect straight to dashboard

    uid = request.cookies.get("sessionID")
    print("uid", uid, request.cookies.get("sessionID"))
    try:
        if not uid:
            print("no uid or invalid uid")
            return RedirectResponse("/static/login.html")

        elif (await vk1.get(uid)).decode() == request.cookies.get("username") and (await vk1.ttl(uid)) > 0:
            return RedirectResponse("/static/dashboard.html")
        else:
            print("no uid or invalid uid")

            return RedirectResponse("/static/login.html")
    except:
        print("no uid or invalid uid")
        return RedirectResponse("/static/login.html")

# Run the app
uvicorn.run(app, timeout_keep_alive=0, timeout_graceful_shutdown=0, port=7860, host="0.0.0.0")