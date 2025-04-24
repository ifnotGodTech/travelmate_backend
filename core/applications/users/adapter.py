# core/applications/users/adapters.py

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        print("SOCIAL LOGIN EMAIL<<<<<<<<<<<<<>>>>>>>>>>>>>>>>:", sociallogin.user.email)
