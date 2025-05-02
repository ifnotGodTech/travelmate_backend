from django.contrib import admin
from .models import EscalationLevel, Ticket, Message, TicketNotification

@admin.register(EscalationLevel)
class EscalationLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')
    search_fields = ('name', 'email')

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_id', 'title', 'category', 'user', 'status', 'created_at', 'escalated', 'escalation_level')
    list_filter = ('status', 'category', 'escalated', 'escalation_level', 'escalation_response_time')
    search_fields = ('ticket_id', 'title', 'description', 'user__username', 'user__email', 'escalation_reason')
    raw_id_fields = ('user',)
    autocomplete_fields = ('escalation_level',)
    date_hierarchy = 'created_at'
    readonly_fields = ('ticket_id', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('ticket_id', 'title', 'category', 'description', 'user', 'status')
        }),
        ('Escalation Details', {
            'fields': ('escalated', 'escalation_level', 'escalation_reason', 'escalation_response_time', 'escalation_note')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'sender', 'timestamp', 'has_attachment')
    list_filter = ('timestamp', 'ticket__category')
    search_fields = ('ticket__ticket_id', 'ticket__title', 'sender__username', 'content')
    raw_id_fields = ('ticket', 'sender')
    readonly_fields = ('timestamp',)

    @admin.display(
        description='Has Attachment',
        boolean=True,
    )
    def has_attachment(self, obj):
        return bool(obj.attachment)

@admin.register(TicketNotification)
class TicketNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'ticket', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'user__email', 'ticket__ticket_id', 'ticket__title', 'message')
    raw_id_fields = ('user', 'ticket')
    readonly_fields = ('created_at',)
    actions = ['mark_as_read', 'mark_as_unread']

    @admin.action(
        description="Mark selected notifications as read"
    )
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(
        description="Mark selected notifications as unread"
    )
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
