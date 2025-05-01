from rest_framework import serializers
from .models import Ticket, Message, EscalationLevel, TicketNotification
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
import os
User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name')

    @extend_schema_field(str)
    def get_first_name(self, user):
        try:
            from core.applications.users.models import Profile
            profile = Profile.objects.get(user=user)
            return profile.first_name
        except:
            return ""

    @extend_schema_field(str)
    def get_last_name(self, user):
        try:
            from core.applications.users.models import Profile
            profile = Profile.objects.get(user=user)
            return profile.last_name
        except:
            return ""

class MessageSerializer(serializers.ModelSerializer):
    sender = UserProfileSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'sender', 'content', 'attachment', 'timestamp')
        read_only_fields = ('id', 'timestamp')

class EscalationLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscalationLevel
        fields = ('id', 'name', 'email')

class TicketSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    escalation_level = EscalationLevelSerializer(read_only=True, allow_null=True)
    priority = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ('id', 'ticket_id', 'title', 'category', 'description', 'status',
                  'created_at', 'updated_at', 'user', 'messages',
                  'escalated', 'escalation_level', 'escalation_reason',
                  'escalation_response_time', 'priority', 'escalation_note')
        read_only_fields = ('id', 'ticket_id', 'created_at', 'updated_at', 'escalated')

    def get_priority(self, obj):
        mapping = {
            '1hr': 'High',
            '4hrs': 'Medium',
            '24hrs': 'Low',
        }
        return mapping.get(obj.escalation_response_time, None)

class TicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ('title', 'category', 'description')

class TicketEscalateSerializer(serializers.ModelSerializer):
    escalation_level = serializers.PrimaryKeyRelatedField(
        queryset=EscalationLevel.objects.all(),
        allow_null=False,
        required=True
    )
    escalation_reason = serializers.CharField(
        required=True,
        allow_null=False,
        allow_blank=False
    )
    escalation_response_time = serializers.ChoiceField(
        choices=Ticket.RESPONSE_TIME_CHOICES,
        required=True
    )
    escalation_note = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True
    )

    class Meta:
        model = Ticket
        fields = ('escalation_level', 'escalation_reason', 'escalation_response_time', 'escalation_note')

class MessageCreateSerializer(serializers.ModelSerializer):
    attachment = serializers.FileField(
        required=False,
        allow_null=True,
        max_length=10485760,  # 10MB limit
        allow_empty_file=True
    )

    class Meta:
        model = Message
        fields = ('content', 'attachment')

    def validate_attachment(self, value):
        if value:
            # Limit file size (10MB)
            if value.size > 10485760:
                raise serializers.ValidationError("File size too large. Max size is 10MB.")

            # Validate file extensions
            valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
            ext = os.path.splitext(value.name)[1].lower()
            if ext not in valid_extensions:
                raise serializers.ValidationError(
                    f"Unsupported file type. Allowed types: {', '.join(valid_extensions)}"
                )
        return value

class TicketStatPeriodSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    tickets = TicketSerializer(many=True)

class TicketEscalatedStatsSerializer(serializers.Serializer):
    unresolved_escalated = serializers.DictField(
        child=TicketStatPeriodSerializer(),
        required=True
    )

class TicketResolutionStatsSerializer(serializers.Serializer):
    resolved_tickets = serializers.DictField(
        child=TicketStatPeriodSerializer(),
        required=True
    )

class CategoryStatsSerializer(serializers.Serializer):
    category = serializers.CharField()
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    resolved = serializers.IntegerField()
    escalated = serializers.IntegerField()

class EscalationLevelStatsSerializer(serializers.Serializer):
    escalation_level__name = serializers.CharField()
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    resolved = serializers.IntegerField()


class TicketNotificationSerializer(serializers.ModelSerializer):
    ticket = TicketSerializer(read_only=True)

    class Meta:
        model = TicketNotification
        fields = ('id', 'user', 'ticket', 'notification_type', 'message', 'created_at', 'is_read')
        read_only_fields = ('id', 'user', 'ticket', 'notification_type', 'message', 'created_at')
