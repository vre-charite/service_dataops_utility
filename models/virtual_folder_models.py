from pydantic import BaseModel, Field
from models.base_models import APIResponse


### VirtulFolderFileGET ###
class VirtualFolderGETResponse(APIResponse):
    result: list = Field([], example=[{   
            'container_id': 1129,
            'id': 29,
            'labels': ['VirtualFolder'],
            'name': 'test-folder',
            'time_created': '2020-12-01T20:45:25',
            'time_lastmodified': '2020-12-01T20:45:25'},
        ]
    )


### VirtulFolderFilePOST ###
class VirtualFolderPOST(BaseModel):
    name: str 
    container_id: int 


class VirtualFolderPOSTResponse(APIResponse):
    result: dict = Field({}, example={   
              'container_id': 1129,
              'id': 1211,
              'labels': ['VirtualFolder'],
              'name': 'limittestfdsad',
              'time_created': '2020-12-09T15:08:29',
              'time_lastmodified': '2020-12-09T15:08:29'
          }
      )

### VirtulFolderFilePUT ###
class VirtualFolderPUT(BaseModel):
    vfolders: list 


class VirtualFolderPUTResponse(APIResponse):
    result: dict = Field([], example=[{   
              'container_id': 1129,
              'id': 1211,
              'labels': ['VirtualFolder'],
              'name': 'limittestfdsad',
              'time_created': '2020-12-09T15:08:29',
              'time_lastmodified': '2020-12-09T15:08:29'
          }]
      )


### VirtulFolderFilePUT ###
class VirtualFolderFilePUT(BaseModel):
    name: str = Field('', example='folder_name')


class VirtualFolderFilePUTResponse(BaseModel):
    result: dict = Field({}, example={   
              'container_id': 1129,
              'id': 1211,
              'labels': ['VirtualFolder'],
              'name': 'limittestfdsad',
              'time_created': '2020-12-09T15:08:29',
              'time_lastmodified': '2020-12-09T15:08:29'
          }
      )


### VirtulFolderFileDelete ###
class VirtualFolderFileDELETEResponse(APIResponse):
    result: str = Field('', example='success')


### VirtulFileBulk ###
class VirtualFileBulkPOSTResponse(APIResponse):
    result: str = Field('', example='success')


class VirtualFileBulkPOST(BaseModel):
    geids: list 


### VirtualFileBulkDELETE ###
class VirtualFileBulkDELETEResponse(APIResponse):
    result: str = Field('', example='success')

class VirtualFileBulkDELETE(BaseModel):
    geids: list 


### VirtualFolderFileGET
class VirtualFolderFileGETResponse(APIResponse):
    result: list = Field([], example=[  
                 {   'archived': False,
                      'file_size': 1409578,
                      'full_path': '/vre-data/gregtest/raw/OIP.WH4UEecUNFLkLRAy3cbgQQHaEK.jpg',
                      'generate_id': 'undefined',
                      'global_entity_id': 'file_data-2bed2e20-64c9-11eb-b013-be498ca98c54-1612210075',
                      'guid': '189cc59e-5c50-4857-a7a6-fca7848ad51c',
                      'id': 501,
                      'labels': ['File', 'VRECore', 'Processed'],
                      'name': 'OIP.WH4UEecUNFLkLRAy3cbgQQHaEK.jpg',
                      'operator': 'admin',
                      'path': '/vre-data/gregtest/raw',
                      'process_pipeline': 'data_transfer',
                      'tags': [],
                      'time_created': '2021-02-01T20:07:55',
                      'time_lastmodified': '2021-02-01T20:07:55',
                      'uploader': 'admin'}
        ]
    )
