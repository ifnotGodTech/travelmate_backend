from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ChatSession, ChatMessage

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'first_name', 'email']

    def get_first_name(self, user):
        try:
            from core.applications.users.models import Profile
            profile = Profile.objects.get(user=user)
            return profile.first_name
        except:
            return ""


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_info = UserSerializer(source='sender', read_only=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'session', 'sender', 'sender_info', 'content', 'is_read', 'created_at']
        read_only_fields = ['is_read', 'created_at']

    def create(self, validated_data):
        # Mark previous messages as read when a new message is sent by the other party
        session = validated_data.get('session')
        sender = validated_data.get('sender')

        # If admin is sending a message, mark user's messages as read and vice versa
        if sender.is_staff:
            ChatMessage.objects.filter(session=session, sender__is_staff=False, is_read=False).update(is_read=True)
        else:
            ChatMessage.objects.filter(session=session, sender__is_staff=True, is_read=False).update(is_read=True)

        return super().create(validated_data)


class ChatSessionSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='user', read_only=True)
    admin_info = UserSerializer(source='assigned_admin', read_only=True)
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ['id', 'user', 'user_info', 'title', 'status', 'created_at',
                  'updated_at', 'assigned_admin', 'admin_info', 'unread_count', 'last_message']
        read_only_fields = ['created_at', 'updated_at']

    def get_unread_count(self, obj):
        # For users, count unread messages from admins
        # For admins, count unread messages from users
        request = self.context.get('request')
        if request and request.user:
            if request.user.is_staff:
                return obj.messages.filter(sender__is_staff=False, is_read=False).count()
            else:
                return obj.messages.filter(sender__is_staff=True, is_read=False).count()
        return 0

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return {
                'content': last_msg.content,
                'sender': last_msg.sender.first_name,
                'created_at': last_msg.created_at
            }
        return None


class ChatSessionDetailSerializer(ChatSessionSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta(ChatSessionSerializer.Meta):
        fields = ChatSessionSerializer.Meta.fields + ['messages']
