# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.routers import search, judgments, embed, filters, summaries, chat, folder_chat

app = FastAPI(
    title="Legal RAG API",
    version="1.0.0",
    description="API do wyszukiwania semantycznego orzeczeń sądowych i aktów prawnych",
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, tags=["search"])
app.include_router(summaries.router, prefix="/judgments", tags=["summary"])
app.include_router(judgments.router, prefix="/judgments", tags=["judgments"])
app.include_router(chat.router, prefix="/judgments", tags=["chat"])
app.include_router(folder_chat.router, tags=["folder-chat"])
app.include_router(embed.router, prefix="/embed", tags=["embed"])
app.include_router(filters.router, tags=["filters"])


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "x-internal-key",
        }
    }
    schema["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema

