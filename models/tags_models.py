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

from typing import List, Optional
from pydantic import BaseModel, validator, Field, root_validator
from models.base_models import APIResponse
from enum import Enum


class TagsAPIPOST(BaseModel):
    tags: List[str]
    inherit: bool = "False"


class SysTagsAPIPOST(BaseModel):
    systags: List[str]
    inherit: bool = "False"


class BatchOpsTagsPOST(BaseModel):
    entity: List[str]
    tags: List[str]
    operation: str = "add/remove"
    inherit: bool = "True"
    only_files: Optional[bool] = "True"


class TagsResponsePOST(APIResponse):
    result: dict = Field({}, example={
            "code": 200,
            "error_msg": "",
            "page": 0,
            "total": 1,
            "num_of_pages": 1,
            "result": {
                "7472aa10-208e-42cb-bdd5-2be49627ca30-1621628879": [
                    "f-k",
                    "k-j"
                ],
                "b46577ef-6f99-469c-8b7c-372a5bbc02c6-1621628906": [
                    "copied-to-core",
                    "f-k",
                    "k-j"
                ],
                "94fb3364-7943-46d4-8459-21871e315aba-1621628908": [
                    "copied-to-core",
                    "f-k",
                    "k-j"
                ],
                "f1e049e0-71a2-4803-91be-d3a810736018-1621628912": [
                    "tag123",
                    "copied-to-core",
                    "f-k",
                    "k-j"
                ],
                "555bec44-c0b5-49ed-8c93-8f7ee2382cd3-1621628916": [
                    "f-k",
                    "k-j",
                    "f-k",
                    "k-j"
                ],
                "3cd5502d-a794-46e0-89f5-4cdc4980a3f0-1621628921": [
                    "tadg4",
                    "copied-to-core",
                    "f-k",
                    "k-j",
                    "f-k",
                    "k-j"
                ],
                "13af67a1-2142-4134-acea-73406fdfb9ed-1621628919": [
                    "cfdsa",
                    "copied-to-core",
                    "f-k",
                    "k-j"
                ],
                "3aaf28f6-4d4f-40d4-b9e6-eb8dfbefb4f4-1621629308": [
                    "copied-to-core",
                    "f-k",
                    "k-j"
                ],
                "6c09d053-236e-4014-ae9e-d0183a6660ef-1621629311": [
                    "copied-to-core",
                    "f-k",
                    "k-j"
                ],
                "c01a211d-8461-4dd4-91e5-fcb321e172f6-1621629315": [
                    "copied-to-core",
                    "f-k",
                    "k-j"
                ],
                "093c0f8a-ee21-43d6-b7d3-0e8d74775846-1621629319": [
                    "copied-to-core",
                    "f-k",
                    "k-j"
                ]
            }
        })
