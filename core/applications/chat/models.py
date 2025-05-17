from django.db import models
from django.contrib.auth import get_user_model
import os

User = get_user_model()

def chat_attachment_path(instance, filename):
    # Generate path like: chat_attachments/session_id/message_id/filename
    return os.path.join('chat_attachments', str(instance.session.id), str(instance.id), filename)

class ChatSession(models.Model):
    """Model for storing chat sessions between users and support staff"""
    STATUS_CHOICES = (
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
        ('WAITING', 'Waiting for Support'),
        ('ACTIVE', 'Active with Support'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    assigned_admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_chats')
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Chat {self.id}: {self.title} ({self.status})"


class ChatMessage(models.Model):
    """Model for storing individual chat messages"""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    attachment = models.FileField(upload_to=chat_attachment_path, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.username} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"
