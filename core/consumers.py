import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .views import build_chatbot_response


class ChatbotConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        await self.accept()
        await self.send_json({
            "type": "connected",
            "message": "Chatbot WebSocket connected.",
        })

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON payload.")
            return

        message = payload.get("message", "")

        if not isinstance(message, str):
            await self.send_error("Message must be text.")
            return

        message = message.strip()

        if not message:
            await self.send_error("Message is required.")
            return

        if len(message) > 500:
            await self.send_error("Message must be 500 characters or fewer.")
            return

        await self.send_json({"type": "thinking"})
        reply = await database_sync_to_async(build_chatbot_response)(
            self.scope["user"],
            message,
        )
        await self.send_json({
            "type": "reply",
            "reply": reply,
        })

    async def send_error(self, message):
        await self.send_json({
            "type": "error",
            "error": message,
        })

    async def send_json(self, payload):
        await self.send(text_data=json.dumps(payload))
