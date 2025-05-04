import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatSession, ChatMessage

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    @database_sync_to_async
    def check_session_access(self, session_id, user):
        return True  # Allow access for everyone

    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            # Reject the connection
            print(f"WebSocket connection rejected: User not authenticated")
            await self.close()
            return

        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'chat_{self.session_id}'

        # Check if user has access to this session
        has_access = await self.check_session_access(self.session_id, self.user)
        if not has_access:
            print(f"WebSocket connection rejected: User {self.user.username} doesn't have access to session {self.session_id}")
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Save message to database
        chat_message = await self.save_message(
            session_id=self.session_id,
            user=self.user,
            message=message
        )

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': chat_message['id'],
                'message': message,
                'sender_id': self.user.id,
                'sender_username': self.user.username,
                'is_staff': self.user.is_staff,
                'created_at': chat_message['created_at'].isoformat(),
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': event['id'],
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_username': event['sender_username'],
            'is_staff': event['is_staff'],
            'created_at': event['created_at'],
        }))



    # Receive notification about session updates
    async def session_update(self, event):
        # Send session update to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'session_update',
            'status': event['status'],
            'assigned_admin': event.get('assigned_admin'),
        }))

    @database_sync_to_async
    def check_session_access(self, session_id, user):
        try:
            session = ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            return False  # Session does not exist

        # Check if the user is allowed to access the session
        if user.is_staff or session.user == user:  # Example: admin or session owner
            return True
        return False

    @database_sync_to_async
    def save_message(self, session_id, user, message):
        session = ChatSession.objects.get(id=session_id)

        # Update session status if needed
        status_changed = False
        if session.status == 'WAITING' and user.is_staff:
            session.status = 'ACTIVE'
            session.assigned_admin = user
            status_changed = True
        elif session.status == 'CLOSED':
            session.status = 'ACTIVE' if user.is_staff else 'WAITING'
            status_changed = True

        if status_changed:
            session.save()

        # Create and save the message
        chat_message = ChatMessage.objects.create(
            session=session,
            sender=user,
            content=message
        )

        # Mark relevant messages as read
        if user.is_staff:
            ChatMessage.objects.filter(
                session=session,
                sender__is_staff=False,
                is_read=False
            ).update(is_read=True)
        else:
            ChatMessage.objects.filter(
                session=session,
                sender__is_staff=True,
                is_read=False
            ).update(is_read=True)

        return {
            'id': chat_message.id,
            'created_at': chat_message.created_at
        }
