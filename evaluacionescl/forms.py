# forms.py
from django import forms
from .models import RegistroUsuarios, RegistroAdmin

class RegistroUsuariosForm(forms.ModelForm):
    contrasena = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = RegistroUsuarios
        fields = ['nombre', 'apellido', 'edad', 'matricula', 'cuatrimestre', 'contrasena']

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_contrasena(self.cleaned_data['contrasena'])
        if commit:
            usuario.save()
        return usuario

class RegistroAdminForm(forms.ModelForm):
    contrasena = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = RegistroAdmin
        fields = ['nombre', 'apellido', 'matricula', 'contrasena']

    def save(self, commit=True):
        admin = super().save(commit=False)
        admin.set_contrasena(self.cleaned_data['contrasena'])
        if commit:
            admin.save()
        return admin

class LoginForm(forms.Form):
    matricula = forms.CharField(max_length=20)
    contrasena = forms.CharField(widget=forms.PasswordInput())
