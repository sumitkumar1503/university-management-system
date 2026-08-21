"""
Local, self-contained "AI" layer for UMS.

No external API keys required. These helpers implement:
  * a rule/intent based assistant that answers questions from live DB data,
  * a heuristic performance predictor (weighted linear model),
  * an at-risk detector, and
  * study/teaching recommendations.

The logic is deterministic and explainable so it works fully offline.
"""
from __future__ import annotations

import re
from statistics import mean

from django.db.models import Avg, Count, Sum

from . import services


# --------------------------------------------------------------------------
# Performance predictor
# --------------------------------------------------------------------------
def predict_performance(attendance_pct: float, avg_marks: float,
                        submission_rate: float) -> dict:
    """
    Predict a student's likely end-of-term score (0-100) from three signals.

    Weighted model (explainable):
        score = 0.35*attendance + 0.50*avg_marks + 0.15*submission_rate
    """
    attendance_pct = max(0.0, min(100.0, attendance_pct))
    avg_marks = max(0.0, min(100.0, avg_marks))
    submission_rate = max(0.0, min(100.0, submission_rate))

    projected = 0.35 * attendance_pct + 0.50 * avg_marks + 0.15 * submission_rate
    projected = round(projected, 1)

    if projected >= 75:
        band, tone, icon = "On track for distinction", "success", "fa-trophy"
    elif projected >= 60:
        band, tone, icon = "Comfortable pass expected", "info", "fa-thumbs-up"
    elif projected >= 45:
        band, tone, icon = "Needs attention", "warning", "fa-triangle-exclamation"
    else:
        band, tone, icon = "High risk — intervene", "danger", "fa-circle-exclamation"

    drivers = []
    if attendance_pct < 75:
        drivers.append("Low attendance is pulling the projection down.")
    if avg_marks < 50:
        drivers.append("Recent exam averages are below the pass line.")
    if submission_rate < 60:
        drivers.append("Several assignments are still unsubmitted.")
    if not drivers:
        drivers.append("All signals are healthy — keep the momentum going.")

    return {
        "projected": projected,
        "band": band,
        "tone": tone,
        "icon": icon,
        "drivers": drivers,
        "inputs": {
            "attendance": round(attendance_pct, 1),
            "avg_marks": round(avg_marks, 1),
            "submission_rate": round(submission_rate, 1),
        },
    }


def student_prediction(student) -> dict:
    stats = services.student_stats(student)
    return predict_performance(stats["attendance_pct"], stats["avg_marks"],
                               stats["submission_rate"])


def at_risk_students(limit: int = 8) -> list[dict]:
    """Return students whose signals fall below healthy thresholds."""
    from accounts.models import StudentProfile

    rows = []
    for student in StudentProfile.objects.select_related("user", "program"):
        stats = services.student_stats(student)
        pred = predict_performance(stats["attendance_pct"], stats["avg_marks"],
                                   stats["submission_rate"])
        if pred["projected"] < 60 or stats["attendance_pct"] < 75:
            rows.append({
                "student": student,
                "attendance": stats["attendance_pct"],
                "avg_marks": stats["avg_marks"],
                "projected": pred["projected"],
                "tone": pred["tone"],
            })
    rows.sort(key=lambda r: r["projected"])
    return rows[:limit]


def study_recommendations(student) -> list[dict]:
    stats = services.student_stats(student)
    recs = []
    if stats["attendance_pct"] < 80:
        recs.append({"icon": "fa-calendar-check", "color": "#e17055",
                     "text": "Attend the next 5 classes without a gap to lift attendance above 80%."})
    if stats["pending_assignments"] > 0:
        recs.append({"icon": "fa-file-pen", "color": "#0984e3",
                     "text": f"You have {stats['pending_assignments']} pending assignment(s). "
                             "Submit the earliest due one today."})
    if stats["avg_marks"] < 60:
        recs.append({"icon": "fa-book-open-reader", "color": "#6C5CE7",
                     "text": "Book a revision slot for your weakest subject and attempt past papers."})
    weakest = stats.get("weakest_subject")
    if weakest:
        recs.append({"icon": "fa-bullseye", "color": "#00b894",
                     "text": f"Focus area: {weakest} — schedule 2 focused sessions this week."})
    if not recs:
        recs.append({"icon": "fa-star", "color": "#00b894",
                     "text": "You're performing well across the board. Aim for a distinction!"})
    return recs


# --------------------------------------------------------------------------
# Intent-based assistant
# --------------------------------------------------------------------------
def _kb_counts():
    from accounts.models import FacultyProfile, StudentProfile
    return {
        "students": StudentProfile.objects.count(),
        "faculty": FacultyProfile.objects.count(),
        "courses": services.Course.objects.count(),
        "departments": services.Department.objects.count(),
    }


