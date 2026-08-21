from django import forms
from django.utils import timezone

from accounts.models import FacultyProfile, Role, StudentProfile, User

from .models import (
    Assignment, Course, Department, Enrollment, Event, Exam, FeeInvoice,
    Notice, Program,
)

CTRL = "form-control"
SEL = "form-select"


def _style(fields, widgets=None):
    """Apply Bootstrap classes to a set of bound form fields."""
    for name, field in fields.items():
        w = field.widget
        if isinstance(w, (forms.Select, forms.SelectMultiple)):
            w.attrs.setdefault("class", SEL)
        elif isinstance(w, forms.CheckboxInput):
            w.attrs.setdefault("class", "form-check-input")
        elif isinstance(w, (forms.DateInput, forms.DateTimeInput)):
            w.attrs.setdefault("class", CTRL)
            w.attrs.setdefault("type", "date")
        else:
            w.attrs.setdefault("class", CTRL)


# ==========================================================================
# STUDENT  (User + StudentProfile combined)
# ==========================================================================
class StudentForm(forms.Form):
    first_name = forms.CharField(max_length=60)
    last_name = forms.CharField(max_length=60)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, initial="0000", required=False)
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput, required=False,
                               help_text="Leave blank to keep the current password (on edit).")
    roll_no = forms.CharField(max_length=20)
    program = forms.ModelChoiceField(queryset=Program.objects.all(), required=False)
    current_semester = forms.IntegerField(min_value=1, max_value=12, initial=1)
    gender = forms.ChoiceField(choices=StudentProfile.GENDER, initial="O")
    address = forms.CharField(max_length=255, required=False)
    guardian_name = forms.CharField(max_length=120, required=False)

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        if instance:
            u = instance.user
            kwargs.setdefault("initial", {}).update({
                "first_name": u.first_name, "last_name": u.last_name,
                "email": u.email, "phone": u.phone, "username": u.username,
                "roll_no": instance.roll_no, "program": instance.program_id,
                "current_semester": instance.current_semester, "gender": instance.gender,
                "address": instance.address, "guardian_name": instance.guardian_name,
            })
        super().__init__(*args, **kwargs)
        _style(self.fields)
        if instance:
            self.fields["username"].widget.attrs["readonly"] = True

    def clean_username(self):
        username = self.cleaned_data["username"]
        qs = User.objects.filter(username__iexact=username)
        if self.instance:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise forms.ValidationError("Username already taken.")
        return username

    def clean_roll_no(self):
        roll = self.cleaned_data["roll_no"]
        qs = StudentProfile.objects.filter(roll_no__iexact=roll)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Roll number already exists.")
        return roll

    def clean(self):
        cleaned = super().clean()
        if not self.instance and not cleaned.get("password"):
            self.add_error("password", "Password is required for a new student.")
        return cleaned

    def save(self):
        d = self.cleaned_data
        if self.instance:
            u = self.instance.user
            sp = self.instance
        else:
            u = User(username=d["username"], role=Role.STUDENT)
            sp = StudentProfile(user=u)
        u.first_name = d["first_name"]
        u.last_name = d["last_name"]
        u.email = d["email"]
        u.phone = d["phone"] or "0000"
        u.role = Role.STUDENT
        if d.get("password"):
            u.set_password(d["password"])
        u.save()
        sp.user = u
        sp.roll_no = d["roll_no"]
        sp.program = d["program"]
        sp.current_semester = d["current_semester"]
        sp.gender = d["gender"]
        sp.address = d["address"] or "Campus Hostel Block"
        sp.guardian_name = d["guardian_name"] or "Guardian"
        if not sp.admission_date:
            sp.admission_date = timezone.now().date()
        sp.save()
        return sp


# ==========================================================================
# FACULTY  (User + FacultyProfile combined)
# ==========================================================================
class FacultyForm(forms.Form):
    first_name = forms.CharField(max_length=60)
    last_name = forms.CharField(max_length=60)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, initial="0000", required=False)
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput, required=False,
                               help_text="Leave blank to keep the current password (on edit).")
    employee_id = forms.CharField(max_length=20)
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=False)
    designation = forms.CharField(max_length=80, initial="Assistant Professor")
    specialization = forms.CharField(max_length=120, required=False)

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        if instance:
            u = instance.user
            kwargs.setdefault("initial", {}).update({
                "first_name": u.first_name, "last_name": u.last_name,
                "email": u.email, "phone": u.phone, "username": u.username,
                "employee_id": instance.employee_id, "department": instance.department_id,
                "designation": instance.designation, "specialization": instance.specialization,
            })
        super().__init__(*args, **kwargs)
        _style(self.fields)
        if instance:
            self.fields["username"].widget.attrs["readonly"] = True

    def clean_username(self):
        username = self.cleaned_data["username"]
        qs = User.objects.filter(username__iexact=username)
        if self.instance:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise forms.ValidationError("Username already taken.")
        return username

    def clean_employee_id(self):
        eid = self.cleaned_data["employee_id"]
        qs = FacultyProfile.objects.filter(employee_id__iexact=eid)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Employee ID already exists.")
        return eid

    def clean(self):
        cleaned = super().clean()
        if not self.instance and not cleaned.get("password"):
            self.add_error("password", "Password is required for a new faculty member.")
        return cleaned

    def save(self):
        d = self.cleaned_data
        if self.instance:
            u = self.instance.user
            fp = self.instance
        else:
            u = User(username=d["username"], role=Role.FACULTY)
            fp = FacultyProfile(user=u)
        u.first_name = d["first_name"]
        u.last_name = d["last_name"]
        u.email = d["email"]
        u.phone = d["phone"] or "0000"
        u.role = Role.FACULTY
        if d.get("password"):
            u.set_password(d["password"])
        u.save()
        fp.user = u
        fp.employee_id = d["employee_id"]
        fp.department = d["department"]
        fp.designation = d["designation"]
        fp.specialization = d["specialization"]
        if not fp.joining_date:
            fp.joining_date = timezone.now().date()
        fp.save()
        return fp


# ==========================================================================
# Simple ModelForms
# ==========================================================================
class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "description", "icon", "color", "image_url"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}),
                   "color": forms.TextInput(attrs={"type": "color"})}

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        _style(self.fields)


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ["name", "code", "department", "level", "duration_years", "total_seats"]

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        _style(self.fields)


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["code", "title", "department", "program", "faculty", "credits",
                  "semester_no", "description", "image_url"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        _style(self.fields)


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ["course", "title", "description", "max_marks", "due_date"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}),
                   "due_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *a, faculty=None, **k):
        super().__init__(*a, **k)
        if faculty is not None:
            self.fields["course"].queryset = Course.objects.filter(faculty=faculty)
        _style(self.fields)


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ["course", "term", "name", "date", "max_marks"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        _style(self.fields)


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["title", "description", "category", "location", "date", "icon", "image_url"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}),
                   "date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        _style(self.fields)


class FeeInvoiceForm(forms.ModelForm):
    class Meta:
        model = FeeInvoice
        fields = ["student", "term", "title", "amount", "amount_paid", "due_date"]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        _style(self.fields)
