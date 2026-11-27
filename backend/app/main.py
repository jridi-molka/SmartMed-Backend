
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, users, slots, appointments, queue, doctors
from app.api.routes import agenda


app = FastAPI(title="SmartMed API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(slots.router)
app.include_router(appointments.router) 
app.include_router(agenda.router)
app.include_router(queue.router)
app.include_router(doctors.router)

@app.get("/")
def accueil():
    return {"message": "Bienvenue dans SmartMed !"}