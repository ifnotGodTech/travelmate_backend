from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import ChatSession, ChatMessage
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
    list_display = ('id', 'title', 'status', 'message_count', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'user__first_name', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ChatMessageInline]
    actions = ['mark_as_closed', 'mark_as_open']

    # def user_link(self, obj):
    #     url = reverse("admin:auth_user_change", args=[obj.user.id])
    #     return format_html('<a href="{}">{}</a>', url, obj.user.username)
    # user_link.short_description = 'User'

    # def assigned_admin_link(self, obj):
    #     if obj.assigned_admin:
    #         url = reverse("admin:auth_user_change", args=[obj.assigned_admin.id])
    #         return format_html('<a href="{}">{}</a>', url, obj.assigned_admin.username)
    #     return '-'
    # assigned_admin_link.short_description = 'Assigned Admin'

    @admin.display(
        description='Messages'
    )
    def message_count(self, obj):
        return obj.messages.count()

    @admin.action(
        description="Mark selected sessions as closed"
    )
    def mark_as_closed(self, request, queryset):
        queryset.update(status='CLOSED')

    @admin.action(
        description="Mark selected sessions as open"
    )
    def mark_as_open(self, request, queryset):
        queryset.update(status='OPEN')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'short_content', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at', 'sender__is_staff')
    search_fields = ('content', 'sender__first_name', 'session__title')
    readonly_fields = ('created_at',)

    # def session_link(self, obj):
    #     url = reverse("admin:core_applications_chat_chatsession_change", args=[obj.session.id])
    #     return format_html('<a href="{}">{}</a>', url, f"Session #{obj.session.id}: {obj.session.title}")
    # session_link.short_description = 'Session'

    @admin.display(
        description='Content'
    )
    def short_content(self, obj):
        return obj.content if len(obj.content) < 50 else f"{obj.content[:47]}..."

    def has_change_permission(self, request, obj=None):
        # Messages shouldn't be editable to maintain conversation integrity
        return False
