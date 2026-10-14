"""Formulários do app de usuários (uso no Django Admin).

Substituem os formulários padrão do ``django.contrib.auth`` porque o Findly usa
um modelo de usuário customizado (login por **e-mail**, sem ``username``).
"""
from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError

from .models import User


class UserCreationForm(forms.ModelForm):
    """Formulário de criação de usuário com confirmação de senha."""

    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput,
        help_text="A senha é processada com hash e não é armazenada em texto puro.",
    )
    password2 = forms.CharField(
        label="Confirmação da senha", widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ("email", "full_name", "phone", "role")

    def clean_password2(self) -> str:
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("As senhas não coincidem.")
        return password2

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """Formulário de edição de usuário."""

    class Meta:
        model = User
        fields = "__all__"
