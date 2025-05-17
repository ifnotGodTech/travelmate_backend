from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import UpdateView
from django.views.generic import CreateView
from core.applications.users.forms import SuperCustomUserCreationForm
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import hashlib
import os
from datetime import datetime, timedelta

from core.applications.users.models import User


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "id"
    slug_url_kwarg = "id"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return reverse("users:detail", kwargs={"pk": self.request.user.pk})


user_redirect_view = UserRedirectView.as_view()



class SuperUserSignupView(CreateView):
    model = User
    form_class = SuperCustomUserCreationForm
    template_name = "users/superuser_signup.html"
    success_url = reverse_lazy('admin:login')


superuser_signup = SuperUserSignupView.as_view()


@csrf_exempt
@require_http_methods(["POST"])
def reactivate_superuser(request):
    # Get the token from environment variable
    expected_token = os.environ.get('SUPERUSER_REACTIVATION_TOKEN')
    if not expected_token:
        return JsonResponse({'error': 'Token not configured'}, status=500)

    # Get token from request
    token = request.headers.get('X-Reactivate-Token')
    if not token or token != expected_token:
        return JsonResponse({'error': 'Invalid token'}, status=403)

    try:
        email = request.POST.get('email')
        if not email:
            return JsonResponse({'error': 'Email is required'}, status=400)

        user = User.objects.get(email=email)
        user.is_superuser = True
        user.is_staff = True
        user.save()

        return JsonResponse({
            'success': True,
            'message': f'Superuser with email {email} has been reactivated'
        })
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
