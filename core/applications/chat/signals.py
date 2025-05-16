from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
from .models import ChatMessage, ChatSession
from core.applications.users.models import Profile

@receiver(post_save, sender=ChatMessage)
def notify_new_message(sender, instance, created, **kwargs):
    """Send notification when a new message is created"""
    if created:
        channel_layer = get_channel_layer()

        # Fetch profile data
        try:
            profile = Profile.objects.get(user=instance.sender)
            profile_data = {
                'first_name': profile.first_name or '',
                'last_name': profile.last_name or '',
                'profile_pics': profile.get_profile_picture
            }
        except Profile.DoesNotExist:
            profile_data = {
                'first_name': '',
                'last_name': '',
                'profile_pics': f'{settings.STATIC_URL}images/avatar.png'
            }

        # Notify the chat room
        async_to_sync(channel_layer.group_send)(
            f'chat_{instance.session.id}',
            {
                'type': 'chat_message',
                'id': instance.id,
                'message': instance.content,
                'sender_id': instance.sender.id,
                'first_name': profile_data['first_name'],
                'last_name': profile_data['last_name'],
                'profile_pics': profile_data['profile_pics'],
                'is_staff': instance.sender.is_staff,
                'created_at': instance.created_at.isoformat(),
            }
        )

@receiver(post_save, sender=ChatSession)
def notify_session_update(sender, instance, **kwargs):
    """Send notification when a session status changes"""
    channel_layer = get_channel_layer()
    session_data = {
        'type': 'session_update',
        'status': instance.status,
    }

    # Notify the chat room
    async_to_sync(channel_layer.group_send)(
        f'chat_{instance.id}',
        session_data
    )
