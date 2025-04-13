from django.contrib import admin
from .models import AboutUs, PrivacyPolicy, TermsOfUse, PartnerCategory, Partner
from django.conf import settings
from allauth.account.decorators import secure_admin_login
from django.utils.translation import gettext_lazy as _


# Only apply this if the setting is True
if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]


@admin.register(AboutUs)
class AboutUsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('content',)


@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'last_updated', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('content',)
    fieldsets = (
        (None, {
            'fields': ('content', 'last_updated')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TermsOfUse)
class TermsOfUseAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'last_updated', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('content',)
    fieldsets = (
        (None, {
            'fields': ('content', 'last_updated')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PartnerCategory)
class PartnerCategoryAdmin(admin.ModelAdmin):
    list_display = ('get_name_display', 'description', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('name', 'description')


class PartnerInline(admin.TabularInline):
    model = Partner
    extra = 1
    fields = ('name', 'logo', 'website', 'is_active')


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'website', 'is_active', 'updated_at')
    list_filter = ('category', 'is_active')
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('name', 'description', 'website')
    fieldsets = (
        (None, {
            'fields': ('name', 'category', 'logo', 'description', 'website', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
