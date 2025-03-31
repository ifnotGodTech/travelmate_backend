from django.contrib import admin
from core.applications.bookings.models import BookingHistory

@admin.register(BookingHistory)
class BookingHistoryAdmin(admin.ModelAdmin):
    """Admin interface for booking history entries"""
    
    list_display = ['id', 'booking', 'booking_type', 'status', 'changed_at', 'get_changed_by']
    list_filter = ['booking_type', 'status', 'changed_at']
    search_fields = ['booking__id', 'notes', 'changed_by__email']
    readonly_fields = ['booking', 'status', 'changed_at', 'notes', 'changed_by', 'booking_type', 'field_changes']
    
    def get_changed_by(self, obj):
        if obj.changed_by:
            return obj.changed_by.email
        return 'System'
    get_changed_by.short_description = 'Changed By'
    
    # Pretty-print JSON field
    def get_field_changes(self, obj):
        from django.utils.safestring import mark_safe
        import json
        if obj.field_changes:
            return mark_safe(f'<pre>{json.dumps(obj.field_changes, indent=2)}</pre>')
        return '-'
    get_field_changes.short_description = 'Field Changes'
    
    fieldsets = (
        (None, {
            'fields': ('booking', 'booking_type', 'status', 'changed_at', 'changed_by')
        }),
        ('Change Details', {
            'fields': ('notes', 'field_changes'),
            'classes': ('collapse',),
        }),
    )