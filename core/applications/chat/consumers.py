import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import ChatSession, ChatMessage, ChatAttachment

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    @database_sync_to_async
    def get_user_profile_data(self, user):
        """Fetch profile data for a user."""
        try:
            from core.applications.users.models import Profile
            profile = Profile.objects.get(user=user)
            return {
                'first_name': profile.first_name or '',
                'last_name': profile.last_name or '',
                'profile_pics': profile.get_profile_picture
            }
        except:
            return {
                'first_name': '',
                'last_name': '',
                'profile_pics': f'{settings.STATIC_URL}images/avatar.png'
            }

    @database_sync_to_async
    def check_session_access(self, session_id, user):
        try:
            session = ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            return False
        if user.is_staff or session.user == user:
            return True
        return False

    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            print(f"WebSocket connection rejected: User not authenticated")
            await self.close()
            return

        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'chat_{self.session_id}'

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

        # Join user's personal notification channel
        self.user_notification_channel = f'user_{self.user.id}'
        await self.channel_layer.group_add(
            self.user_notification_channel,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        if hasattr(self, 'user_notification_channel'):
            await self.channel_layer.group_discard(
                self.user_notification_channel,
                self.channel_name
            )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        attachments = text_data_json.get('attachments', [])

        chat_message = await self.save_message(
            session_id=self.session_id,
            user=self.user,
            message=message,
            attachments=attachments
        )

        # Fetch profile data
        profile_data = await self.get_user_profile_data(self.user)

        # Send message to room group with profile data
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': chat_message['id'],
                'message': message,
                'sender_id': self.user.id,
                'first_name': profile_data['first_name'],
                'last_name': profile_data['last_name'],
                'profile_pics': profile_data['profile_pics'],
                'is_staff': self.user.is_staff,
                'created_at': chat_message['created_at'].isoformat(),
                'attachments': chat_message.get('attachments', [])
            }
        )

        # Send notification to the other user
        session = await self.get_session(self.session_id)
        recipient = await self.get_session_recipient(session, self.user)
        if recipient:
            await self.channel_layer.group_send(
                f'user_{recipient.id}',
                {
                    'type': 'notification',
                    'message': {
                        'type': 'new_message',
                        'session_id': self.session_id,
                        'sender': {
                            'id': self.user.id,
                            'first_name': profile_data['first_name'],
                            'last_name': profile_data['last_name'],
                            'profile_pics': profile_data['profile_pics'],
                            'is_staff': self.user.is_staff
                        },
                        'preview': message[:100] + ('...' if len(message) > 100 else ''),
                        'has_attachments': bool(attachments)
                    }
                }
            )

    async def chat_message(self, event):
        # Send message to WebSocket with profile data
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': event['id'],
            'message': event['message'],
            'sender_id': event['sender_id'],
            'first_name': event['first_name'],
            'last_name': event['last_name'],
            'profile_pics': event['profile_pics'],
            'is_staff': event['is_staff'],
            'created_at': event['created_at'],
            'attachments': event.get('attachments', [])
        }))

    async def notification(self, event):
        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': event['message']
        }))

    async def session_update(self, event):
        # Send session update to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'session_update',
            'status': event['status']
        }))

    @database_sync_to_async
    def get_session(self, session_id):
        return ChatSession.objects.get(id=session_id)

    @database_sync_to_async
    def save_message(self, session_id, user, message, attachments=None):
        session = ChatSession.objects.get(id=session_id)

        status_changed = False
        if session.status == 'WAITING' and user.is_staff:
            session.status = 'ACTIVE'
            status_changed = True
        elif session.status == 'CLOSED':
            session.status = 'ACTIVE' if user.is_staff else 'WAITING'
            status_changed = True

        if status_changed:
            session.save()

        chat_message = ChatMessage.objects.create(
            session=session,
            sender=user,
            content=message
        )

        # Handle attachments
        attachment_data = []
        if attachments:
            for attachment in attachments:
                attachment_obj = ChatAttachment.objects.create(
                    message=chat_message,
                    file=attachment['file'],
                    file_name=attachment['name'],
                    file_type=attachment['type'],
                    file_size=attachment['size']
                )
                attachment_data.append({
                    'id': attachment_obj.id,
                    'file_name': attachment_obj.file_name,
                    'file_type': attachment_obj.file_type,
                    'file_size': attachment_obj.file_size,
                    'file_url': attachment_obj.file.url if attachment_obj.file else None
                })

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
            'created_at': chat_message.created_at,
            'attachments': attachment_data
        }

    @database_sync_to_async
    def get_session_recipient(self, session, current_user):
        """Get the recipient of the message based on the current user."""
        if current_user.is_staff:
            return session.user
        return None
