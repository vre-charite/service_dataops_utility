from fastapi import Depends
from config import ConfigClass
from auth import jwt_required
import requests
import json


def check_folder_permissions(folder_id: int, current_identity = Depends(jwt_required)):
    url = ConfigClass.NEO4J_SERVICE + "relations"
    params = {"start_id": current_identity["user_id"], "end_id": folder_id}
    res = requests.get(url=url, params=params)
    if(res.status_code != 200):
        raise Exception("Unauthorized: " + str(res.json()))
    relations = json.loads(res.text)
    if not relations or not relations[0]['r']['type'] == 'owner':
        raise Exception("Unauthorized: " + str(res.json()))
    return current_identity
