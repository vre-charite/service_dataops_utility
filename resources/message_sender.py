from config import ConfigClass
import requests

def send_message_to_queue(payload):
    url = ConfigClass.SEND_MESSAGE_URL
    res = requests.post(
        url=url,
        json=payload,
        headers={"Content-type": "application/json; charset=utf-8"}
    )
    print(res.status_code)
    return res.status_code == 200