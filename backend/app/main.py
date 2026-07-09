from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import auth, interactions, chat, dashboard, conversations, ws
from app.database.connection import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-First CRM", version="1.0.0", description="AI-Powered CRM for Healthcare Professionals")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(interactions.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(dashboard.router)
app.include_router(ws.router)

@app.get("/")
def root():
    return {"message": "AI-First CRM API", "version": "1.0.0", "status": "running"}
