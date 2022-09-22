# Copyright 2022 Indoc Research
# 
# Licensed under the EUPL, Version 1.2 or – as soon they
# will be approved by the European Commission - subsequent
# versions of the EUPL (the "Licence");
# You may not use this work except in compliance with the
# Licence.
# You may obtain a copy of the Licence at:
# 
# https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
# 
# Unless required by applicable law or agreed to in
# writing, software distributed under the Licence is
# distributed on an "AS IS" basis,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied.
# See the Licence for the specific language governing
# permissions and limitations under the Licence.
# 

from config import ConfigClass
import requests
from models import filemeta_models as models
import httpx

class CataLoguingManager:
    base_url = ConfigClass.CATALOGUING_SERVICE_V2
    async def create_file_meta(self, post_form: models.FiledataMetaPOST, geid):
        filedata_endpoint = 'filedata'
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
        
        async with httpx.AsyncClient() as client:
            res = await client.post(
                json=req_postform, 
                url=self.base_url + filedata_endpoint,
                timeout=None
            )
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
