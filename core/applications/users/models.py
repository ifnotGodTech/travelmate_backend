from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.db.models import EmailField
from django.db.models import BooleanField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.auth.models import Group
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField

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
    is_active = BooleanField(default=True)

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
        if self.profile_pics:  # Changed from self.profile_picture to self.profile_pics
            return self.profile_pics.url
        return f'{settings.STATIC_URL}images/avatar.png'

class Role(Group):
    """
    Extends the built‑in auth.Group with extra fields.
    This will create its own `core_applications_users_role` table
    linked 1‑to‑1 with auth_group.
    """
    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"


    description = models.TextField(blank=True)
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="roles_created",
    )

    @property
    def assigned_users(self):
        return self.user_set.all()

    def assign_user(self, user: User):
        current_roles = Role.objects.filter(user=user)
        for role in current_roles:
            role.user_set.remove(user)

        self.user_set.add(user)


class RoleInvitation(models.Model):
    email = models.EmailField()
    name = models.CharField(max_length=255, blank=True)
    role = models.ForeignKey("Role", on_delete=models.CASCADE, related_name="invitations")
    token = models.CharField(max_length=255)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_role_invitations"
    )
    sent_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("email", "role")
        ordering = ["-sent_at"]
        verbose_name = "Role Invitation"
        verbose_name_plural = "Role Invitations"

    def is_accepted(self):
        return self.accepted_at is not None
