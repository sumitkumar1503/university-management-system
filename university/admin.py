from django.contrib import admin

from .models import (
    Assignment, Attendance, Course, Department, Enrollment, Event,
    Exam, FeeInvoice, Notice, Payment, Program, Result, Submission, AcademicTerm,
)

for model in (Department, Program, AcademicTerm, Course, Enrollment, Attendance,
              Assignment, Submission, Exam, Result, FeeInvoice, Payment, Event, Notice):
    admin.site.register(model)
