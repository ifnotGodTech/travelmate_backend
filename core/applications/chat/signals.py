from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import ChatMessage, ChatSession

@receiver(post_save, sender=ChatMessage)
def notify_new_message(sender, instance, created, **kwargs):
    """Send notification when a new message is created"""
    if created:
        channel_layer = get_channel_layer()
        # Notify the chat room
        async_to_sync(channel_layer.group_send)(
            f'chat_{instance.session.id}',
            {
                'type': 'chat_message',
                'id': instance.id,
                'message': instance.content,
                'sender_id': instance.sender.id,
                'sender_username': instance.sender.username,
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

    if instance.assigned_admin:
        session_data['assigned_admin'] = {
            'id': instance.assigned_admin.id,
            'username': instance.assigned_admin.username
        }

    # Notify the chat room
    async_to_sync(channel_layer.group_send)(
        f'chat_{instance.id}',
        session_data
    )
