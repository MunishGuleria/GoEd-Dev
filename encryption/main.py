import os
import base64
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv

# 1. Load environment variables
load_dotenv()

# 2. Get Salt from .env
SALT_ENV = os.getenv("SALT")
if not SALT_ENV:
    raise RuntimeError("SALT not found in .env file. Please create one.")
SALT = SALT_ENV.encode()

app = FastAPI(title="Message Encryption API")

# --- Models ---
class Message(BaseModel):
    password: str
    text: str

class EncryptedMessage(BaseModel):
    password: str
    encrypted_text: str

class PasswordRequest(BaseModel):
    password: str

# --- Core Logic ---
def password_to_key(password: str) -> bytes:
    """Convert password to encryption key using the fixed salt from .env"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=100000,
        backend=default_backend()
    )
    # Return URL-safe base64-encoded key
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

# --- Endpoints ---
@app.get("/")
def home():
    return {"status": "Message Encryption API Running"}

@app.post("/generate-key")
def generate_key(request: PasswordRequest):
    """Generate encryption key from user password (min 8 characters)"""
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    try:
        key = password_to_key(request.password)
        return {
            "key": key.decode(),
            "message": "Save this key securely. You'll need the same password to encrypt/decrypt."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/encrypt")
def encrypt_message(message: Message):
    """Encrypt a message with password"""
    try:
        key = password_to_key(message.password)
        cipher = Fernet(key)
        encrypted = cipher.encrypt(message.text.encode()).decode()
        return {"encrypted_text": encrypted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/decrypt")
def decrypt_message(message: EncryptedMessage):
    """Decrypt a message with password"""
    try:
        key = password_to_key(message.password)
        cipher = Fernet(key)
        decrypted = cipher.decrypt(message.encrypted_text.encode()).decode()
        return {"text": decrypted}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Wrong password or invalid message")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)