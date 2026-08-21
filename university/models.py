from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=40, default="fa-building-columns",
                            help_text="Font Awesome icon name")
    color = models.CharField(max_length=20, default="#6C5CE7")
    image_url = models.URLField(blank=True, default="")

    class Meta:
        ordering = ["name"]

    def get_absolute_url(self):
        return reverse("university:department_detail", args=[self.pk])

    def __str__(self):
        return f"{self.code} — {self.name}"


class Program(models.Model):
    LEVELS = [("UG", "Undergraduate"), ("PG", "Postgraduate"), ("PHD", "Doctorate")]
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=15, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="programs")
    level = models.CharField(max_length=3, choices=LEVELS, default="UG")
    duration_years = models.PositiveSmallIntegerField(default=4)
    total_seats = models.PositiveIntegerField(default=120)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class AcademicTerm(models.Model):
    name = models.CharField(max_length=40, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name


class Course(models.Model):
    code = models.CharField(max_length=15, unique=True)
    title = models.CharField(max_length=150)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="courses")
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="courses")
    faculty = models.ForeignKey("accounts.FacultyProfile", on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="courses")
    credits = models.PositiveSmallIntegerField(default=4)
    semester_no = models.PositiveSmallIntegerField(default=1)
    description = models.TextField(blank=True, default="")
    image_url = models.URLField(blank=True, default="")

    class Meta:
        ordering = ["code"]

    def get_absolute_url(self):
        return reverse("university:course_detail", args=[self.pk])

    @property
    def enrolled_count(self):
        return self.enrollments.filter(status=Enrollment.ACTIVE).count()

    def __str__(self):
        return f"{self.code} — {self.title}"


class Enrollment(models.Model):
    ACTIVE, COMPLETED, DROPPED = "ACTIVE", "COMPLETED", "DROPPED"
    STATUS = [(ACTIVE, "Active"), (COMPLETED, "Completed"), (DROPPED, "Dropped")]
    student = models.ForeignKey("accounts.StudentProfile", on_delete=models.CASCADE,
                                related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    term = models.ForeignKey(AcademicTerm, on_delete=models.SET_NULL, null=True, blank=True)
    enrolled_on = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS, default=ACTIVE)

    class Meta:
        unique_together = ("student", "course")
        ordering = ["-enrolled_on"]

    def __str__(self):
        return f"{self.student.roll_no} → {self.course.code}"


class Attendance(models.Model):
    PRESENT, ABSENT, LATE = "P", "A", "L"
    STATUS = [(PRESENT, "Present"), (ABSENT, "Absent"), (LATE, "Late")]
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=1, choices=STATUS, default=PRESENT)

    class Meta:
        unique_together = ("enrollment", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.enrollment} {self.date} {self.status}"


class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    max_marks = models.PositiveSmallIntegerField(default=100)
    assigned_on = models.DateField(default=timezone.now)
    due_date = models.DateField()

    class Meta:
        ordering = ["-due_date"]

    def get_absolute_url(self):
        return reverse("university:assignment_detail", args=[self.pk])

    @property
    def is_open(self):
        return self.due_date >= timezone.now().date()

    def __str__(self):
        return f"{self.title} ({self.course.code})"


class Submission(models.Model):
    PENDING, SUBMITTED, GRADED = "PENDING", "SUBMITTED", "GRADED"
    STATUS = [(PENDING, "Pending"), (SUBMITTED, "Submitted"), (GRADED, "Graded")]
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey("accounts.StudentProfile", on_delete=models.CASCADE,
                                related_name="submissions")
    content = models.TextField(blank=True, default="")
    submitted_on = models.DateTimeField(null=True, blank=True)
    marks = models.PositiveSmallIntegerField(null=True, blank=True)
    feedback = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS, default=PENDING)

    class Meta:
        unique_together = ("assignment", "student")
        ordering = ["-submitted_on"]

    def __str__(self):
        return f"{self.student.roll_no} · {self.assignment.title}"


class Exam(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="exams")
    term = models.ForeignKey(AcademicTerm, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=80, default="Mid Term")
    date = models.DateField(default=timezone.now)
    max_marks = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.name} — {self.course.code}"


class Result(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="results")
    student = models.ForeignKey("accounts.StudentProfile", on_delete=models.CASCADE,
                                related_name="results")
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = ("exam", "student")
        ordering = ["-exam__date"]

    @property
    def percentage(self):
        if not self.exam.max_marks:
            return 0
        return round(float(self.marks_obtained) / self.exam.max_marks * 100, 1)

    @property
    def grade(self):
        p = self.percentage
        if p >= 90: return "A+"
        if p >= 80: return "A"
        if p >= 70: return "B+"
        if p >= 60: return "B"
        if p >= 50: return "C"
        if p >= 40: return "D"
        return "F"

    def __str__(self):
        return f"{self.student.roll_no} {self.exam.course.code}: {self.marks_obtained}"


class FeeInvoice(models.Model):
    PAID, PARTIAL, UNPAID = "PAID", "PARTIAL", "UNPAID"
    STATUS = [(PAID, "Paid"), (PARTIAL, "Partial"), (UNPAID, "Unpaid")]
    student = models.ForeignKey("accounts.StudentProfile", on_delete=models.CASCADE,
                                related_name="invoices")
    term = models.ForeignKey(AcademicTerm, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=120, default="Semester Tuition Fee")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    issued_on = models.DateField(default=timezone.now)
    due_date = models.DateField()

    class Meta:
        ordering = ["-issued_on"]

    @property
    def balance(self):
        return self.amount - self.amount_paid

    @property
    def status(self):
        if self.amount_paid >= self.amount:
            return self.PAID
        if self.amount_paid > 0:
            return self.PARTIAL
        return self.UNPAID

    def __str__(self):
        return f"{self.title} · {self.student.roll_no}"


class Payment(models.Model):
    invoice = models.ForeignKey(FeeInvoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_on = models.DateField(default=timezone.now)
    method = models.CharField(max_length=30, default="Online")
    reference = models.CharField(max_length=40, default="TXN-0000")

    class Meta:
        ordering = ["-paid_on"]

    def __str__(self):
        return f"{self.reference} · {self.amount}"


class Event(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=40, default="Campus")
    location = models.CharField(max_length=120, default="Main Auditorium")
    date = models.DateField(default=timezone.now)
    image_url = models.URLField(blank=True, default="")
    icon = models.CharField(max_length=40, default="fa-calendar-star")

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return self.title


class Notice(models.Model):
    AUDIENCE = [("ALL", "Everyone"), ("STUDENT", "Students"),
                ("FACULTY", "Faculty"), ("ADMIN", "Admins")]
    title = models.CharField(max_length=150)
    body = models.TextField()
    audience = models.CharField(max_length=10, choices=AUDIENCE, default="ALL")
    is_pinned = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title
