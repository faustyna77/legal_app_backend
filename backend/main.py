from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import search, judgments, embed
from app.routers import filters

app = FastAPI(title="Legal RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-app.vercel.app",
        "http://localhost:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, tags=["search"])
app.include_router(judgments.router, prefix="/judgments", tags=["judgments"])
app.include_router(embed.router, prefix="/embed", tags=["embed"])
app.include_router(filters.router, tags=["filters"])


@app.get("/health")
async def health():
    return {"status": "ok"}
