from __future__ import annotations

import uuid

import auto_prefetch
from django import forms
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.query import QuerySet
from model_utils import FieldTracker


def generate_uuid() -> str:
    """
    Number of Possibilities = 16^8

    Here, 16 represents the number of possible hexadecimal characters
    (0-9 and a-f), and 8 is the length of the substring.

    Calculating it:

    16^10 = 1,099,511,627,776
    """
    return uuid.uuid4().hex


class ChoiceArrayField(ArrayField):
    def formfield(self, **kwargs):
        defaults = {
            "form_class": forms.TypedMultipleChoiceField,
            "choices": self.base_field.choices,
            "coerce": self.base_field.to_python,
            "widget": forms.CheckboxSelectMultiple,
        }
        defaults.update(kwargs)

        return super(ArrayField, self).formfield(**defaults)


class VisibleManager(auto_prefetch.Manager):
    def get_queryset(self) -> QuerySet:
        """filters queryset to return only visible items"""
        return super().get_queryset().filter(visible=True)


class TimeBasedModel(auto_prefetch.Model):
    id = models.UUIDField(
        default=generate_uuid,
        editable=False,
        primary_key=True,
        serialize=False,
        unique=True,
    )
    visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta(auto_prefetch.Model.Meta):
        abstract = True

    objects = auto_prefetch.Manager()
    items: models.QuerySet = VisibleManager()


class TitleTimeBasedModel(TimeBasedModel):
    title = models.CharField(max_length=50, null=True, blank=True)

    class Meta(auto_prefetch.Model.Meta):
        abstract = True
        ordering = ["title", "created_at"]

    def __str__(self):
        return self.title


class UIDTimeBasedModel(TimeBasedModel):
    id = models.CharField(
        primary_key=True,
        default=generate_uuid,
        max_length=120,
        editable=False,
        unique=True,
    )
    tracker = FieldTracker()

    class Meta(auto_prefetch.Model.Meta):
        abstract = True
        ordering = ["-created_at"]

    def __str__(self):
        return self.id


class BaseModel(UIDTimeBasedModel):
    created_by = auto_prefetch.ForeignKey(
        "users.Account",
        on_delete=models.CASCADE,
        related_name="created_by",
    )

    class Meta(auto_prefetch.Model.Meta):
        abstract = True
