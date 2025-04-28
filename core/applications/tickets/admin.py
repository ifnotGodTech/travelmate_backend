from django.contrib import admin
from .models import EscalationLevel, Ticket, Message

@admin.register(EscalationLevel)
class EscalationLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')
    search_fields = ('name', 'email')

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'user', 'status', 'created_at', 'escalated')
    list_filter = ('status', 'category', 'escalated', 'escalation_level', 'escalation_response_time')
    search_fields = ('title', 'description', 'user__username', 'user__email', 'escalation_reason')
    raw_id_fields = ('user',)
    autocomplete_fields = ('escalation_level',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'sender', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('ticket__title', 'sender__username', 'content')
    raw_id_fields = ('ticket', 'sender')
