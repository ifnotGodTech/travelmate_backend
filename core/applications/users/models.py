from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.db.models import EmailField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.helpers.enums import GenderChoice

from .managers import UserManager
from django.db import models
import auto_prefetch


class User(AbstractUser):
    """
    Default custom user model for travelmate-backend.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})


class Profile(models.Model):
    """
    Profile model for travelmate-backend.
    """

    user: "User" = auto_prefetch.OneToOneField(
        "users.User", on_delete=models.CASCADE, related_name="profile"
    )
    first_name  = models.CharField(_("First Name"), max_length=50, blank=True, null=True)
    last_name = models.CharField(_("Last Name"), max_length=50, blank=True, null=True)
    gender = models.CharField(
        _("Gender"), max_length=10, choices=GenderChoice.choices,
        blank=True, null=True
    )
    date_of_birth = models.DateField(_("Date of Birth"), blank=True, null=True)
    address = models.TextField(_("Address"), blank=True, null=True)
    mobile_number = models.CharField(_("Mobile Number"), max_length=15, blank=True, null=True)
