import requests
import logging
    
def init_payment(email, amount, ref, currency):
    data = {
        "email": email,
        "amount" : amount,
        "ref" : ref,
        "currency" : currency
    }
    print(data)
    try:
        response = requests.post(f"http://localhost:8000/init", json=data)
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

def banks(country):
    try:
        response = requests.get(f"http://localhost:8000/banks/{country}")
    except:
        logging.error("Unable to send request to payment gateway")
    else:
        return response.json()
    
def branches(id):
    try:
        response = requests.get(f"http://localhost:8000/branches/{id}")
    except:
        logging.error("Unable to send request to payment gateway")
    else:
        return response.json()

def beneficiary(params):
    data = {
        "bank_code" : params["code"],
        "number": params["number"],
        "name" : params["name"],
        "currency" : params["currency"]
    }
    print(data)
    try:
        response = requests.post(f"http://localhost:8000/beneficiary", json=data)
    except:
        logging.error("Unable to send request to payment gateway")
    else:
        print(response.json())
        return response.json()
    
def transfer(params):
    try:
        response = requests.post(f"http://localhost:8000/transfer", json=params)
        print(params)
    except:
        logging.error("Unable to send request to payment gateway")
    else:
        print(response.json())
        return response.json()
    
def transfer_fee(amount, currency):
    try:
        response = requests.get(f"http://localhost:8000/transfer_fee/{amount}/{currency}")
    except:
        logging.error("Unable to send request to payment gateway")
    else:
        print(response.text)
        return response.text
    
def transaction_fee(amount, currency):
    try:
        response = requests.get(f"http://localhost:8000/transaction_fee/{amount}/{currency}")
    except:
        logging.error("Unable to send request to payment gateway")
    else:
        print(response.text)
        return response.text