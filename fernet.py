from services.db.db import connect_db
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

db = connect_db(uri=MONGO_URI)

bets = db.collection["bets"].delete_many({})
print(bets)

pools = db.collection["pools"].delete_many({})
print(pools)

users = db.collection["users"].delete_many({})
print(users)

transactions = db.collection["transactions"].delete_many({})
print(transactions)