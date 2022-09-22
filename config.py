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

from functools import lru_cache
from typing import Any
from typing import Dict
from typing import Optional

from common import VaultClient
from pydantic import BaseSettings
from pydantic import Extra


class VaultConfig(BaseSettings):
    """Store vault related configuration."""

    APP_NAME: str = 'service_dataops_utility'
    CONFIG_CENTER_ENABLED: bool = False

    VAULT_URL: Optional[str]
    VAULT_CRT: Optional[str]
    VAULT_TOKEN: Optional[str]

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


def load_vault_settings(settings: BaseSettings) -> Dict[str, Any]:
    config = VaultConfig()

    if not config.CONFIG_CENTER_ENABLED:
        return {}

    client = VaultClient(config.VAULT_URL, config.VAULT_CRT, config.VAULT_TOKEN)
    return client.get_from_vault(config.APP_NAME)


class Settings(BaseSettings):
    """Store service configuration settings."""

    APP_NAME: str = 'service_dataops_utility'
    VERSION = '0.3.0'
    PORT: int = 5063
    HOST: str = '127.0.0.1'
    env: str = ''
    namespace: str = ''

    GREEN_ZONE_LABEL: str = 'Greenroom'
    CORE_ZONE_LABEL: str = 'Core'

    AUTH_SERVICE: str
    NEO4J_SERVICE: str
    ENTITYINFO_SERVICE: str
    CATALOGUING_SERVICE: str
    QUEUE_SERVICE: str
    SEND_MESSAGE_URL: str
    PROVENANCE_SERVICE: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str

    RDS_DB_URI: str

    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_HTTPS: bool = False

    OPEN_TELEMETRY_ENABLED: bool = False
    OPEN_TELEMETRY_HOST: str = '127.0.0.1'
    OPEN_TELEMETRY_PORT: int = 6831

    def __init__(self):
        super().__init__()

        self.AUTH_SERVICE = self.AUTH_SERVICE + '/v1/'
        NEO4J_HOST = self.NEO4J_SERVICE
        self.NEO4J_SERVICE = NEO4J_HOST + '/v1/neo4j/'
        self.NEO4J_SERVICE_V2 = NEO4J_HOST + '/v2/neo4j/'
        self.ENTITYINFO_SERVICE = self.ENTITYINFO_SERVICE + '/v1/'
        self.CATALOGUING_SERVICE_V2 = self.CATALOGUING_SERVICE + '/v2/'
        self.QUEUE_SERVICE = self.QUEUE_SERVICE + '/v1/'
        self.SEND_MESSAGE_URL = self.SEND_MESSAGE_URL + '/v1/send_message'
        self.PROVENANCE_SERVICE = self.PROVENANCE_SERVICE + '/v1/'
        self.MINIO_SERVICE = 'http://' + self.MINIO_ENDPOINT
        self.RDS_DB_URI = self.RDS_DB_URI.replace('postgresql', 'postgresql+asyncpg')

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = Extra.allow

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            return env_settings, load_vault_settings, init_settings, file_secret_settings


@lru_cache(1)
def get_settings():
    settings = Settings()
    return settings


ConfigClass = get_settings()
