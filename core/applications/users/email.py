from templated_mail.mail import BaseEmailMessage

from core.applications.users.token import default_token_generator
from django.conf import settings


class ActivationEmail(BaseEmailMessage):
    template_name = "email/activation.html"

    def get_context_data(self):
        # ActivationEmail can be deleted
        context = super().get_context_data()

        user = context.get("user")
        context["token"] = default_token_generator.make_token(user)
        return context


class OTPRegistrationEmail(BaseEmailMessage):
    """
    Email class for sending OTPs during user registration.
    """
    template_name = "email/otp_registration.html"

    def get_context_data(self):
        """
        Add the OTP to the email context.
        """

        context = super().get_context_data()
        context["otp"] = self.context.get("otp")  # Pass the OTP to the template
        context["site_name"] = settings.SITE_NAME
        return context


class ConfirmationEmail(BaseEmailMessage):
    template_name = "email/confirmation.html"


class PasswordResetEmail(ActivationEmail):
    template_name = "email/password_reset.html"


class PasswordChangedConfirmationEmail(BaseEmailMessage):
    template_name = "email/password_changed_confirmation.html"


class UsernameChangedConfirmationEmail(BaseEmailMessage):
    template_name = "email/username_changed_confirmation.html"


class UsernameResetEmail(ActivationEmail):
    template_name = "email/username_reset.html"

    def get_context_data(self):
        context = super().get_context_data()

        user = context.get("user")
        context["token"] = default_token_generator.make_token(user)
        return context
