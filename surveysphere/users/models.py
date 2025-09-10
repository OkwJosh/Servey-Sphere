from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    dob = models.DateField(blank=False, null=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    email = models.EmailField(unique=True, blank=False, null=False)

    def __str__(self):
        return self.email
