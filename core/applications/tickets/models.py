from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


User = get_user_model()


class EscalationLevel(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()

    def __str__(self):
        return self.name

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

    ticket_id = models.CharField(max_length=12, unique=True, editable=False)
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
    escalation_reason = models.TextField(blank=True, null=True)
    escalation_response_time = models.CharField(max_length=10, choices=RESPONSE_TIME_CHOICES, null=True, blank=True)
    escalation_note = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            # Get the current year
            year = timezone.now().year

            # Get the last ticket for the current year
            last_ticket = Ticket.objects.filter(
                ticket_id__startswith=f'TKT{year}'
            ).order_by('ticket_id').last()

            if last_ticket:
                # Extract the number from the last ticket ID and increment it
                last_number = int(last_ticket.ticket_id.split('-')[-1])
                new_number = last_number + 1
            else:
                # If no tickets exist for this year, start with 1
                new_number = 1

            # Generate the new ticket ID
            self.ticket_id = f'TKT{year}-{new_number:03d}'

        super().save(*args, **kwargs)

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


class TicketNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('new_message', 'New Message'),
        ('ticket_resolved', 'Ticket Resolved'),
        ('ticket_escalated', 'Ticket Escalated'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ticket_notifications')
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.email}: {self.notification_type}"


@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    if created:
        # Create notification for ticket owner if message is from staff
        if instance.sender.is_staff and instance.ticket.user != instance.sender:
            TicketNotification.objects.create(
                user=instance.ticket.user,
                ticket=instance.ticket,
                notification_type='new_message',
                message=f'New message from support on ticket: {instance.ticket.title}'
            )
        # Create notification for staff if message is from user
        elif not instance.sender.is_staff:
            for admin in User.objects.filter(is_staff=True):
                TicketNotification.objects.create(
                    user=admin,
                    ticket=instance.ticket,
                    notification_type='new_message',
                    message=f'New message from {instance.sender.email} on ticket: {instance.ticket.title}'
                )

@receiver(post_save, sender=Ticket)
def create_ticket_status_notification(sender, instance, **kwargs):
    if kwargs.get('update_fields'):
        # Ticket resolved notification
        if 'status' in kwargs['update_fields'] and instance.status == 'resolved':
            TicketNotification.objects.create(
                user=instance.user,
                ticket=instance,
                notification_type='ticket_resolved',
                message=f'Your ticket "{instance.title}" has been resolved'
            )

        # Ticket escalated notification
        if 'escalated' in kwargs['update_fields'] and instance.escalated:
            # Notify user
            TicketNotification.objects.create(
                user=instance.user,
                ticket=instance,
                notification_type='ticket_escalated',
                message=f'Your ticket "{instance.title}" has been escalated to {instance.escalation_level.name}'
            )
            # Notify staff
            for admin in User.objects.filter(is_staff=True):
                TicketNotification.objects.create(
                    user=admin,
                    ticket=instance,
                    notification_type='ticket_escalated',
                    message=f'Ticket "{instance.title}" has been escalated to {instance.escalation_level.name}'
                )
