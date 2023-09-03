import requests
import logging

def fixtures(date):
    try:
        response = requests.get(f"http://localhost:3030/fixtures/{date}",)
    except:
        logging.error("Unable to send request to payment gateway")
    else:
        print(response.json())
        return response.json()