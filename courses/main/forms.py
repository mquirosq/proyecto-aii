from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class':'form-control','placeholder':'Nombre de usuario','autofocus':'autofocus'})
        self.fields['password1'].widget.attrs.update({'class':'form-control','placeholder':'Contraseña'})
        self.fields['password2'].widget.attrs.update({'class':'form-control','placeholder':'Repite la contraseña'})

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if not password1:
            raise ValidationError('La contraseña no puede estar vacía.')
        if password1 != password2:
            raise ValidationError('Las contraseñas no coinciden.')
        return password2
