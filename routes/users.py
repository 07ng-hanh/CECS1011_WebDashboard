import asyncpg.pool
import glide
from fastapi.params import Depends
from fastapi import APIRouter
from fastapi.responses import Response
from fastapi.requests import Request

from dependency_injection import get_pgpool, get_vk

rt = APIRouter()

@rt.delete("/revoke-session")
async def log_out(request: Request, response: Response, vk: glide.GlideClient = Depends(get_vk)):
    # Remove session from valkey
    sessionID = request.cookies.get("sessionID")
    print(sessionID)

    await vk.delete(sessionID)
    try:
        response.delete_cookie("sessionID", path="/api")
        response.delete_cookie("username", path="/")
        response.delete_cookie("adminID", path="/admin")
    except:
        pass

    response.status_code = 200

    return response