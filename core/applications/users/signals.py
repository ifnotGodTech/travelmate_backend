from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import user_logged_in
from django.contrib.auth import user_logged_out
from django.core.cache import cache
from django.dispatch import receiver
from django.db.models.signals import post_save, post_migrate

from core.applications.users.models import Profile, User, Role
from core.helpers.utils import get_bearer_token

channel_layer = get_channel_layer()


@receiver(user_logged_in)
def on_user_logged_in(sender, token=None, user=None, **kwargs):
    cache.set(
        token,
        user.id,
        settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
    )


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    cache.delete(get_bearer_token(request))
    channel_config = {"type": "on_user_logged_out", "code": 200}
    async_to_sync(channel_layer.group_send)(str(request.user.id), channel_config)


# Signal to create Profile when User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_migrate)
def create_superadmin_role(sender, **kwargs):
    Role.objects.get_or_create(name="Super Admin", description="Full access to all system Features and data")
