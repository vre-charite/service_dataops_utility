from config import ConfigClass
import requests

def fetch_geid(id_type):
    ## fetch global entity id
    entity_id_url = ConfigClass.UTILITY_SERVICE + "/v1/utility/id?entity_type={}".format(id_type)
    respon_entity_id_fetched = requests.get(entity_id_url)
    if respon_entity_id_fetched.status_code == 200:
        pass
    else:
        raise Exception('Entity id fetch failed: ' + entity_id_url + ": " + str(respon_entity_id_fetched.text))
    trash_geid = respon_entity_id_fetched.json()['result']
    return trash_geid