from http import HTTPStatus

import asyncpg.pool
import glide
from fastapi import Depends, APIRouter
from dependency_injection import get_vk, get_pgpool
from datamodels import NewUserForm
from fastapi.responses import JSONResponse
from argon2 import PasswordHasher

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
async def list_users(page: int = 1, pgpool: asyncpg.pool.Pool = Depends(get_pgpool)):
    async with pgpool.acquire() as con:
        try:
            users = await con.fetchall("select username, is_admin from users limit 20 offset $1", (page - 1) * 20)
            return JSONResponse(users)
        except:
            return JSONResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR)

@rt.delete("/user")
async def delete_user(username: str):
    pass

@rt.put("/user/toggle-admin")
async def toggle_admin(username: str, is_admin: bool):
    pass