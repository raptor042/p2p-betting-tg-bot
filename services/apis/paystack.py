import requests
import logging

def create_recipient(name, account, code):
    data = {
        "name": name,
        "account" : account,
        "code" : code
    }
    print(data)
    try:
        response = requests.post("http://localhost:8000/create", json=data)
    except:
        logging.error("Unable to send request to payment gateway")
    else:
        print(response.json())
        return response.json()
    
def init_payment(email, amount):
    try:
        response = requests.get(f"http://localhost:8000/init/{email}/{amount}")
    except:
        logging.error("Unable to send request to payment gateway")
    else:
        print(response.json())
        return response.json()
    
def verify_payment(ref):
    try:
        response = requests.get(f"http://localhost:8000/verify/{ref}")
    except:
        logging.error("Unable to send request to payment gateway")
    else:
        print(response.text)
        return response.text