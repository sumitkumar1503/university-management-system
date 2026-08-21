"""Analytics + aggregation helpers shared by dashboards and the AI layer."""
from __future__ import annotations

import calendar
from datetime import date

from django.db.models import Avg, Count, F, Sum

from .models import (
    Assignment, Attendance, Course, Department, Enrollment, Event,
    Exam, FeeInvoice, Notice, Program, Result, Submission,
)


# --------------------------------------------------------------------------
# Small reusable aggregates
# --------------------------------------------------------------------------
def overall_attendance() -> float:
    total = Attendance.objects.count()
    if not total:
        return 0.0
    present = Attendance.objects.filter(
        status__in=[Attendance.PRESENT, Attendance.LATE]).count()
    return round(present / total * 100, 1)


def total_fees_collected() -> float:
    agg = FeeInvoice.objects.aggregate(s=Sum("amount_paid"))
    return float(agg["s"] or 0)


def total_fees_billed() -> float:
    agg = FeeInvoice.objects.aggregate(s=Sum("amount"))
    return float(agg["s"] or 0)


def popular_courses(limit: int = 5):
    return list(
        Course.objects.annotate(n=Count("enrollments"))
        .order_by("-n")[:limit]
    )


# --------------------------------------------------------------------------
# Per-student statistics
# --------------------------------------------------------------------------
def student_stats(student) -> dict:
    enrollments = Enrollment.objects.filter(student=student)
    course_count = enrollments.count()

    att_qs = Attendance.objects.filter(enrollment__student=student)
    att_total = att_qs.count()
    att_present = att_qs.filter(status__in=[Attendance.PRESENT, Attendance.LATE]).count()
    attendance_pct = round(att_present / att_total * 100, 1) if att_total else 0.0

    results = Result.objects.filter(student=student).select_related("exam__course")
    pcts = [r.percentage for r in results]
    avg_marks = round(sum(pcts) / len(pcts), 1) if pcts else 0.0
    gpa = round(min(10.0, avg_marks / 9.5), 2)

    # weakest subject by average percentage
    subject_scores: dict[str, list[float]] = {}
    for r in results:
        subject_scores.setdefault(r.exam.course.title, []).append(r.percentage)
    weakest_subject = None
    if subject_scores:
        weakest_subject = min(
            subject_scores.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))[0]

    subs = Submission.objects.filter(student=student)
    total_assignments = Assignment.objects.filter(
        course__enrollments__student=student).distinct().count()
    submitted = subs.exclude(status=Submission.PENDING).count()
    pending = max(0, total_assignments - submitted)
    submission_rate = round(submitted / total_assignments * 100, 1) if total_assignments else 100.0

    fee_due = 0.0
    for inv in FeeInvoice.objects.filter(student=student):
        fee_due += float(inv.balance)

    return {
        "courses": course_count,
        "attendance_pct": attendance_pct,
        "avg_marks": avg_marks,
        "gpa": gpa,
        "pending_assignments": pending,
        "submission_rate": submission_rate,
        "fee_due": round(fee_due, 2),
        "weakest_subject": weakest_subject,
    }


# --------------------------------------------------------------------------
# Dashboard context builders
# --------------------------------------------------------------------------
def _month_labels(n=12):
    return [calendar.month_abbr[m] for m in range(1, n + 1)]


def admin_dashboard():
    from accounts.models import FacultyProfile, StudentProfile

    student_count = StudentProfile.objects.count()
    faculty_count = FacultyProfile.objects.count()
    course_count = Course.objects.count()
    collected = total_fees_collected()

    # Monthly fee collection (current year) -------------------------------
    year = date.today().year
    collected_by_month = [0.0] * 12
    pending_by_month = [0.0] * 12
    for inv in FeeInvoice.objects.all():
        m = inv.issued_on.month - 1
        collected_by_month[m] += float(inv.amount_paid)
        pending_by_month[m] += float(inv.balance)

    # Enrollment trend (cumulative by month) ------------------------------
    enroll_by_month = [0] * 12
    for e in Enrollment.objects.all():
        enroll_by_month[e.enrolled_on.month - 1] += 1
    cumulative = []
    running = 0
    for v in enroll_by_month:
        running += v
        cumulative.append(running)

    # Department distribution --------------------------------------------
    dept_rows = (Department.objects
                 .annotate(n=Count("programs__students"))
                 .values("name", "color", "n").order_by("-n"))

    # Attendance split ----------------------------------------------------
    att = Attendance.objects.values("status").annotate(n=Count("id"))
    att_map = {a["status"]: a["n"] for a in att}

    return {
        "cards": [
            {"label": "Total Students", "value": student_count, "delta": "+12% vs last month",
             "icon": "fa-users", "grad": "linear-gradient(135deg,#7b6cf6,#5a4bd6)", "up": True},
            {"label": "Total Faculty", "value": faculty_count, "delta": "+5% vs last month",
             "icon": "fa-chalkboard-user", "grad": "linear-gradient(135deg,#20c997,#12b886)", "up": True},
            {"label": "Total Courses", "value": course_count, "delta": "-3% vs last month",
             "icon": "fa-book", "grad": "linear-gradient(135deg,#f368a6,#e6488a)", "up": False},
            {"label": "Fees Collected", "value": f"${collected:,.0f}", "delta": "+18% vs last month",
             "icon": "fa-sack-dollar", "grad": "linear-gradient(135deg,#4dabf7,#3b9ae1)", "up": True},
        ],
        "months": _month_labels(),
        "fee_collected": collected_by_month,
        "fee_pending": pending_by_month,
        "enroll_trend": cumulative,
        "new_admissions": enroll_by_month,
        "dept_rows": list(dept_rows),
        "attendance_split": [
            att_map.get(Attendance.PRESENT, 0),
            att_map.get(Attendance.ABSENT, 0),
            att_map.get(Attendance.LATE, 0),
        ],
        "recent_notices": Notice.objects.all()[:5],
        "upcoming_events": Event.objects.filter(date__gte=date.today())[:4],
        "top_courses": popular_courses(5),
    }


