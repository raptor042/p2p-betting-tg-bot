import logging

def get_pool(db, query : dict) -> dict:
    try:
        pool = db.collection["pools"].find_one(query)
    except TimeoutError:
        logging.error("Cannot get pool data to database, may be due to poor network connectivity")
    else:
        return pool

def set_pool(db, value : dict) -> dict:
    try:
        pool = db.collection["pools"].insert_one(value)
    except TimeoutError:
        logging.error("Cannot post pool data to database, may be due to poor network connectivity")
    else:
        return pool

def update_pool(db, query: dict, value: dict) -> dict:
    try:
        pool = db.collection["pools"].update_one(query, value)
    except TimeoutError:
        logging.error("Cannot update pool data to database, may be due to poor network connectivity")
    else:
        return pool
    
def delete_pool(db, query: dict) -> dict:
    try:
        pool = db.collection["pools"].delete_one(query)
    except TimeoutError:
        logging.error("Cannot delete pool data to database, may be due to poor network connectivity")
    else:
        return pool