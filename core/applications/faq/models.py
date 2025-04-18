from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class FAQCategory(models.Model):
    CATEGORY_CHOICES = [
        ('FLIGHTS', 'Flights'),
        ('STAYS', 'Stays'),
        ('CAR_RENTALS', 'Car Rentals'),
        ('ACCOUNT', 'Account'),
    ]

    name = models.CharField(max_length=50, choices=CATEGORY_CHOICES, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "FAQ Category"
        verbose_name_plural = "FAQ Categories"
        ordering = ['order', 'name']

    def __str__(self):
        return self.get_name_display()

class FAQ(models.Model):
    category = models.ForeignKey(FAQCategory, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=255)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ['category__order', 'order', 'question']
        unique_together = ['category', 'question']

    def __str__(self):
        return self.question

    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])
