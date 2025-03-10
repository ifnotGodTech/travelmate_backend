from django.db.models import TextChoices


class GenderChoice(TextChoices):
    MALE = ("Male", "Male")
    FEMALE = ("Female", "Female")
