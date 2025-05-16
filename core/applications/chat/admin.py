from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import ChatSession, ChatMessage, ChatAttachment
from django.conf import settings
from allauth.account.decorators import secure_admin_login
from django.utils.translation import gettext_lazy as _


# Only apply this if the setting is True
if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]

class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('sender', 'content', 'is_read', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'assigned_admin', 'status', 'created_at', 'updated_at', 'get_message_count')
    list_filter = ('status', 'created_at', 'assigned_admin')
    search_fields = ('title', 'user__username', 'user__email', 'assigned_admin__username', 'assigned_admin__email')
    readonly_fields = ('created_at', 'updated_at', 'get_message_count')
    raw_id_fields = ('user', 'assigned_admin')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    @admin.display(
        description='Messages'
    )
    def get_message_count(self, obj):
        count = obj.messages.count()
        return format_html('<span style="color: {};">{}</span>',
                         'green' if count > 0 else 'red',
                         count)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Non-superusers can only see sessions they are assigned to
            return qs.filter(assigned_admin=request.user)
        return qs

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        # Only superusers or assigned admins can modify the session
        return request.user.is_superuser or obj.assigned_admin == request.user

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'sender', 'is_staff_sender', 'content_preview', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at', 'sender__is_staff')
    search_fields = ('content', 'sender__username', 'sender__email', 'session__title')
    readonly_fields = ('created_at', 'get_attachments')
    raw_id_fields = ('session', 'sender')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    @admin.display(
        description='Content'
    )
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content

    @admin.display(
        description='Staff',
        boolean=True,
    )
    def is_staff_sender(self, obj):
        return obj.sender.is_staff

    @admin.display(
        description='Attachments'
    )
    def get_attachments(self, obj):
        attachments = obj.attachments.all()
        if not attachments:
            return "No attachments"

        html = '<ul>'
        for attachment in attachments:
            html += f'<li><a href="{attachment.file.url}" target="_blank">{attachment.file_name}</a> ({attachment.file_type}, {attachment.file_size} bytes)</li>'
        html += '</ul>'
        return format_html(html)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Non-superusers can only see messages from sessions they are assigned to
            return qs.filter(session__assigned_admin=request.user)
        return qs

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        # Only superusers or assigned admins can modify messages
        return request.user.is_superuser or obj.session.assigned_admin == request.user

@admin.register(ChatAttachment)
class ChatAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'file_name', 'file_type', 'file_size', 'created_at')
    list_filter = ('file_type', 'created_at')
    search_fields = ('file_name', 'message__content', 'message__sender__username')
    readonly_fields = ('created_at', 'file_preview')
    raw_id_fields = ('message',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    @admin.display(
        description='Preview'
    )
    def file_preview(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">View File</a>', obj.file.url)
        return "No file"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Non-superusers can only see attachments from sessions they are assigned to
            return qs.filter(message__session__assigned_admin=request.user)
        return qs

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        # Only superusers or assigned admins can modify attachments
        return request.user.is_superuser or obj.message.session.assigned_admin == request.user
