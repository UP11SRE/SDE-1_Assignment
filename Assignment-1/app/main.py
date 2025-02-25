from fastapi import FastAPI# app/main.py
from fastapi import FastAPI
from app import db, api
import uvicorn

app = FastAPI()

# Include the API routes from api.py
app.include_router(api.router)

@app.on_event("startup")
async def startup():
   
    await db.init_db_pool()
    await db.create_tables()

@app.on_event("shutdown")
async def shutdown():
   
    await db.close_db_pool()

if __name__ == "__main__":
    # Run the application with auto-reload for development.
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
