from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class User_login(UserCreationForm):

    class Meta:
        form = UserCreationForm()
        fields = [
            'username', 'password'
        ]

    