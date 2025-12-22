from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, users, natilleras, aportes, invitaciones, transacciones, prestamos

app = FastAPI(
    title="Natillera API",
    description="Sistema de ahorro colaborativo",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "https://natillera-app.vercel.app",  # Dominio de producción en Vercel
        "https://natillera-app.vercel.app",  # Agregar también sin www si es necesario
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Montar archivos estáticos - Comentado porque el frontend está separado
# app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Incluir routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(natilleras.router)
app.include_router(aportes.router)
app.include_router(invitaciones.router)
app.include_router(transacciones.router)
app.include_router(prestamos.router)

@app.get("/")
def read_root():
    return {"message": "Bienvenido a Natillera API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
