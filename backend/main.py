# backend/main.py - Fixed FastAPI Entry Point
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from app.main import app as api_app

# Create main FastAPI application
app = FastAPI(
    title="Smart Agriculture IoT API",
    description="Real-time agriculture monitoring system with sensor data and irrigation control",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:80",
        "https://*.onrender.com",
        "*"  # For development - restrict in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the API app
app.mount("/api", api_app)

# Health check endpoint
@app.get("/")
async def root():
    return {
        "name": "Smart Agriculture IoT API",
        "version": "1.0.0",
        "status": "running",
        "docs_url": "/docs",
        "api_url": "/api"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )