import logging
import requests

logger = logging.getLogger(__name__)

def request_third_party_deposit():
    try:
        response = requests.post("http://localhost:8010/")
        return response.json()
    except Exception as e:
        logger.error(f"Error at request_third_party_deposit: {str(e)}")
        return None