def faculty_dashboard(faculty):
    courses = Course.objects.filter(faculty=faculty)
    course_ids = list(courses.values_list("id", flat=True))
    students = (Enrollment.objects.filter(course_id__in=course_ids)
                .values("student").distinct().count())
    assignments = Assignment.objects.filter(course_id__in=course_ids)
    pending_grading = Submission.objects.filter(
        assignment__course_id__in=course_ids, status=Submission.SUBMITTED).count()

    # attendance per course
    course_labels, course_att = [], []
    for c in courses:
        qs = Attendance.objects.filter(enrollment__course=c)
        t = qs.count()
        p = qs.filter(status__in=[Attendance.PRESENT, Attendance.LATE]).count()
        course_labels.append(c.code)
        course_att.append(round(p / t * 100, 1) if t else 0)

    # grade distribution across faculty courses
    grade_buckets = {"A+": 0, "A": 0, "B+": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for r in Result.objects.filter(exam__course_id__in=course_ids):
        grade_buckets[r.grade] += 1

    return {
        "cards": [
            {"label": "My Courses", "value": courses.count(), "icon": "fa-book-open",
             "grad": "linear-gradient(135deg,#009688,#26c6a6)"},
            {"label": "My Students", "value": students, "icon": "fa-user-group",
             "grad": "linear-gradient(135deg,#0d9488,#0f766e)"},
            {"label": "Assignments", "value": assignments.count(), "icon": "fa-file-lines",
             "grad": "linear-gradient(135deg,#f59e0b,#f97316)"},
            {"label": "To Grade", "value": pending_grading, "icon": "fa-pen-clip",
             "grad": "linear-gradient(135deg,#ef4444,#f43f5e)"},
        ],
        "courses": courses,
        "course_labels": course_labels,
        "course_att": course_att,
        "grade_labels": list(grade_buckets.keys()),
        "grade_values": list(grade_buckets.values()),
        "recent_submissions": Submission.objects.filter(
            assignment__course_id__in=course_ids).select_related(
            "student__user", "assignment")[:6],
    }


def student_dashboard(student):
    stats = student_stats(student)
    enrollments = Enrollment.objects.filter(student=student).select_related("course")

    # attendance trend over recent classes (last 8 dates)
    dates = list(Attendance.objects.filter(enrollment__student=student)
                 .values_list("date", flat=True).distinct().order_by("date"))[-8:]
    trend_labels, trend_values = [], []
    for d in dates:
        day_qs = Attendance.objects.filter(enrollment__student=student, date=d)
        t = day_qs.count()
        p = day_qs.filter(status__in=[Attendance.PRESENT, Attendance.LATE]).count()
        trend_labels.append(d.strftime("%d %b"))
        trend_values.append(round(p / t * 100) if t else 0)

    # marks per subject
    subj_labels, subj_values = [], []
    for e in enrollments:
        r = Result.objects.filter(student=student, exam__course=e.course).first()
        if r:
            subj_labels.append(e.course.code)
            subj_values.append(r.percentage)

    return {
        "stats": stats,
        "cards": [
            {"label": "Attendance", "value": f"{stats['attendance_pct']}%", "icon": "fa-calendar-check",
             "grad": "linear-gradient(135deg,#0984e3,#48b1f3)"},
            {"label": "Average / GPA", "value": f"{stats['gpa']}", "icon": "fa-graduation-cap",
             "grad": "linear-gradient(135deg,#6C5CE7,#8f7bff)"},
            {"label": "Pending Work", "value": stats["pending_assignments"], "icon": "fa-list-check",
             "grad": "linear-gradient(135deg,#e17055,#f0932b)"},
            {"label": "Fee Balance", "value": f"${stats['fee_due']:,.0f}", "icon": "fa-wallet",
             "grad": "linear-gradient(135deg,#00b894,#20bf6b)"},
        ],
        "enrollments": enrollments,
        "trend_labels": trend_labels,
        "trend_values": trend_values,
        "subj_labels": subj_labels,
        "subj_values": subj_values,
        "upcoming_events": Event.objects.filter(date__gte=date.today())[:4],
        "invoices": FeeInvoice.objects.filter(student=student)[:5],
    }
