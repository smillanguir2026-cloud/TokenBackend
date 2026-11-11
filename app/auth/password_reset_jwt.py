import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, BackgroundTasks, status, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
import jwt

app = FastAPI()

SECRET_KEY = os.getenv("SECRET_KEY", "cambiar_esto_por_una_clave_larga_y_aleatoria")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

fake_users_db = {
    "usuario@ejemplo.com": {
        "id": 1,
        "email": "usuario@ejemplo.com",
        "hashed_password": pwd_context.hash("clave_antigua_123")
    }
}

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    user_id: int
    token: str
    new_password: str = Field(..., min_length=8)

def send_reset_email(email: str, link: str):
    print(f"Para: {email} | Enlace: {link}")

@app.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(data: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    user = fake_users_db.get(data.email)
    generic_response = {"message": "Si el correo existe, recibirás un enlace de recuperación."}

    if not user:
        return generic_response

    dynamic_secret = SECRET_KEY + user["hashed_password"]
    payload = {
        "sub": str(user["id"]),
        "type": "password_reset",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
    }
    token = jwt.encode(payload, dynamic_secret, algorithm=ALGORITHM)
    reset_link = f"{BASE_URL}/reset-password?user_id={user['id']}&token={token}"

    background_tasks.add_task(send_reset_email, user["email"], reset_link)
    return generic_response

@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_form(user_id: int = Query(...), token: str = Query(...)):
    html = Path("public/reset_password.html").read_text(encoding="utf-8")
    return html

@app.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(data: ResetPasswordRequest):
    user = next((u for u in fake_users_db.values() if u["id"] == data.user_id), None)
    if not user:
        raise HTTPException(status_code=400, detail="Solicitud inválida.")

    dynamic_secret = SECRET_KEY + user["hashed_password"]
    try:
        payload = jwt.decode(data.token, dynamic_secret, algorithms=[ALGORITHM])
        if payload.get("type") != "password_reset" or payload.get("sub") != str(user["id"]):
            raise HTTPException(status_code=400, detail="Token inválido para esta operación.")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="El enlace ha expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="El enlace es inválido o ya fue utilizado.")

    user["hashed_password"] = pwd_context.hash(data.new_password)
    return {"message": "Contraseña actualizada exitosamente."}
