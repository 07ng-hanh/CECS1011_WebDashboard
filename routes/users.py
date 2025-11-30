import http.client

import asyncpg.pool
import glide
from fastapi.params import Depends
from fastapi import APIRouter
from fastapi.responses import Response
from fastapi.requests import Request
from starlette.responses import RedirectResponse

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

@rt.get("/request-settings-page")
async def request_settings_page(request: Request):
    # This endpoint can only be reached when the user is authenticated via the middleware
    # This endpoint is for redirecting users to their corresponding settings page (admin, non-admin),
    # and does not do strict restriction enforcement.

    # Enforcement is actually done by the middleware when requesting /users or /admin endpoints.
    # Hence, a non-admin user navigating to the admin's settings page would not automatically bypass the restrictions.

    username = request.cookies.get("username")
    adminID = request.cookies.get("adminID")


    if adminID:
        return RedirectResponse("/static/settings-admin.html", http.client.SEE_OTHER)
    else:
        return RedirectResponse("/static/settings-nonprivileged.html", http.client.SEE_OTHER)