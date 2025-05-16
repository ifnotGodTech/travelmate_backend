from django.db import models
from django.contrib.auth import get_user_model
import os

User = get_user_model()

def chat_attachment_path(instance, filename):
    # Generate path like: chat_attachments/session_id/message_id/filename
    return os.path.join('chat_attachments', str(instance.message.session.id), str(instance.message.id), filename)

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
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.username} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class ChatAttachment(models.Model):
    """Model for storing file attachments in chat messages"""
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=chat_attachment_path)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100)
    file_size = models.IntegerField()  # Size in bytes
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Attachment: {self.file_name} for message {self.message.id}"

    def save(self, *args, **kwargs):
        if not self.file_name and self.file:
            self.file_name = os.path.basename(self.file.name)
        if not self.file_type and self.file:
            self.file_type = os.path.splitext(self.file.name)[1].lower()
        if not self.file_size and self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
