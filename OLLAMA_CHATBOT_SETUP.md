# Ollama Chatbot Setup

This project already includes:

- Django chatbot API: `POST /api/chatbot/`
- Django chatbot WebSocket: `/ws/chatbot/`
- React Native/Expo chatbot screen
- Default model setting: `qwen2.5:0.5b`

## 1. Install Ollama

Download and install Ollama:

```powershell
winget install Ollama.Ollama
```

Or download it from:

```text
https://ollama.com/download
```

## 2. Verify Installation

```powershell
ollama --version
```

## 3. Download Qwen2.5 0.5B

```powershell
ollama pull qwen2.5:0.5b
```

## 4. Test The Model

```powershell
ollama run qwen2.5:0.5b
```

Then type a short question. Press `Ctrl+C` to exit.

## 5. Keep Ollama Running

Ollama must be running while Django uses the chatbot.

```powershell
ollama serve
```

If Ollama is already running in the background, this command may say the port is already in use. That is okay.

## 6. Connect Django To Ollama

For local development, put this in `enrollment_system/.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=qwen2.5:0.5b
OLLAMA_TIMEOUT=30
```

For a deployed backend, `localhost` means the deployed server, not your computer. Use one of these:

- Run Ollama on the same server as Django.
- Run Ollama on a separate reachable server and set `OLLAMA_BASE_URL` to that public/private URL.
- Keep chatbot testing local only.

## 7. Run Django

```powershell
python manage.py runserver 0.0.0.0:8000
```

## 8. Test Chat API

Login first and copy the JWT access token, then:

```powershell
$token = "PASTE_ACCESS_TOKEN_HERE"
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/chatbot/" `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Body '{"message":"What subjects are available?"}'
```

## Gmail Verification Codes

To receive Gmail verification codes, set these variables in your backend deploy environment:

```env
GMAIL_EMAIL=your_sender_gmail@gmail.com
GMAIL_APP_PASSWORD=your_16_character_google_app_password
DEFAULT_FROM_EMAIL=Enrollment <your_sender_gmail@gmail.com>
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
```

Use a Google App Password, not your normal Gmail password.

If the deployed server returns `[Errno 101] Network is unreachable`, the server cannot reach Gmail SMTP. In that case, the code is not lost: the email was never sent. You must either allow outbound SMTP on the host or use an email provider/API that the host can reach.
