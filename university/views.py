import json
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import FacultyProfile, Role, StudentProfile

from . import ai, services
from .decorators import role_required
from .forms import (
    AssignmentForm, CourseForm, DepartmentForm, EventForm, ExamForm,
    FacultyForm, FeeInvoiceForm, ProgramForm, StudentForm,
)
from .models import (
    Assignment, Attendance, Course, Department, Enrollment, Event,
    Exam, FeeInvoice, Notice, Payment, Program, Result, Submission,
)


# ==========================================================================
# PUBLIC SITE
# ==========================================================================
def home(request):
    ctx = {
        "stats": {
            "students": StudentProfile.objects.count(),
            "faculty": FacultyProfile.objects.count(),
            "courses": Course.objects.count(),
            "departments": Department.objects.count(),
        },
        "departments": Department.objects.all()[:6],
        "featured_courses": Course.objects.select_related("department")[:6],
        "events": Event.objects.filter(date__gte=date.today())[:3],
    }
    return render(request, "public/home.html", ctx)


def about(request):
    return render(request, "public/about.html", {
        "departments": Department.objects.all(),
    })


def contact(request):
    if request.method == "POST":
        messages.success(request, "Thanks for reaching out! Our team will reply to your "
                                  "example.com inbox shortly.")
        return redirect("university:contact")
    return render(request, "public/contact.html")


def courses_public(request):
    q = request.GET.get("q", "").strip()
    courses = Course.objects.select_related("department", "faculty__user")
    if q:
        courses = courses.filter(Q(title__icontains=q) | Q(code__icontains=q))
    return render(request, "public/courses.html", {
        "courses": courses, "departments": Department.objects.all(), "q": q,
    })


# ==========================================================================
# DASHBOARD ROUTER
# ==========================================================================
@login_required
def dashboard(request):
    user = request.user
    if user.is_admin_role or user.is_superuser:
        return render(request, "dashboard/admin_dashboard.html", services.admin_dashboard())
    if user.is_faculty:
        fp = get_object_or_404(FacultyProfile, user=user)
        ctx = services.faculty_dashboard(fp)
        ctx["faculty"] = fp
        return render(request, "dashboard/faculty_dashboard.html", ctx)
    sp = get_object_or_404(StudentProfile, user=user)
    ctx = services.student_dashboard(sp)
    ctx["student"] = sp
    ctx["prediction"] = ai.student_prediction(sp)
    return render(request, "dashboard/student_dashboard.html", ctx)


# ==========================================================================
# Generic form / delete helpers (rendered with reusable templates)
# ==========================================================================
def _render_form(request, form, title, subtitle="", icon="fa-pen-to-square", back=None):
    return render(request, "dashboard/form_page.html", {
        "form": form, "form_title": title, "form_subtitle": subtitle,
        "form_icon": icon, "back_url": back,
    })


def _confirm_delete(request, obj, label, back):
    if request.method == "POST":
        name = str(obj)
        obj.delete()
        messages.success(request, f"Deleted {label}: {name}.")
        return redirect(back)
    return render(request, "dashboard/confirm_delete.html", {
        "object": obj, "label": label, "back_url": back,
    })


# ==========================================================================
# ADMIN AREA — STUDENTS
# ==========================================================================
@role_required(Role.ADMIN)
def admin_students(request):
    q = request.GET.get("q", "").strip()
    students = StudentProfile.objects.select_related("user", "program")
    if q:
        students = students.filter(
            Q(roll_no__icontains=q) | Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q))
    return render(request, "dashboard/admin_students.html",
                  {"students": students, "q": q})


@role_required(Role.ADMIN)
def student_detail(request, pk):
    student = get_object_or_404(StudentProfile.objects.select_related("user", "program"), pk=pk)
    ctx = services.student_dashboard(student)
    ctx["student"] = student
    ctx["prediction"] = ai.student_prediction(student)
    ctx["recommendations"] = ai.study_recommendations(student)
    return render(request, "dashboard/student_detail.html", ctx)


