import os
import fastapi
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import psycopg2.pool as psycopg_pool
import dotenv
from argon2 import PasswordHasher

from datamodels import Credentials

# Load environment variables
dotenv.load_dotenv("private.env")
app = fastapi.FastAPI()
# argon2 password hasher with optimal settings
passwordHasher = PasswordHasher(memory_cost=64, time_cost=3, parallelism=1 )

# Set up database connection
pgpool = psycopg_pool.ThreadedConnectionPool(minconn=5, maxconn=60, user=os.getenv("PG_USER"), password=os.getenv("PG_PASSWORD"), host=os.getenv("PG_HOST"), port=os.getenv("PG_PORT"), database=os.getenv("PG_DATABASE"))

# Mount the web dashboard interface
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post("/session")
async def create_session(credentials: Credentials):
    with pgpool.getconn().cursor() as cur:
        # Get the provided credentials and compare them to the one in the database via hashing
        pass
    pass

@app.delete("/session/:id")
async def revoke_session(id: int):
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