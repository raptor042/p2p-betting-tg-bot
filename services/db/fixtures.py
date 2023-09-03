import logging

def get_fixture(db, query : dict) -> dict:
    try:
        fixture = db.collection["fixtures"].find_one(query)
    except TimeoutError:
        logging.error("Cannot get fixture data from database, may be due to poor network connectivity")
    else:
        return fixture

def count_fixture(db) -> int:
    try:
        count = db.collection["fixtures"].count_documents({})
    except TimeoutError:
        logging.error("Cannot count fixtures data from database, may be due to poor network connectivity")
    else:
        return count

def set_fixture(db, value : dict) -> dict:
    try:
        fixtures = db.collection["fixtures"].insert_one(value)
    except TimeoutError:
        logging.error("Cannot post fixtures data to database, may be due to poor network connectivity")
    else:
        return fixtures

def update_fixture(db, query: dict, value: dict) -> dict:
    try:
        fixtures = db.collection["fixtures"].update_one(query, value)
    except TimeoutError:
        logging.error("Cannot update fixtures data to database, may be due to poor network connectivity")
    else:
        return fixtures
    
def delete_fixture(db, query: dict) -> dict:
    try:
        fixtures = db.collection["fixtures"].delete_one(query)
    except TimeoutError:
        logging.error("Cannot delete fixtures data to database, may be due to poor network connectivity")
    else:
        return fixtures