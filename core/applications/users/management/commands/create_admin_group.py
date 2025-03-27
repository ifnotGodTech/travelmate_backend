from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from core.applications.users.models import User

class Command(BaseCommand):
    """
    Custom Django management command to create an "Admin" group
    and assign all user-related permissions to it.

    This ensures that users assigned to the Admin group have
    the necessary permissions to manage other users.
    """

    help = "Create an Admin group with necessary user management permissions"

    def handle(self, *args, **kwargs):
        """
        Main method executed when the command is run.
        It creates the "Admin" group and assigns all user-related permissions.
        """
        # Create or get the "Admin" group
        admin_group, created = Group.objects.get_or_create(name="Admin")

        if created:
            self.stdout.write(self.style.SUCCESS("Admin group created successfully!"))
        else:
            self.stdout.write(self.style.WARNING("Admin group already exists."))

        # Get content type for the User model
        user_content_type = ContentType.objects.get_for_model(User)

        # Fetch all permissions related to the user model

        user_permissions = Permission.objects.filter(content_type=user_content_type)

        # Assign permissions to the Admin group
        admin_group.permissions.set(user_permissions)
        admin_group.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Assigned {user_permissions.count()} permissions to the Admin group."
            )
        )
