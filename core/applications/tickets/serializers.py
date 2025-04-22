from rest_framework import serializers
from .models import Ticket, Message, EscalationLevel, EscalationReason
from django.contrib.auth import get_user_model
from django.utils import timezone
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
        fields = ('id', 'ticket_id', 'title', 'category', 'description', 'status',
                  'created_at', 'updated_at', 'user', 'messages',
                  'escalated', 'escalation_level', 'escalation_reason',
                  'escalation_response_time', 'escalation_note')
        read_only_fields = ('id', 'ticket_id', 'created_at', 'updated_at', 'escalated')

class TicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ('title', 'category', 'description')

        # def create(self, validated_data):
        #     # Get the current year
        #     year = timezone.now().year

        #     # Get the last ticket for the current year
        #     last_ticket = Ticket.objects.filter(
        #         ticket_id__startswith=f'TKT{year}'
        #     ).order_by('ticket_id').last()

        #     if last_ticket:
        #         last_number = int(last_ticket.ticket_id.split('-')[-1])
        #         new_number = last_number + 1
        #     else:
        #         new_number = 1

        #     # Generate the new ticket ID
        #     ticket_id = f'TKT{year}-{new_number:03d}'

        #     # Create the ticket with the generated ID
        #     ticket = Ticket.objects.create(
        #         ticket_id=ticket_id,
        #         **validated_data
        #     )

        #     return ticket



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
