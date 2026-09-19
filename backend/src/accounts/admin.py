from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User

# Rejestrujemy stockowym UserAdmin — pola AbstractUser są niezmienione,
# customowy fieldset dojdzie, gdy pojawią się pola domenowe (role itp.).
admin.site.register(User, UserAdmin)
