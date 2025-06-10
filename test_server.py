from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/test")
def read_root():
    return {"message": "Server is running!"}

if __name__ == "__main__":
    print("Starting test server...")
    print("Try accessing: http://localhost:8000/test")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info") 