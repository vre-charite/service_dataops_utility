from config import ConfigClass
import requests
from models import filemeta_models as models

class CataLoguingManager:
    base_url = ConfigClass.CATALOGUING_SERVICE_V2
    def create_file_meta(self, post_form: models.FiledataMetaPOST, geid):
        filedata_endpoint = 'filedata'
        print(post_form.labels)
        req_postform = {
            "uploader": post_form.uploader,
            "file_name": post_form.file_name,
            "path": post_form.path,
            "file_size": post_form.file_size,
            "description": post_form.description,
            "namespace": post_form.namespace,
            "project_code": post_form.project_code,
            "labels": post_form.labels,
            "global_entity_id": geid,
            "operator": post_form.operator,
            "processed_pipeline": post_form.process_pipeline
        }
        res = requests.post(json=req_postform, url=self.base_url + filedata_endpoint)
        if res.status_code == 200:
            json_payload = res.json()
            created_entity = None
            if json_payload['result']['mutatedEntities'].get('CREATE'):
                created_entity = json_payload['result']['mutatedEntities']['CREATE'][0]
            elif json_payload['result']['mutatedEntities'].get('UPDATE'):
                created_entity = json_payload['result']['mutatedEntities']['UPDATE'][0]
            if created_entity:
                guid = created_entity['guid']
                return {
                    'guid': guid
                }
            else:
                print('Error on creating atlas entity: ' + json_payload)
                return {
                    'error_code': 500,
                    'result': json_payload
                }
        else:
            json_payload = res.json()
            return {
                'error_code': res.status_code,
                'result': json_payload
            }
    def update_file_meta(self, guid):
        pass
