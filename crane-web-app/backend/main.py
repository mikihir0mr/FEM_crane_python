from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os
import secrets
from crane_calc import calculate_crane

app = FastAPI()
security = HTTPBasic()

# Environment variables for Basic Auth
AUTH_USER = os.getenv("AUTH_USER", "admin")
AUTH_PASS = os.getenv("AUTH_PASS", "password")

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, AUTH_USER)
    correct_password = secrets.compare_digest(credentials.password, AUTH_PASS)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CraneParams(BaseModel):
    pipe_od: float = 48.6
    t_wall: float = 2.4
    base_len: float = 900.0
    base_wid: float = 600.0
    arm_pivot_height: float = 1800.0
    tripod_attach_height: float = 1000.0
    brace_mast_height: float = 800.0
    arm_len: float = 1000.0
    arm_angle: float = 180.0
    mass_tip: float = 50.0

@app.post("/calculate", dependencies=[Depends(get_current_username)])
async def calculate(params: CraneParams):
    try:
        results = calculate_crane(params.dict())
        return results
    except Exception as e:
        return {"error": str(e)}

# Serve Static Files
frontend_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{full_path:path}", dependencies=[Depends(get_current_username)])
    async def serve_frontend(full_path: str):
        # If API path, let it pass (though /calculate is POST, so this GET won't catch it)
        # But we need to be careful not to shadow API routes if we had GET APIs.
        # Here we only have POST /calculate.
        
        # Check if file exists in dist
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Otherwise return index.html (SPA routing)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
