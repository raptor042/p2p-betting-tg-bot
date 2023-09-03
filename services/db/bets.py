import logging

def get_bet(db, query : dict) -> dict:
    try:
        bet = db.collection["bets"].find_one(query)
    except TimeoutError:
        logging.error("Cannot get bet data to database, may be due to poor network connectivity")
    else:
        return bet

def set_bet(db, value : dict) -> dict:
    try:
        bet = db.collection["bets"].insert_one(value)
    except TimeoutError:
        logging.error("Cannot post bet data to database, may be due to poor network connectivity")
    else:
        return bet

def update_bet(db, query: dict, value: dict) -> dict:
    try:
        bet = db.collection["bets"].update_one(query, value)
    except TimeoutError:
        logging.error("Cannot update bet data to database, may be due to poor network connectivity")
    else:
        return bet
    
def delete_bet(db, query: dict) -> dict:
    try:
        bet = db.collection["bets"].delete_one(query)
    except TimeoutError:
        logging.error("Cannot delete bet data to database, may be due to poor network connectivity")
    else:
        return bet