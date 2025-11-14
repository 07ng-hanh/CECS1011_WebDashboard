import os

import fastapi
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import psycopg2.pool as psycopg_pool
import dotenv

# Load environment variables
dotenv.load_dotenv("private.env")
app = fastapi.FastAPI()

# Set up database connection
pgpool = psycopg_pool.ThreadedConnectionPool(minconn=5, maxconn=60, user=os.getenv("PG_USER"), password=os.getenv("PG_PASSWORD"), host=os.getenv("PG_HOST"), port=os.getenv("PG_PORT"), database=os.getenv("PG_DATABASE"))

# Mount the web dashboard interface
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post("/session")
async def create_session():
    pass

@app.delete("/session")
async def revoke_session():
    pass

@app.get("/")
async def reroute_to_dashboard_ui():
    """
    If the session cookie is present, redirect user to dashboard or admin page.
    Otherwise, redirect to the login page
    """

    return RedirectResponse("/static/login.html")

# Run the app
uvicorn.run(app)