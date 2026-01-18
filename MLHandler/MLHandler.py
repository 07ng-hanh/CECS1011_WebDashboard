"""
Handler for machine learning models.
Implement the ML logic in the ML_logic function.
"""
import json
import os
from typing import List

from fastapi import APIRouter

import requests
from pydantic import BaseModel

# shipments: shipment_id, produce_id, remaining_quantity_needed, scheduled_departure, eta
# available batches: batch_id, produce_id, quantity, exp_date

class Shipment(BaseModel):
    shipment_id: int
    produce_id: int
    remaining_quantity_needed: int
    schedule_departure: int
    eta: int
    schedule_arrival: int

class Batch(BaseModel):
    batch_id: int
    produce_id: int
    quantity: int
    exp_date_timestamp: int

class ResultPair(BaseModel):
    shipment_id: int
    batch_id: int

class ResultList(BaseModel):
    results: List[ResultPair]

def write_result_to_file(job_id, results: List[ResultPair]):

    if results == None:
        with open(f"{job_id}.json", "w") as p:
            p.write("ERROR")
        return

    with open(f"{job_id}.json", "w") as p:
        p.write(ResultList(results=results).model_dump_json())


def ML_logic(shipment_lst: List[Shipment], batch_lst: List[Batch]) -> List[ResultPair]:
    """ Implement ML logic here. """


    # Provide some hard-rule groundings and csv_formatting
    batch_csv = ["batch_id,produce_id,quantity,expiration_date_timestamp,eligible_shipment_ids"]
    shipment_csv = ["shipment_id,produce_id,target_quantity,scheduled_arrival_timestamp"]

    for shipment in shipment_lst:
        shipment_csv.append(",".join([str(shipment.shipment_id), str(shipment.produce_id), str(shipment.remaining_quantity_needed), str(shipment.schedule_arrival)]))

    for batch in batch_lst:
        eligible_shipments = [str(x.shipment_id) for x in filter(lambda shipment: shipment.produce_id == batch.produce_id and shipment.schedule_arrival < batch.exp_date_timestamp, shipment_lst)]
        batch_csv.append(",".join([
            str(batch.batch_id), str(batch.produce_id), str(batch.quantity), str(batch.exp_date_timestamp), "::".join(eligible_shipments)
        ]))

    shipment_csv_str = "\n".join(shipment_csv)
    batch_csv_str = "\n".join(batch_csv)

    headers = {
        'x-goog-api-key': os.getenv('GEMINI_API_KEY', ''),
        'Content-Type': 'application/json',
    }
    json_data = {
        'contents': [
            {
                'parts': [
                    {
                        'text': f"""
                        You are provided with the following hypothetical list of shipments and produce batches. Please devise an optimized
                        batch-to-shipment allocation strategy based on these ground rules:
                        1. You can only allocate one shipment to one batch.
                        2. The allocated shipment for each batch must be in the eligible_shipment_ids list separated by ::.
                        3. Aim for exporting as many batches as possible. Each batch must either not be transported, or be transported in whole.
                        4. You may say your thinking process as needed, but the final result must be a batch-to-shipment mapping CSV table
                        with the columns "batch_id" and "shipment_id".
                        5. It is not required to fulfill a shipment completely.
                        6. Stop answering immediately after returning the result table.
                        
                        Shipments table:
                        '''csv
                        {shipment_csv_str}
                        '''
                        
                        Batches table:
                        '''csv
                        {batch_csv_str}
                        '''
                         
                        """,
                    },
                ],
            },
        ],
    }



    response = requests.post(
        'https://generativelanguage.googleapis.com/v1beta/models/gemma-3-27b-it:generateContent',
        headers=headers,
        json=json_data,
    )
    if response.status_code == 200:
        raw_resp: str = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        parsed_rep = raw_resp[raw_resp.rfind("csv")+3:].strip().strip("`").strip("\'")

        print(parsed_rep)

        parsed_grid = [line.split(',') for line in parsed_rep.split('\n')]
        final_lst: List[ResultPair] = []
        for line in parsed_grid[1:]:
            if (len(line) < 2):
                continue
            batch_id = line[0] if parsed_grid[0][0] == 'batch_id' else line[1]
            shipment_id = line[0] if parsed_grid[0][0] == 'shipment_id' else line[1]
            final_lst.append(ResultPair(shipment_id=int(shipment_id), batch_id=int(batch_id)))
        return final_lst
    else:
        raise BaseException("Generation failed with code " + str(response.status_code))


def caller(job_id, shipment_lst: List[Shipment], batch_lst: List[Batch]):
    try:
        r = ML_logic(shipment_lst, batch_lst)
        write_result_to_file(job_id, r)
    except Exception as e:

        write_result_to_file(job_id, None)
        raise e

if __name__ == "__main__":
    print(caller())