from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.db.models import EmailField
from django.db.models import BooleanField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from core.helpers.enums import Account_Delete_Reason_Choices, GenderChoice

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
    is_admin = BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})

class AccountDeletionReason(models.Model):
    user = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    reason = models.CharField(
        max_length=50, choices=Account_Delete_Reason_Choices.choices,
        default=Account_Delete_Reason_Choices.OTHERS
    )
    additional_feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

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
    profile_pics = models.ImageField(
        _("Profile Picture"), upload_to="profile_pics/",
        blank=True, null=True
    )


    @property
    def get_profile_picture(self):
        if self.profile_picture:
            return self.profile_picture.url
        return f'{settings.STATIC_URL}images/avatar.png'