@role_required(Role.ADMIN)
def student_create(request):
    form = StudentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        sp = form.save()
        messages.success(request, f"Student {sp.user.display_name} added.")
        return redirect("university:student_detail", pk=sp.pk)
    return _render_form(request, form, "Add Student", "Create a new student account and profile",
                        "fa-user-plus", "university:admin_students")


@role_required(Role.ADMIN)
def student_edit(request, pk):
    sp = get_object_or_404(StudentProfile, pk=pk)
    form = StudentForm(request.POST or None, instance=sp)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Student updated.")
        return redirect("university:student_detail", pk=sp.pk)
    return _render_form(request, form, "Edit Student", sp.user.display_name,
                        "fa-user-pen", "university:admin_students")


@role_required(Role.ADMIN)
def student_delete(request, pk):
    sp = get_object_or_404(StudentProfile, pk=pk)
    user = sp.user
    if request.method == "POST":
        name = sp.user.display_name
        user.delete()  # cascades to profile
        messages.success(request, f"Deleted student {name}.")
        return redirect("university:admin_students")
    return render(request, "dashboard/confirm_delete.html", {
        "object": sp, "label": "student", "back_url": "university:admin_students",
    })


# ==========================================================================
# ADMIN AREA — FACULTY
# ==========================================================================
@role_required(Role.ADMIN)
def admin_faculty(request):
    faculty = FacultyProfile.objects.select_related("user", "department").annotate(
        n_courses=Count("courses"))
    return render(request, "dashboard/admin_faculty.html", {"faculty": faculty})


@role_required(Role.ADMIN)
def faculty_detail(request, pk):
    fp = get_object_or_404(FacultyProfile.objects.select_related("user", "department"), pk=pk)
    return render(request, "dashboard/faculty_detail.html",
                  {"faculty": fp, "courses": fp.courses.all()})


@role_required(Role.ADMIN)
def faculty_create(request):
    form = FacultyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        fp = form.save()
        messages.success(request, f"Faculty {fp.user.display_name} added.")
        return redirect("university:faculty_detail", pk=fp.pk)
    return _render_form(request, form, "Add Faculty", "Create a new faculty account and profile",
                        "fa-user-plus", "university:admin_faculty")


@role_required(Role.ADMIN)
def faculty_edit(request, pk):
    fp = get_object_or_404(FacultyProfile, pk=pk)
    form = FacultyForm(request.POST or None, instance=fp)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Faculty updated.")
        return redirect("university:faculty_detail", pk=fp.pk)
    return _render_form(request, form, "Edit Faculty", fp.user.display_name,
                        "fa-user-pen", "university:admin_faculty")


@role_required(Role.ADMIN)
def faculty_delete(request, pk):
    fp = get_object_or_404(FacultyProfile, pk=pk)
    user = fp.user
    if request.method == "POST":
        name = fp.user.display_name
        user.delete()
        messages.success(request, f"Deleted faculty {name}.")
        return redirect("university:admin_faculty")
    return render(request, "dashboard/confirm_delete.html", {
        "object": fp, "label": "faculty", "back_url": "university:admin_faculty",
    })


# ==========================================================================
# ADMIN AREA — DEPARTMENTS & PROGRAMS
# ==========================================================================
@role_required(Role.ADMIN)
def admin_departments(request):
    departments = Department.objects.annotate(
        n_courses=Count("courses", distinct=True),
        n_programs=Count("programs", distinct=True))
    return render(request, "dashboard/admin_departments.html", {"departments": departments})


