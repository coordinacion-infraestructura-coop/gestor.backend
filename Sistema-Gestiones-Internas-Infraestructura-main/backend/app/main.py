from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import me, gestiones, catalogos, usuarios

app = FastAPI(title="Infra Gestión API - batracio palangana")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:8081", "http://localhost:8080", "http://127.0.0.1:8081", "https://labotech-analytics.github.io", "https://labotech-analytics.github.io/SistemaGestiones_infraestructura_front/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(me.router)
app.include_router(catalogos.router)
app.include_router(gestiones.router)
app.include_router(usuarios.router)
