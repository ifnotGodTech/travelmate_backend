from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class EscalationLevel(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()

    def __str__(self):
        return self.name

class EscalationReason(models.Model):
    reason = models.CharField(max_length=255)

    def __str__(self):
        return self.reason

class Ticket(models.Model):
    CATEGORY_CHOICES = [
        ('Flight', 'Flight'),
        ('Hotel', 'Hotel'),
        ('Car', 'Car'),
        ('Account', 'Account'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
    ]

    RESPONSE_TIME_CHOICES = [
        ('1hr', '1 Hour Emergency'),
        ('4hrs', '4 Hours Urgent'),
        ('24hrs', '24 Hours High Priority'),
    ]

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Escalation fields
    escalated = models.BooleanField(default=False)
    escalation_level = models.ForeignKey(EscalationLevel, on_delete=models.SET_NULL, null=True, blank=True)
    escalation_reason = models.ForeignKey(EscalationReason, on_delete=models.SET_NULL, null=True, blank=True)
    escalation_response_time = models.CharField(max_length=10, choices=RESPONSE_TIME_CHOICES, null=True, blank=True)
    escalation_note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Ticket #{self.id}: {self.title}"

class Message(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    attachment = models.FileField(upload_to='ticket_attachments/', null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message in Ticket #{self.ticket.id} by {self.sender.username}"