@login_required
def department_detail(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    return render(request, "dashboard/department_detail.html", {
        "dept": dept, "courses": dept.courses.all(), "programs": dept.programs.all(),
    })


@role_required(Role.ADMIN)
def department_create(request):
    form = DepartmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        dept = form.save()
        messages.success(request, f"Department {dept.name} created.")
        return redirect("university:department_detail", pk=dept.pk)
    return _render_form(request, form, "Add Department", "", "fa-building-columns",
                        "university:admin_departments")


@role_required(Role.ADMIN)
def department_edit(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    form = DepartmentForm(request.POST or None, instance=dept)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Department updated.")
        return redirect("university:department_detail", pk=dept.pk)
    return _render_form(request, form, "Edit Department", dept.name, "fa-pen",
                        "university:admin_departments")


@role_required(Role.ADMIN)
def department_delete(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    return _confirm_delete(request, dept, "department", "university:admin_departments")


@role_required(Role.ADMIN)
def program_create(request):
    form = ProgramForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        p = form.save()
        messages.success(request, f"Program {p.name} created.")
        return redirect("university:department_detail", pk=p.department_id)
    return _render_form(request, form, "Add Program", "", "fa-graduation-cap",
                        "university:admin_departments")


@role_required(Role.ADMIN)
def program_edit(request, pk):
    p = get_object_or_404(Program, pk=pk)
    form = ProgramForm(request.POST or None, instance=p)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Program updated.")
        return redirect("university:department_detail", pk=p.department_id)
    return _render_form(request, form, "Edit Program", p.name, "fa-pen",
                        "university:admin_departments")


@role_required(Role.ADMIN)
def program_delete(request, pk):
    p = get_object_or_404(Program, pk=pk)
    return _confirm_delete(request, p, "program", "university:admin_departments")


# ==========================================================================
# COURSES  (admin CRUD + enrollment management)
# ==========================================================================
@login_required
def admin_courses(request):
    q = request.GET.get("q", "").strip()
    courses = Course.objects.select_related("department", "faculty__user").annotate(
        n=Count("enrollments"))
    if q:
        courses = courses.filter(Q(title__icontains=q) | Q(code__icontains=q))
    return render(request, "dashboard/admin_courses.html", {"courses": courses, "q": q})


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course.objects.select_related(
        "department", "faculty__user"), pk=pk)
    roster = Enrollment.objects.filter(course=course).select_related("student__user")
    enrolled_ids = roster.values_list("student_id", flat=True)
    available = StudentProfile.objects.exclude(pk__in=enrolled_ids).select_related("user")
    return render(request, "dashboard/course_detail.html", {
        "course": course, "roster": roster,
        "assignments": course.assignments.all(), "exams": course.exams.all(),
        "available_students": available,
    })


@role_required(Role.ADMIN)
def course_create(request):
    form = CourseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        c = form.save()
        messages.success(request, f"Course {c.code} created.")
        return redirect("university:course_detail", pk=c.pk)
    return _render_form(request, form, "Add Course", "", "fa-book",
                        "university:admin_courses")


@role_required(Role.ADMIN)
def course_edit(request, pk):
    c = get_object_or_404(Course, pk=pk)
    form = CourseForm(request.POST or None, instance=c)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Course updated.")
        return redirect("university:course_detail", pk=c.pk)
    return _render_form(request, form, "Edit Course", c.title, "fa-pen",
                        "university:admin_courses")


@role_required(Role.ADMIN)
def course_delete(request, pk):
    c = get_object_or_404(Course, pk=pk)
    return _confirm_delete(request, c, "course", "university:admin_courses")


@role_required(Role.ADMIN)
@require_POST
def course_enroll(request, pk):
    course = get_object_or_404(Course, pk=pk)
    student_id = request.POST.get("student")
    if student_id:
        sp = get_object_or_404(StudentProfile, pk=student_id)
        Enrollment.objects.get_or_create(student=sp, course=course,
                                          defaults={"status": Enrollment.ACTIVE})
        messages.success(request, f"Enrolled {sp.user.display_name} in {course.code}.")
    return redirect("university:course_detail", pk=course.pk)


@role_required(Role.ADMIN)
@require_POST
def enrollment_remove(request, pk):
    enr = get_object_or_404(Enrollment, pk=pk)
    course_pk = enr.course_id
    name = enr.student.user.display_name
    enr.delete()
    messages.info(request, f"Removed {name} from the course.")
    return redirect("university:course_detail", pk=course_pk)


# ==========================================================================
# FEES  (admin)
# ==========================================================================
@role_required(Role.ADMIN)
def admin_fees(request):
    invoices = FeeInvoice.objects.select_related("student__user")
    ctx = {
        "invoices": invoices[:100],
        "collected": services.total_fees_collected(),
        "billed": services.total_fees_billed(),
        "unpaid": sum(float(i.balance) for i in invoices),
    }
    return render(request, "dashboard/admin_fees.html", ctx)


@role_required(Role.ADMIN)
def fee_create(request):
    form = FeeInvoiceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Invoice created.")
        return redirect("university:admin_fees")
    return _render_form(request, form, "Create Invoice", "", "fa-file-invoice-dollar",
                        "university:admin_fees")


@role_required(Role.ADMIN)
@require_POST
def record_payment(request, pk):
    invoice = get_object_or_404(FeeInvoice, pk=pk)
    try:
        amount = Decimal(request.POST.get("amount", "0"))
    except (InvalidOperation, TypeError):
        amount = Decimal("0")
    if amount > 0:
        amount = min(amount, invoice.balance)
        invoice.amount_paid += amount
        invoice.save()
        Payment.objects.create(invoice=invoice, amount=amount, method="Front-desk",
                               reference=f"TXN-{timezone.now().strftime('%H%M%S')}")
        messages.success(request, f"Recorded ${amount:,.0f} against {invoice.title}.")
    return redirect("university:admin_fees")


# ==========================================================================
# NOTICES & EVENTS  (notices are viewable by everyone)
# ==========================================================================
@login_required
def notices(request):
    can_post = request.user.is_admin_role or request.user.is_faculty or request.user.is_superuser
    if request.method == "POST":
        if not can_post:
            messages.error(request, "You are not allowed to publish notices.")
            return redirect("university:notices")
        Notice.objects.create(
            title=request.POST.get("title", "Untitled"),
            body=request.POST.get("body", ""),
            audience=request.POST.get("audience", "ALL"),
            is_pinned=bool(request.POST.get("is_pinned")),
            created_by=request.user)
        messages.success(request, "Notice published.")
        return redirect("university:notices")
    aud = ["ALL", request.user.role]
    return render(request, "dashboard/notices.html", {
        "notices": Notice.objects.filter(audience__in=aud), "can_post": can_post,
    })


@role_required(Role.ADMIN, Role.FACULTY)
@require_POST
def notice_delete(request, pk):
    notice = get_object_or_404(Notice, pk=pk)
    notice.delete()
    messages.info(request, "Notice removed.")
    return redirect("university:notices")


@login_required
def events(request):
    return render(request, "dashboard/events.html",
                  {"events": Event.objects.all(),
                   "can_manage": request.user.is_admin_role or request.user.is_superuser})


@role_required(Role.ADMIN)
def event_create(request):
    form = EventForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Event created.")
        return redirect("university:events")
    return _render_form(request, form, "Add Event", "", "fa-calendar-plus",
                        "university:events")


@role_required(Role.ADMIN)
def event_edit(request, pk):
    ev = get_object_or_404(Event, pk=pk)
    form = EventForm(request.POST or None, instance=ev)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Event updated.")
        return redirect("university:events")
    return _render_form(request, form, "Edit Event", ev.title, "fa-pen",
                        "university:events")


@role_required(Role.ADMIN)
def event_delete(request, pk):
    ev = get_object_or_404(Event, pk=pk)
    return _confirm_delete(request, ev, "event", "university:events")


# ==========================================================================
# FACULTY AREA — courses, attendance (day-wise), assignments, grading
# ==========================================================================
@role_required(Role.FACULTY)
def faculty_courses(request):
    fp = get_object_or_404(FacultyProfile, user=request.user)
    courses = Course.objects.filter(faculty=fp).annotate(n=Count("enrollments"))
    return render(request, "dashboard/faculty_courses.html", {"courses": courses})


@role_required(Role.FACULTY, Role.ADMIN)
def faculty_attendance(request, pk):
    """Mark / edit attendance for a chosen date (defaults to today)."""
    if request.user.is_admin_role or request.user.is_superuser:
        course = get_object_or_404(Course, pk=pk)
    else:
        fp = get_object_or_404(FacultyProfile, user=request.user)
        course = get_object_or_404(Course, pk=pk, faculty=fp)
    roster = Enrollment.objects.filter(course=course, status=Enrollment.ACTIVE
                                       ).select_related("student__user")
    sel = request.GET.get("date") or request.POST.get("date")
    try:
        day = date.fromisoformat(sel) if sel else timezone.now().date()
    except ValueError:
        day = timezone.now().date()
    if request.method == "POST":
        marked = 0
        for e in roster:
            status = request.POST.get(f"status_{e.id}")
            if status in dict(Attendance.STATUS):
                Attendance.objects.update_or_create(
                    enrollment=e, date=day, defaults={"status": status})
                marked += 1
        messages.success(request, f"Attendance saved for {marked} student(s) on {day}.")
        return redirect(f"{request.path}?date={day.isoformat()}")
    existing = {a.enrollment_id: a.status for a in
                Attendance.objects.filter(enrollment__in=roster, date=day)}
    return render(request, "dashboard/faculty_attendance.html", {
        "course": course, "roster": roster, "existing": existing, "today": day,
    })


@role_required(Role.FACULTY, Role.ADMIN)
def faculty_attendance_history(request, pk):
    """Day-wise attendance register: dates x students matrix."""
    if request.user.is_admin_role or request.user.is_superuser:
        course = get_object_or_404(Course, pk=pk)
    else:
        fp = get_object_or_404(FacultyProfile, user=request.user)
        course = get_object_or_404(Course, pk=pk, faculty=fp)
    roster = list(Enrollment.objects.filter(course=course, status=Enrollment.ACTIVE
                                            ).select_related("student__user"))
    records = Attendance.objects.filter(enrollment__course=course)
    dates = sorted({r.date for r in records}, reverse=True)
    lookup = {(r.enrollment_id, r.date): r.status for r in records}
    rows = []
    for e in roster:
        cells = [{"date": d, "status": lookup.get((e.id, d))} for d in dates]
        present = sum(1 for c in cells if c["status"] in (Attendance.PRESENT, Attendance.LATE))
        total = sum(1 for c in cells if c["status"])
        rows.append({"enrollment": e, "cells": cells,
                     "pct": round(present / total * 100, 1) if total else 0})
    return render(request, "dashboard/faculty_attendance_history.html", {
        "course": course, "dates": dates, "rows": rows,
    })


@role_required(Role.FACULTY, Role.ADMIN)
def faculty_assignments(request):
    if request.user.is_admin_role or request.user.is_superuser:
        assignments = Assignment.objects.select_related("course").annotate(
            n_sub=Count("submissions"))
    else:
        fp = get_object_or_404(FacultyProfile, user=request.user)
        assignments = Assignment.objects.filter(course__faculty=fp).select_related(
            "course").annotate(n_sub=Count("submissions"))
    return render(request, "dashboard/faculty_assignments.html", {"assignments": assignments})


@role_required(Role.FACULTY, Role.ADMIN)
def assignment_create(request):
    fp = None
    if not (request.user.is_admin_role or request.user.is_superuser):
        fp = get_object_or_404(FacultyProfile, user=request.user)
    form = AssignmentForm(request.POST or None, faculty=fp)
    if request.method == "POST" and form.is_valid():
        a = form.save()
        messages.success(request, f"Assignment '{a.title}' created.")
        return redirect("university:faculty_grade", pk=a.pk)
    return _render_form(request, form, "New Assignment", "", "fa-file-circle-plus",
                        "university:faculty_assignments")


@role_required(Role.FACULTY, Role.ADMIN)
def assignment_edit(request, pk):
    fp = None
    if request.user.is_admin_role or request.user.is_superuser:
        a = get_object_or_404(Assignment, pk=pk)
    else:
        fp = get_object_or_404(FacultyProfile, user=request.user)
        a = get_object_or_404(Assignment, pk=pk, course__faculty=fp)
    form = AssignmentForm(request.POST or None, instance=a, faculty=fp)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Assignment updated.")
        return redirect("university:faculty_grade", pk=a.pk)
    return _render_form(request, form, "Edit Assignment", a.title, "fa-pen",
                        "university:faculty_assignments")


@role_required(Role.FACULTY, Role.ADMIN)
def assignment_delete(request, pk):
    if request.user.is_admin_role or request.user.is_superuser:
        a = get_object_or_404(Assignment, pk=pk)
    else:
        fp = get_object_or_404(FacultyProfile, user=request.user)
        a = get_object_or_404(Assignment, pk=pk, course__faculty=fp)
    return _confirm_delete(request, a, "assignment", "university:faculty_assignments")


@login_required
def assignment_detail(request, pk):
    assignment = get_object_or_404(Assignment.objects.select_related("course"), pk=pk)
    ctx = {"assignment": assignment}
    if request.user.is_student and hasattr(request.user, "student_profile"):
        sp = request.user.student_profile
        ctx["submission"] = Submission.objects.filter(assignment=assignment, student=sp).first()
        ctx["enrolled"] = Enrollment.objects.filter(student=sp, course=assignment.course).exists()
    else:
        ctx["submissions"] = Submission.objects.filter(
            assignment=assignment).select_related("student__user")
    return render(request, "dashboard/assignment_detail.html", ctx)


@role_required(Role.ADMIN, Role.FACULTY)
def exam_create(request):
    initial = {}
    course_id = request.GET.get("course")
    if course_id:
        initial["course"] = course_id
    form = ExamForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        x = form.save()
        messages.success(request, f"Exam '{x.name}' created.")
        return redirect("university:course_detail", pk=x.course_id)
    return _render_form(request, form, "Add Exam", "", "fa-file-pen",
                        "university:admin_courses")


@role_required(Role.ADMIN, Role.FACULTY)
def exam_edit(request, pk):
    x = get_object_or_404(Exam, pk=pk)
    form = ExamForm(request.POST or None, instance=x)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Exam updated.")
        return redirect("university:course_detail", pk=x.course_id)
    return _render_form(request, form, "Edit Exam", x.name, "fa-pen",
                        "university:admin_courses")


@role_required(Role.ADMIN, Role.FACULTY)
def exam_delete(request, pk):
    x = get_object_or_404(Exam, pk=pk)
    course_pk = x.course_id
    if request.method == "POST":
        x.delete()
        messages.success(request, "Exam deleted.")
        return redirect("university:course_detail", pk=course_pk)
    return render(request, "dashboard/confirm_delete.html", {
        "object": x, "label": "exam", "back_url": "university:admin_courses",
    })


@role_required(Role.FACULTY, Role.ADMIN)
def faculty_grade(request, pk):
    if request.user.is_admin_role or request.user.is_superuser:
        assignment = get_object_or_404(Assignment, pk=pk)
    else:
        fp = get_object_or_404(FacultyProfile, user=request.user)
        assignment = get_object_or_404(Assignment, pk=pk, course__faculty=fp)
    subs = Submission.objects.filter(assignment=assignment).select_related("student__user")
    if request.method == "POST":
        for s in subs:
            raw = request.POST.get(f"marks_{s.id}", "").strip()
            if raw:
                try:
                    s.marks = min(int(raw), assignment.max_marks)
                    s.feedback = request.POST.get(f"feedback_{s.id}", "")
                    s.status = Submission.GRADED
                    s.save()
                except ValueError:
                    pass
        messages.success(request, "Grades updated.")
        return redirect("university:faculty_grade", pk=assignment.pk)
    return render(request, "dashboard/faculty_grade.html",
                  {"assignment": assignment, "subs": subs})


# ==========================================================================
# STUDENT AREA
# ==========================================================================
@role_required(Role.STUDENT)
def student_courses(request):
    sp = get_object_or_404(StudentProfile, user=request.user)
    enrollments = Enrollment.objects.filter(student=sp).select_related(
        "course__department", "course__faculty__user")
    return render(request, "dashboard/student_courses.html", {"enrollments": enrollments})


@role_required(Role.STUDENT)
def student_attendance(request):
    sp = get_object_or_404(StudentProfile, user=request.user)
    rows = []
    for e in Enrollment.objects.filter(student=sp).select_related("course"):
        qs = Attendance.objects.filter(enrollment=e)
        t = qs.count()
        p = qs.filter(status__in=[Attendance.PRESENT, Attendance.LATE]).count()
        rows.append({"course": e.course, "total": t, "present": p,
                     "pct": round(p / t * 100, 1) if t else 0})
    log = Attendance.objects.filter(enrollment__student=sp).select_related(
        "enrollment__course").order_by("-date")[:60]
    return render(request, "dashboard/student_attendance.html", {"rows": rows, "log": log})


@role_required(Role.STUDENT)
def student_results(request):
    sp = get_object_or_404(StudentProfile, user=request.user)
    results = Result.objects.filter(student=sp).select_related("exam__course")
    return render(request, "dashboard/student_results.html",
                  {"results": results, "stats": services.student_stats(sp)})


@role_required(Role.STUDENT)
def student_assignments(request):
    sp = get_object_or_404(StudentProfile, user=request.user)
    course_ids = Enrollment.objects.filter(student=sp).values_list("course_id", flat=True)
    assignments = Assignment.objects.filter(course_id__in=course_ids).select_related("course")
    subs = {s.assignment_id: s for s in Submission.objects.filter(student=sp)}
    data = [{"assignment": a, "submission": subs.get(a.id)} for a in assignments]
    return render(request, "dashboard/student_assignments.html", {"data": data})


@role_required(Role.STUDENT)
@require_POST
def submit_assignment(request, pk):
    sp = get_object_or_404(StudentProfile, user=request.user)
    assignment = get_object_or_404(Assignment, pk=pk)
    content = request.POST.get("content", "").strip()
    Submission.objects.update_or_create(
        assignment=assignment, student=sp,
        defaults={"content": content, "submitted_on": timezone.now(),
                  "status": Submission.SUBMITTED})
    messages.success(request, f"Submitted '{assignment.title}'.")
    return redirect("university:student_assignments")


@role_required(Role.STUDENT)
def student_fees(request):
    sp = get_object_or_404(StudentProfile, user=request.user)
    invoices = FeeInvoice.objects.filter(student=sp)
    return render(request, "dashboard/student_fees.html", {
        "invoices": invoices, "stats": services.student_stats(sp),
    })


# ==========================================================================
# AI FEATURES (no external API key)
# ==========================================================================
@login_required
def ai_assistant(request):
    return render(request, "dashboard/ai_assistant.html",
                  {"suggestions": ai._default_suggestions(request.user)})


@login_required
@require_POST
def ai_reply(request):
    try:
        payload = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        payload = {}
    message = payload.get("message", "")
    return JsonResponse(ai.assistant_reply(message, request.user))


@login_required
def ai_insights(request):
    user = request.user
    if user.is_student and hasattr(user, "student_profile"):
        sp = user.student_profile
        return render(request, "dashboard/ai_insights_student.html", {
            "prediction": ai.student_prediction(sp),
            "recommendations": ai.study_recommendations(sp),
            "stats": services.student_stats(sp),
        })
    return render(request, "dashboard/ai_insights_staff.html", {
        "at_risk": ai.at_risk_students(12),
        "top_courses": services.popular_courses(5),
    })
