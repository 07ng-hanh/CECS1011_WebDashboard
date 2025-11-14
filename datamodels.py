from pydantic import BaseModel
from typing import Optional

class Credentials(BaseModel):
    username: str
    password: str

class NewUserForm(Credentials):
    isadmin: bool

class PasswordResetForm(Credentials):
    newpassword: str

class NewBatchForm(BaseModel):
    product_type_id: int
    weight: float
    quantity: int
    import_date: int # UNIX timestamp at UTC time (seconds)
    export_date: int # UNIX timestamp at UTC time (seconds)
    assigned_order_no: int # UNIX timestamp at UTC time (seconds)

class ProduceInfoForm(BaseModel):
    harvest_type_name: str
    shelf_life: int
    thresh_temp_lo: float
    thresh_temp_hi: float
    thresh_humidity_lo: float
    thresh_humidity_hi: float
    thresh_co2_lo: float
    thresh_co2_hi: float

class EnvironmentReading(BaseModel):
    timestamp: int # UNIX timestamp at UTC time (seconds)
    temperature: float
    co2: float
    humidity: float

class ExportOrder(BaseModel):
    departure_port_name: str
    departure_port_lat: float
    departure_port_lon: float
    destination_port_name: str
    destination_port_lat: float
    destination_port_lon: float
    departure_day: int
