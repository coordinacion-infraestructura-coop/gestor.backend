from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import me, gestiones, catalogos, usuarios, informe_cooperativas

app = FastAPI(title="Infra Gestión API - update 3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501",
        "http://localhost:5173",
        "http://localhost:8081",
        "http://localhost:8080",
        "http://127.0.0.1:8081",
        "https://labotech-analytics.github.io",
        "https://labotech-analytics.github.io/SistemaGestiones_infraestructura_front/",
        "https://coordinacion-infraestructura-coop.github.io/gestor/",
        "https://gestorcooperativo.web.app",
        "https://gestorcooperativo.firebaseapp.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(me.router)
app.include_router(catalogos.router)
app.include_router(gestiones.router)
app.include_router(gestiones.public_router)
app.include_router(usuarios.router)
app.include_router(informe_cooperativas.router)

# Rutas con prefijo para consumo vía API Gateway (APPEND_PATH_TO_ADDRESS)
# El Vanilla JS legacy sigue usando las rutas sin prefijo de arriba.
app.include_router(me.router, prefix="/api/v1/privada")
app.include_router(gestiones.router, prefix="/api/v1/privada")
app.include_router(gestiones.public_router, prefix="/api/v1/privada")
app.include_router(catalogos.router, prefix="/api/v1/privada")
app.include_router(usuarios.router, prefix="/api/v1/privada")
