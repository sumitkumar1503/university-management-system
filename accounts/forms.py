from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

from university.models import Program

from .models import Role, StudentProfile, User

INPUT = "form-control form-control-lg"


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(
        attrs={"class": INPUT, "placeholder": "Username", "autofocus": True}))
    password = forms.CharField(widget=forms.PasswordInput(
        attrs={"class": INPUT, "placeholder": "Password"}))


class SignUpForm(forms.ModelForm):
    """Public self-registration -> always creates a STUDENT account."""
    first_name = forms.CharField(widget=forms.TextInput(
        attrs={"class": INPUT, "placeholder": "First name"}))
    last_name = forms.CharField(widget=forms.TextInput(
        attrs={"class": INPUT, "placeholder": "Last name"}))
    email = forms.EmailField(widget=forms.EmailInput(
        attrs={"class": INPUT, "placeholder": "you@example.com"}))
    program = forms.ModelChoiceField(
        queryset=Program.objects.all(), required=False,
        widget=forms.Select(attrs={"class": "form-select form-select-lg"}))
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput(
        attrs={"class": INPUT, "placeholder": "Create a password"}))
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput(
        attrs={"class": INPUT, "placeholder": "Repeat password"}))

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]
        widgets = {
            "username": forms.TextInput(attrs={"class": INPUT, "placeholder": "Choose a username"}),
        }

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already taken.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = Role.STUDENT
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            count = StudentProfile.objects.count() + 1
            StudentProfile.objects.create(
                user=user,
                roll_no=f"UMS{timezone.now().year}{count:04d}",
                program=self.cleaned_data.get("program"),
                admission_date=timezone.now().date(),
            )
        return user
