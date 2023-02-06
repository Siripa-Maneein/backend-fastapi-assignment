from fastapi import FastAPI, HTTPException, Body
from datetime import datetime
from pymongo import MongoClient
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import urllib

DATABASE_NAME = "exceed06"
COLLECTION_NAME = "reservation_pa"
load_dotenv('.env')
username = os.getenv('username')
password = urllib.parse.quote(os.getenv('password'))
MONGO_DB_URL = f"mongodb://{username}:{password}@mongo.exceed19.online"
MONGO_DB_PORT = 8443


class Reservation(BaseModel):
    name: str
    start_date: str
    end_date: str
    room_id: int


client = MongoClient(f"{MONGO_DB_URL}:{MONGO_DB_PORT}")

db = client[DATABASE_NAME]

collection = db[COLLECTION_NAME]

app = FastAPI()


def room_avaliable(room_id: int, start_date: str, end_date: str):
    query={"room_id": room_id,
           "$or": 
                [{"$and": [{"start_date": {"$lte": start_date}}, {"end_date": {"$gte": start_date}}]},
                 {"$and": [{"start_date": {"$lte": end_date}}, {"end_date": {"$gte": end_date}}]},
                 {"$and": [{"start_date": {"$gte": start_date}}, {"end_date": {"$lte": end_date}}]}]
            }
    
    result = collection.find(query, {"_id": 0})
    list_cursor = list(result)

    return not len(list_cursor) > 0


@app.get("/reservation/by-name/{name}")
def get_reservation_by_name(name: str):
    reservations = []
    for i in collection.find({'name': name}, {'_id': False}):
        reservations.append(i)
    return {"result": reservations}


@app.get("/reservation/by-room/{room_id}")
def get_reservation_by_room(room_id: int):
    reservations = []
    for i in collection.find({'room_id': room_id}, {'_id': False}):
        reservations.append(i)
    return {"result": reservations}


def validate_date(start_date, end_date):
    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=422, detail="Date out of range")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="The start date must come before the end date.")
    return str(start_date.date()), str(end_date.date())


@app.post("/reservation")
def reserve(reservation: Reservation):
    start_date, end_date = validate_date(reservation.start_date, reservation.end_date)
    room_id = reservation.room_id
    if room_id not in range(1, 11):
        raise HTTPException(status_code=400, detail="We only have room id 1-10.")
    if room_avaliable(room_id=room_id,
                      start_date=start_date,
                      end_date=end_date):
        collection.insert_one({"name": reservation.name,
                               "start_date": start_date,
                               "end_date": end_date,
                               "room_id": reservation.room_id})
    else:
        raise HTTPException(status_code=400, detail="Sorry, Room not available.")


@app.put("/reservation/update")
def update_reservation(reservation: Reservation, new_start_date: str = Body(), new_end_date: str = Body()):
    reservation = collection.find_one(dict(reservation), {"_id": False})
    new_start, new_end = validate_date(new_start_date, new_end_date)
    if reservation and room_avaliable(room_id=reservation["room_id"],
                                      start_date=new_start,
                                      end_date=new_end):
        collection.update_one(reservation, {'$set': {"start_date": new_start,
                                                     "end_date": new_end}})
        return "Reservation updated"
    else:
        raise HTTPException(status_code=400, detail="Reservation not available.")


@app.delete("/reservation/delete")
def cancel_reservation(reservation: Reservation):
    reservation = collection.find_one(dict(reservation), {"_id": False})
    if reservation:
        collection.delete_one(dict(reservation))
    else:
        return HTTPException(status_code=400, detail="Reservation not found.")
