import os
from http import HTTPStatus


import argon2.exceptions
import asyncpg.pool
import uvicorn
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

# Load environment variables
dotenv.load_dotenv("private.env")
#TODO: Change to True in production dotenv
secure_cookie = True if os.getenv("SECURE_COOKIE") == "true" else False
session_exp = 2 * 60 * 60

app = FastAPI()
# argon2 password hasher with optimal settings
passwordHasher = PasswordHasher(memory_cost=64, time_cost=3, parallelism=1 )

# Set up database connection
# pgpool = psycopg_pool.ThreadedConnectionPool(minconn=5, maxconn=60, user=os.getenv("PG_USER"), password=os.getenv("PG_PASSWORD"), host=os.getenv("PG_HOST"), port=os.getenv("PG_PORT"), database=os.getenv("PG_DATABASE"))
# Mount the web dashboard interface
app.mount("/static", StaticFiles(directory="static"), name="static")

vk1: GlideClient = None
pgpool: asyncpg.pool.Pool = None
# Initialize DB and session storage
@app.on_event("startup")
async def startup_event():
    global vk1, pgpool
    # Connect to session cache
    vk1_conf = GlideClientConfiguration([NodeAddress("0.0.0.0", 6379)], request_timeout=1000)
    vk1 = await GlideClient.create(vk1_conf)

    # Connect to DB
    pgpool = await asyncpg.create_pool(f"postgres://{os.getenv("PG_USER")}:{os.getenv("PG_PASSWORD")}@{os.getenv("PG_HOST")}:{os.getenv("PG_PORT")}/{os.getenv("PG_DATABASE")}", min_size=5, max_size=30)

# Session Checker Middleware
@app.middleware("http")
async def check_session_validity(request: Request, call_next):

    # If the request targets /api endpoints or /admin endpoints, check cookie against server store for validity
    if request.url.path.startswith("/api") or request.url.path.startswith("/admin"):
        sent_cookie_token = request.cookies["sessionID"]
        username = request.cookies["username"]
        # Check if the key is valid AND the user owns that key
        # For invalid or expired ttl-bound keys, valkey returns a value <= 0.
        if (await vk1.ttl(sent_cookie_token)) <= 0 and (await vk1.get(sent_cookie_token)) == username:
            # Reject access and redirect to Session Expired page
            return RedirectResponse("/static/session_invalid.html")
        else:
            if request.url.path.startswith("/admin"):
                # Check against DB if user is really admin before granting access to admin APIs
                # if yes, pass on, else, reject
                # async with pgpool.acquire() as cur:
                #     await cur.("select is_admin from users where username = %s", (username,))
                #     is_admin = cur.fetchone()[0]
                #     if is_admin:
                #         return await call_next(request)
                #     else:
                #         return JSONResponse({}, HTTPStatus.UNAUTHORIZED)

                async with pgpool.acquire() as con:
                    is_admin = await con.fetchval("select is_admin from users where username = $1", username, )
                    if is_admin:
                        return await call_next(request)
                    else:
                        return JSONResponse({}, HTTPStatus.UNAUTHORIZED)
            else:
                # Not requesting admin API access - can pass to the actual request
                # For each server-side request, we reset the inactivity timeout.
                # await vk1.setex("sessionID", session_exp, sent_cookie_token)
                await vk1.set(sent_cookie_token, username, conditional_set=None, expiry=ExpirySet(ExpiryType.SEC, session_exp))
                return await call_next(request)

    else:
        # DO NOT capture other requests (for login, dashboard html, etc.)
        return await call_next(request)


@app.post("/session")
async def create_session(credentials: Credentials, response: Response):
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
                cookie_token = token_urlsafe(32)
                response.set_cookie(
                    key="sessionID",
                    value= cookie_token,
                    path="/api",
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
async def reroute_to_dashboard_ui():
    """
    If the session cookie is present, redirect user to dashboard or admin page.
    Otherwise, redirect to the login page
    """
    return RedirectResponse("/static/login.html")
# Run the app
uvicorn.run(app)