import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import ChatSession, ChatMessage
import base64
from django.core.files.base import ContentFile
import uuid

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

        # Superuser can access any session
        if user.is_superuser:
            return True

        # User can only access their own sessions
        if session.user == user:
            return True

        # Admin can only access if they are assigned or if no admin is assigned
        if user.is_staff:
            return session.assigned_admin is None or session.assigned_admin == user

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

    @database_sync_to_async
    def get_assigned_admin_data(self, session):
        """Get assigned admin data in a sync context"""
        if not session.assigned_admin:
            return None
        try:
            from core.applications.users.models import Profile
            profile = Profile.objects.get(user=session.assigned_admin)
            return {
                'id': session.assigned_admin.id,
                'first_name': profile.first_name or '',
                'last_name': profile.last_name or '',
                'profile_pics': profile.get_profile_picture
            }
        except Profile.DoesNotExist:
            return {
                'id': session.assigned_admin.id,
                'first_name': '',
                'last_name': '',
                'profile_pics': f'{settings.STATIC_URL}images/avatar.png'
            }

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json['message']
            attachment = text_data_json.get('attachment')

            print(f"Received message: {message}")
            print(f"Attachment: {attachment}")

            chat_message = await self.save_message(
                session_id=self.session_id,
                user=self.user,
                message=message,
                attachment=attachment
            )

            print(f"Saved message: {chat_message}")

            # Fetch profile data
            profile_data = await self.get_user_profile_data(self.user)

            # Get assigned admin info
            session = await self.get_session(self.session_id)
            assigned_admin_data = await self.get_assigned_admin_data(session)

            # Send message to room group with profile data
            message_data = {
                'type': 'chat_message',
                'id': chat_message['id'],
                'message': message,
                'sender_id': self.user.id,
                'first_name': profile_data['first_name'],
                'last_name': profile_data['last_name'],
                'profile_pics': profile_data['profile_pics'],
                'is_staff': self.user.is_staff,
                'created_at': chat_message['created_at'].isoformat(),
                'attachment': chat_message.get('attachment'),
                'assigned_admin': assigned_admin_data
            }

            print(f"Sending message data: {message_data}")

            await self.channel_layer.group_send(
                self.room_group_name,
                message_data
            )

            # Send notification to the other user
            recipient = await self.get_session_recipient(session, self.user)
            if recipient:
                notification_data = {
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
                        'has_attachment': bool(attachment)
                    }
                }
                print(f"Sending notification data: {notification_data}")
                await self.channel_layer.group_send(
                    f'user_{recipient.id}',
                    notification_data
                )

        except PermissionError as e:
            print(f"Permission error: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
        except Exception as e:
            print(f"Error in receive: {str(e)}")
            import traceback
            print(traceback.format_exc())
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'An error occurred while sending the message: {str(e)}'
            }))

    async def chat_message(self, event):
        # Send message to WebSocket with profile data
        await self.send(text_data=json.dumps(event))

    async def notification(self, event):
        # Send notification to WebSocket
        await self.send(text_data=json.dumps(event))

    async def session_update(self, event):
        # Send session update to WebSocket
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_session(self, session_id):
        return ChatSession.objects.get(id=session_id)

    @database_sync_to_async
    def save_message(self, session_id, user, message, attachment=None):
        session = ChatSession.objects.get(id=session_id)

        # Check if user is admin
        is_admin = user.is_staff

        # If admin is sending message
        if is_admin:
            # If no admin is assigned, assign this admin
            if not session.assigned_admin:
                session.assigned_admin = user
                session.status = 'ACTIVE'
                session.save()
            # If another admin is assigned, prevent sending
            elif session.assigned_admin != user:
                raise PermissionError("This chat is already assigned to another admin")

        # If user is sending message and session is closed, reopen it
        elif session.status == 'CLOSED':
            session.status = 'WAITING'
            session.save()

        # Create the message first without attachment
        chat_message = ChatMessage.objects.create(
            session=session,
            sender=user,
            content=message
        )

        # Handle attachment if provided
        if attachment:
            try:
                # Extract the base64 data
                format, filedata = attachment.split(';base64,')
                ext = format.split('/')[-1]

                # Generate a unique filename
                filename = f"{uuid.uuid4()}.{ext}"

                # Decode and save the file
                data = ContentFile(base64.b64decode(filedata), name=filename)
                chat_message.attachment.save(filename, data, save=True)
            except Exception as e:
                print(f"Error saving attachment: {str(e)}")
                # If there's an error with the attachment, we'll still save the message
                pass

        # Update read status
        if user.is_staff:
            ChatMessage.objects.filter(session=session, sender__is_staff=False, is_read=False).update(is_read=True)
        else:
            ChatMessage.objects.filter(session=session, sender__is_staff=True, is_read=False).update(is_read=True)

        # Return message data with safe attachment URL handling
        attachment_url = None
        if chat_message.attachment:
            try:
                attachment_url = chat_message.attachment.url
            except Exception as e:
                print(f"Error getting attachment URL: {str(e)}")

        return {
            'id': chat_message.id,
            'created_at': chat_message.created_at,
            'attachment': attachment_url
        }

    @database_sync_to_async
    def get_session_recipient(self, session, current_user):
        """Get the other user in the session (recipient of the message)"""
        if current_user == session.user:
            return session.assigned_admin
        return session.user
