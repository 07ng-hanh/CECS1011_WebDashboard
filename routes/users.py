import asyncpg.pool
import glide
from fastapi.params import Depends
from fastapi import APIRouter
from fastapi.responses import Response
from fastapi.requests import Request
from dependency_injection import get_pgpool, get_vk
from fastapi.responses import PlainTextResponse


rt = APIRouter()

@rt.delete("/revoke-session")
async def log_out(request: Request, response: Response, vk: glide.GlideClient = Depends(get_vk)):
    # Remove session from valkey
    sessionID = request.cookies.get("sessionID")

    await vk.delete([sessionID])
    # print(d)
    try:
        response.delete_cookie("sessionID", path="/api")
        response.delete_cookie("username", path="/")
        response.delete_cookie("adminID", path="/admin")
    except:
        pass

    response.status_code = 200

    return response

@rt.get("/check-logon")
async def check_logon():
    # This endpoint is only reachable if the user is authenticated
    # Which is checked at the authentication middleware
    # Hence, we can return 200 here

    return PlainTextResponse("")
