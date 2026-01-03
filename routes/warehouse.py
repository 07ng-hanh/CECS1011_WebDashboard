from fastapi import APIRouter

rt = APIRouter()

@rt.get("/get-warehouse-config")
def get_warehouse_config():
    pass