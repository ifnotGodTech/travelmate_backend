from rest_framework import serializers
from .models import Ticket, Message, EscalationLevel, EscalationReason
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
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

class EscalationReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscalationReason
        fields = ('id', 'reason')

class TicketSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    escalation_level = EscalationLevelSerializer(read_only=True, allow_null=True)
    escalation_reason = EscalationReasonSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Ticket
        fields = ('id', 'title', 'category', 'description', 'status',
                  'created_at', 'updated_at', 'user', 'messages',
                  'escalated', 'escalation_level', 'escalation_reason',
                  'escalation_response_time', 'escalation_note')
        read_only_fields = ('id', 'created_at', 'updated_at', 'escalated')

class TicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ('title', 'category', 'description')

class TicketEscalateSerializer(serializers.ModelSerializer):
    escalation_level = serializers.PrimaryKeyRelatedField(
        queryset=EscalationLevel.objects.all(),
        allow_null=False,  # Changed from True to False
        required=True      # Explicitly require this field
    )
    escalation_reason = serializers.PrimaryKeyRelatedField(
        queryset=EscalationReason.objects.all(),
        allow_null=False,  # Changed from True to False
        required=True      # Explicitly require this field
    )

    class Meta:
        model = Ticket
        fields = ('escalation_level', 'escalation_reason', 'escalation_response_time', 'escalation_note')
class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ('content', 'attachment')
