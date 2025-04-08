
from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import FAQCategory, FAQ
from django.conf import settings
from allauth.account.decorators import secure_admin_login
from django.utils.translation import gettext_lazy as _

User = get_user_model()

# Only apply this if the setting is True
if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]



@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'icon', 'order')
    list_editable = ('order',)
    list_filter = ('name',)
    search_fields = ('name', 'description')
    ordering = ('order', 'name')


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'is_active', 'order', 'views', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('question', 'answer')
    list_editable = ('is_active', 'order')
    ordering = ('category__order', 'order', 'question')
    raw_id_fields = ('created_by',)
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('category', 'question', 'answer', 'is_active', 'order')
        }),
        ('Statistics', {
            'fields': ('views', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('views', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # If this is a new object (not an update)
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
