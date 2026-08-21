from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Administrator"
    FACULTY = "FACULTY", "Faculty"
    STUDENT = "STUDENT", "Student"


# Per-role UI theme (drives the colour scheme / design language of each portal).
ROLE_THEMES = {
    Role.ADMIN: {
        "key": "admin",
        "name": "Administrator",
        "primary": "#6C5CE7",
        "primary_dark": "#4834d4",
        "accent": "#e84393",
        "sidebar": "linear-gradient(180deg,#2d2a4a 0%,#3b3564 100%)",
        "surface": "#f4f5fb",
        "gradient": "linear-gradient(135deg,#6C5CE7 0%,#8f7bff 100%)",
        "icon": "fa-user-shield",
    },
    Role.FACULTY: {
        "key": "faculty",
        "name": "Faculty",
        "primary": "#009688",
        "primary_dark": "#00695c",
        "accent": "#ff7043",
        "sidebar": "linear-gradient(180deg,#08312c 0%,#0b4f45 100%)",
        "surface": "#eef7f5",
        "gradient": "linear-gradient(135deg,#009688 0%,#26c6a6 100%)",
        "icon": "fa-chalkboard-user",
    },
    Role.STUDENT: {
        "key": "student",
        "name": "Student",
        "primary": "#0984e3",
        "primary_dark": "#0652a5",
        "accent": "#e17055",
        "sidebar": "linear-gradient(180deg,#0a2540 0%,#123a63 100%)",
        "surface": "#eef4fb",
        "gradient": "linear-gradient(135deg,#0984e3 0%,#48b1f3 100%)",
        "icon": "fa-user-graduate",
    },
}


class User(AbstractUser):
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    phone = models.CharField(max_length=20, blank=True, default="0000")
    avatar_url = models.URLField(blank=True)

    @property
    def theme(self):
        return ROLE_THEMES.get(self.role, ROLE_THEMES[Role.STUDENT])

    @property
    def is_admin_role(self):
        return self.role == Role.ADMIN

    @property
    def is_faculty(self):
        return self.role == Role.FACULTY

    @property
    def is_student(self):
        return self.role == Role.STUDENT

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def avatar(self):
        if self.avatar_url:
            return self.avatar_url
        seed = (self.display_name or self.username).replace(" ", "+")
        colors = {"ADMIN": "6C5CE7", "FACULTY": "009688", "STUDENT": "0984e3"}
        bg = colors.get(self.role, "6C5CE7")
        return f"https://ui-avatars.com/api/?name={seed}&background={bg}&color=fff&bold=true"

    def __str__(self):
        return f"{self.display_name} ({self.get_role_display()})"


class StudentProfile(models.Model):
    GENDER = [("M", "Male"), ("F", "Female"), ("O", "Other")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    roll_no = models.CharField(max_length=20, unique=True)
    program = models.ForeignKey("university.Program", on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="students")
    current_semester = models.PositiveSmallIntegerField(default=1)
    gender = models.CharField(max_length=1, choices=GENDER, default="O")
    date_of_birth = models.DateField(null=True, blank=True)
    admission_date = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True, default="Campus Hostel Block")
    guardian_name = models.CharField(max_length=120, blank=True, default="Guardian")

    class Meta:
        ordering = ["roll_no"]

    def get_absolute_url(self):
        return reverse("university:student_detail", args=[self.pk])

    def __str__(self):
        return f"{self.roll_no} - {self.user.display_name}"


class FacultyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="faculty_profile")
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey("university.Department", on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="faculty")
    designation = models.CharField(max_length=80, default="Assistant Professor")
    specialization = models.CharField(max_length=120, blank=True, default="")
    joining_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["employee_id"]

    def get_absolute_url(self):
        return reverse("university:faculty_detail", args=[self.pk])

    def __str__(self):
        return f"{self.employee_id} - {self.user.display_name}"
