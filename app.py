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

from functools import partial

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi_sqlalchemy import DBSessionMiddleware
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from api.routes import api_router
from api.routes import api_router_v2
from config import Settings
from config import get_settings
from dependencies import get_redis


def create_app() -> FastAPI:
    """Initialize and configure the application."""

    settings = get_settings()

    app = FastAPI(
        title='Dataops Service',
        description='Dataops',
        docs_url='/v1/api-doc',
        version=settings.VERSION,
    )

    setup_routers(app)
    setup_middlewares(app, settings)
    setup_dependencies(app, settings)
    setup_exception_handlers(app)
    setup_tracing(app, settings)

    return app


def setup_routers(app: FastAPI) -> None:
    """Configure the application routers."""

    app.include_router(api_router, prefix='/v1')
    app.include_router(api_router_v2, prefix='/v2')


def setup_middlewares(app: FastAPI,  settings: Settings) -> None:
    """Configure the application middlewares."""

    app.add_middleware(
        CORSMiddleware,
        allow_origins='*',
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )


def setup_dependencies(app: FastAPI, settings: Settings) -> None:
    """Perform dependencies setup/teardown at the application startup/shutdown events."""

    app.add_event_handler('startup', partial(startup_event, settings))


async def startup_event(settings: Settings) -> None:
    """Initialise dependencies at the application startup event."""

    await get_redis(settings=settings)


def setup_exception_handlers(app: FastAPI) -> None:
    """Configure the application exception handlers."""

    app.add_exception_handler(Exception, global_exception_handler)


def global_exception_handler(request: Request, exception: Exception) -> JSONResponse:
    """Return the default response structure for all unhandled exceptions."""

    return JSONResponse(status_code=500, content={'error_msg': 'Internal Server Error'})


def setup_tracing(app: FastAPI, settings: Settings) -> None:
    """Instrument the application with OpenTelemetry tracing."""

    if not settings.OPEN_TELEMETRY_ENABLED:
        return

    tracer_provider = TracerProvider(resource=Resource.create({SERVICE_NAME: settings.APP_NAME}))
    trace.set_tracer_provider(tracer_provider)

    FastAPIInstrumentor.instrument_app(app)
    RequestsInstrumentor().instrument()
    LoggingInstrumentor().instrument()

    jaeger_exporter = JaegerExporter(
        agent_host_name=settings.OPEN_TELEMETRY_HOST, agent_port=settings.OPEN_TELEMETRY_PORT
    )

    tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
