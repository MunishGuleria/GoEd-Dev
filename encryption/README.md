# Encryption Module — Message Encryption API

A lightweight FastAPI service for password-based message encryption/decryption using Fernet symmetric encryption.

---

## How to Run

```bash
cd encryption
pip install -r requirements.txt
python main.py
# Runs on http://localhost:8003
```

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/generate-key` | Generate encryption key from password |
| `POST` | `/encrypt` | Encrypt a message with password |
| `POST` | `/decrypt` | Decrypt a message with password |

---

## How It Works

1. User provides a password (minimum 8 characters)
2. Password is converted to a 256-bit key using **PBKDF2-HMAC-SHA256** with a fixed salt from `.env`
3. The key is used for **Fernet** (AES-128-CBC) symmetric encryption
4. Same password always produces the same key (deterministic via fixed salt)

---

## Usage Examples

```bash
# Generate key
curl -X POST http://localhost:8003/generate-key \
  -H "Content-Type: application/json" \
  -d '{"password": "mypassword123"}'

# Encrypt
curl -X POST http://localhost:8003/encrypt \
  -H "Content-Type: application/json" \
  -d '{"password": "mypassword123", "text": "Hello, World!"}'

# Decrypt
curl -X POST http://localhost:8003/decrypt \
  -H "Content-Type: application/json" \
  -d '{"password": "mypassword123", "encrypted_text": "gAAAAA..."}'
```

---

## Environment Variables

```env
SALT=your-random-salt-string
```

> **Important:** The `SALT` must remain consistent. Changing it will invalidate all previously encrypted messages.
