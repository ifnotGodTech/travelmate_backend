from django.db import models
from django.utils import timezone


class AboutUs(models.Model):
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "About Us"

    def __str__(self):
        return f"About Us (Last updated: {self.updated_at.strftime('%Y-%m-%d')})"


class PrivacyPolicy(models.Model):
    content = models.TextField()
    last_updated = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Privacy Policies"

    def __str__(self):
        return f"Privacy Policy (Last updated: {self.last_updated.strftime('%Y-%m-%d')})"


class TermsOfUse(models.Model):
    content = models.TextField()
    last_updated = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Terms of Use"

    def __str__(self):
        return f"Terms of Use (Last updated: {self.last_updated.strftime('%Y-%m-%d')})"


class PartnerCategory(models.Model):
    CATEGORY_CHOICES = [
        ('airline', 'Airline Partners'),
        ('stay', 'Stay Partners'),
        ('car_rental', 'Car Rental Partners'),
    ]

    name = models.CharField(max_length=20, choices=CATEGORY_CHOICES, unique=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Partner Categories"

    def __str__(self):
        return self.get_name_display()


class Partner(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='partners/', null=True, blank=True)
    description = models.TextField()
    website = models.URLField(blank=True, null=True)
    category = models.ForeignKey(PartnerCategory, related_name='partners', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.category.get_name_display()}"
