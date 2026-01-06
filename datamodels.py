from pydantic import BaseModel, field_serializer
import math
from typing import Optional, Any

# test push

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
    import_datetime_utc_int: int # UNIX timestamp at UTC time (milliseconds)

class BatchInfo(BaseModel):
    @classmethod
    def from_list(cls, data: list[Any]):
        return cls(**dict(zip(cls.model_fields, data)))
    batch_id: int
    harvest_type_name: str
    quantity: int
    weight: float
    import_date: int
    exp_date: int
    export_date: Optional[int] = None
    assigned_order_no: Optional[int] = None
    is_in_warehouse: bool
    discard_reason: Optional[str] = None

class ProduceInfoForm(BaseModel):
    harvest_type_name: str
    shelf_life: int
    thresh_temp_lo: Optional[float] = float('-inf')
    thresh_temp_hi: Optional[float] = float('inf')
    thresh_humidity_lo: Optional[float] = float('-inf')
    thresh_humidity_hi: Optional[float] = float('inf')
    thresh_co2_lo: Optional[float] = float('-inf')
    thresh_co2_hi: Optional[float] = float('inf')

    # Since threshold values can contain inf and -inf which are not JSON-compliant
    # the following code serializes such to "Infinity" / "-Infinity" string representation
    @field_serializer('thresh_temp_lo', 'thresh_temp_hi', 'thresh_humidity_lo', 'thresh_humidity_hi', 'thresh_co2_lo', 'thresh_co2_hi')
    def serialize_float(self, v: float):
        if math.isinf(v):
            return "Infinity" if v > 0 else "-Infinity"
        if math.isnan(v):
            return None
        return v

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

class WarehouseConfig(BaseModel):
    capacity: Optional[int] = None
    threshold_auto: Optional[bool] = False
    temperature_low: Optional[float] = float('-inf')
    temperature_hi: Optional[float] = float('inf')
    co2_low: Optional[float] = float('-inf')
    co2_hi: Optional[float] = float('inf')
    humidity_lo: Optional[float] = float('-inf')
    humidity_hi: Optional[float] = float('inf')
