from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from api.routes import api_router
import uvicorn


app = FastAPI(
    title="Dataops Service",
    description="Dataops",
    docs_url="/v1/api-docs",
    version="0.3.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()

app.include_router(api_router, prefix="/v1")

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=5063, log_level="info", reload=True)