def assistant_reply(text: str, user) -> dict:
    """Very small intent router over the live database."""
    q = (text or "").lower().strip()

    def resp(message, icon="fa-robot", suggestions=None):
        return {"reply": message, "icon": icon,
                "suggestions": suggestions or _default_suggestions(user)}

    if not q:
        return resp("Ask me about attendance, results, fees, courses or campus stats.")

    if re.search(r"\b(hi|hello|hey|namaste)\b", q):
        return resp(f"Hello {user.display_name.split()[0]}! How can I help you today?",
                    "fa-hand-sparkles")

    # Attendance -----------------------------------------------------------
    if "attendance" in q:
        if user.is_student and hasattr(user, "student_profile"):
            s = services.student_stats(user.student_profile)
            return resp(f"Your overall attendance is <b>{s['attendance_pct']}%</b> "
                        f"across {s['courses']} course(s). "
                        + ("Great going!" if s['attendance_pct'] >= 80
                           else "Try not to miss upcoming classes."),
                        "fa-calendar-check")
        agg = services.overall_attendance()
        return resp(f"Campus-wide attendance is averaging <b>{agg}%</b> this term.",
                    "fa-calendar-check")

    # Results / marks ------------------------------------------------------
    if any(w in q for w in ["result", "marks", "grade", "gpa", "score", "cgpa"]):
        if user.is_student and hasattr(user, "student_profile"):
            s = services.student_stats(user.student_profile)
            return resp(f"Your average score is <b>{s['avg_marks']}%</b> "
                        f"(GPA ≈ {s['gpa']}). Predicted term score: "
                        f"<b>{student_prediction(user.student_profile)['projected']}</b>.",
                        "fa-graduation-cap")
        return resp("Students can ask me for their personal GPA and predicted score.",
                    "fa-graduation-cap")

    # Fees -----------------------------------------------------------------
    if any(w in q for w in ["fee", "fees", "payment", "due", "invoice"]):
        if user.is_student and hasattr(user, "student_profile"):
            s = services.student_stats(user.student_profile)
            if s["fee_due"] > 0:
                return resp(f"You have an outstanding balance of "
                            f"<b>${s['fee_due']:,.0f}</b>. Please clear it before the due date.",
                            "fa-wallet")
            return resp("All your fees are cleared. You're good to go! ✅", "fa-wallet")
        total = services.total_fees_collected()
        return resp(f"Total fees collected so far: <b>${total:,.0f}</b>.", "fa-wallet")

    # Counts ---------------------------------------------------------------
    if "how many" in q or "count" in q or "number of" in q or "total" in q:
        kb = _kb_counts()
        if "student" in q:
            return resp(f"There are <b>{kb['students']}</b> students enrolled.", "fa-users")
        if "teacher" in q or "faculty" in q or "professor" in q:
            return resp(f"We have <b>{kb['faculty']}</b> faculty members.", "fa-chalkboard-user")
        if "course" in q:
            return resp(f"The catalogue lists <b>{kb['courses']}</b> courses.", "fa-book")
        if "department" in q:
            return resp(f"There are <b>{kb['departments']}</b> departments.", "fa-building-columns")
        return resp(f"Campus at a glance — {kb['students']} students, {kb['faculty']} faculty, "
                    f"{kb['courses']} courses across {kb['departments']} departments.",
                    "fa-chart-pie")

    # Courses --------------------------------------------------------------
    if "course" in q or "subject" in q:
        top = services.popular_courses(3)
        if top:
            names = ", ".join(f"{c.code} ({c.enrolled_count})" for c in top)
            return resp(f"Most enrolled courses right now: {names}.", "fa-book")

    # At-risk (staff) ------------------------------------------------------
    if "risk" in q or "weak" in q or "struggling" in q:
        rows = at_risk_students(5)
        if rows:
            names = ", ".join(r["student"].user.display_name for r in rows)
            return resp(f"{len(rows)} student(s) need attention: {names}.",
                        "fa-triangle-exclamation")
        return resp("No students are currently flagged as at-risk. 🎉",
                    "fa-triangle-exclamation")

    if "recommend" in q or "advice" in q or "improve" in q:
        if user.is_student and hasattr(user, "student_profile"):
            recs = study_recommendations(user.student_profile)
            return resp("Here's what I'd focus on: " + " ".join(r["text"] for r in recs[:2]),
                        "fa-lightbulb")

    return resp("I can help with <b>attendance</b>, <b>results</b>, <b>fees</b>, "
                "<b>courses</b> and campus statistics. Try one of the chips below.",
                "fa-circle-question")


def _default_suggestions(user):
    if getattr(user, "is_student", False):
        return ["My attendance", "My GPA", "Any fees due?", "Study recommendations"]
    if getattr(user, "is_faculty", False):
        return ["At-risk students", "How many courses?", "Campus attendance"]
    return ["How many students?", "Total fees collected", "At-risk students", "Popular courses"]
