"""
Seed the University Management System with realistic, privacy-safe demo data.

Privacy note: all emails use the @example.com domain and phone numbers are 0000
so the demo can be shown publicly (e.g. on YouTube) without exposing real
personal information.

Usage:
    python manage.py seed_demo          # seed (wipes previous demo data)
    python manage.py seed_demo --keep   # seed without wiping
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import FacultyProfile, Role, StudentProfile
from university.models import (
    AcademicTerm, Assignment, Attendance, Course, Department, Enrollment,
    Event, Exam, FeeInvoice, Notice, Payment, Program, Result, Submission,
)

User = get_user_model()
random.seed(42)

PASSWORD = "demo1234"
EMAIL_DOMAIN = "example.com"
PHONE = "0000"

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Ananya", "Diya", "Ishaan", "Kabir", "Meera",
    "Riya", "Rohan", "Saanvi", "Arjun", "Kavya", "Neha", "Priya", "Rahul",
    "Sara", "Tara", "Yash", "Zara", "Nikhil", "Pooja", "Karan", "Isha",
    "Dev", "Anika", "Manav", "Sneha", "Varun", "Aisha", "Reyansh", "Myra",
    "Kiaan", "Aadhya", "Vihaan", "Anaya", "Krish", "Navya", "Shaurya", "Siya",
]
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Reddy", "Nair", "Iyer", "Rao", "Gupta",
    "Mehta", "Chopra", "Bose", "Das", "Kapoor", "Singh", "Kulkarni", "Menon",
]

DEPARTMENTS = [
    ("Computer Science", "CSE", "fa-laptop-code", "#6C5CE7",
     "Software, AI, data science and modern computing systems."),
    ("Electronics & Communication", "ECE", "fa-microchip", "#0984e3",
     "Circuits, embedded systems, signal processing and communication."),
    ("Mechanical Engineering", "MECH", "fa-gears", "#e17055",
     "Design, thermodynamics, robotics and manufacturing."),
    ("Business Administration", "MBA", "fa-briefcase", "#00b894",
     "Management, finance, marketing and entrepreneurship."),
    ("Civil Engineering", "CIVIL", "fa-helmet-safety", "#f0932b",
     "Structures, construction, surveying and urban planning."),
    ("Biotechnology", "BIO", "fa-dna", "#e84393",
     "Genetics, molecular biology and bio-informatics."),
]

PROGRAMS = [
    ("B.Tech Computer Science", "BT-CSE", "CSE", "UG", 4),
    ("M.Tech Data Science", "MT-DS", "CSE", "PG", 2),
    ("B.Tech Electronics", "BT-ECE", "ECE", "UG", 4),
    ("B.Tech Mechanical", "BT-MECH", "MECH", "UG", 4),
    ("Master of Business Admin", "MBA-GEN", "MBA", "PG", 2),
    ("B.Tech Civil", "BT-CIVIL", "CIVIL", "UG", 4),
    ("B.Sc Biotechnology", "BS-BIO", "BIO", "UG", 3),
]

COURSES = [
    ("CS101", "Introduction to Programming", "CSE", 1),
    ("CS201", "Data Structures & Algorithms", "CSE", 3),
    ("CS305", "Database Management Systems", "CSE", 5),
    ("CS402", "Machine Learning", "CSE", 7),
    ("EC101", "Basic Electronics", "ECE", 1),
    ("EC210", "Digital Signal Processing", "ECE", 4),
    ("EC330", "Embedded Systems", "ECE", 6),
    ("ME101", "Engineering Mechanics", "MECH", 1),
    ("ME220", "Thermodynamics", "MECH", 3),
    ("ME340", "Robotics & Automation", "MECH", 6),
    ("MB110", "Principles of Management", "MBA", 1),
    ("MB230", "Financial Accounting", "MBA", 2),
    ("MB350", "Digital Marketing", "MBA", 3),
    ("CV120", "Structural Analysis", "CIVIL", 2),
    ("CV310", "Transportation Engineering", "CIVIL", 5),
    ("BT150", "Cell Biology", "BIO", 1),
    ("BT260", "Genetic Engineering", "BIO", 4),
    ("BT370", "Bioinformatics", "BIO", 6),
]

EVENTS = [
    ("TechFest 2026", "Annual technology festival with hackathons, robotics and coding contests.",
     "Technology", "Main Auditorium", "fa-microchip"),
    ("Cultural Night", "An evening of music, dance and drama celebrating campus diversity.",
     "Culture", "Open Air Theatre", "fa-masks-theater"),
    ("Career & Placement Fair", "Meet 50+ recruiters across engineering and management domains.",
     "Career", "Convention Centre", "fa-briefcase"),
    ("Sports Meet", "Inter-department athletics, cricket and football championship.",
     "Sports", "University Ground", "fa-medal"),
    ("Research Symposium", "Students present papers and posters to a panel of experts.",
     "Academics", "Seminar Hall B", "fa-flask"),
    ("Alumni Reunion", "Reconnect with graduates and hear inspiring success stories.",
     "Community", "Central Lawn", "fa-people-group"),
]

NOTICES = [
    ("Mid-Term Examinations Schedule Released", "The mid-term exam timetable is now available. "
     "Please check your course pages for dates and reporting times.", "STUDENT", True),
    ("Fee Payment Deadline Extended", "The last date for semester fee payment has been extended "
     "by one week. Kindly clear dues to avoid late charges.", "ALL", True),
    ("Faculty Development Program", "A three-day FDP on 'AI in Education' will be conducted next "
     "month. Interested faculty may register at the academic office.", "FACULTY", False),
    ("Library Timings Updated", "The central library will now remain open until 10 PM on weekdays "
     "during the examination season.", "ALL", False),
    ("Guest Lecture on Cloud Computing", "An industry expert will deliver a guest lecture this "
     "Friday. All CSE and ECE students are encouraged to attend.", "STUDENT", False),
    ("Campus Placement Drive", "Registrations are open for the upcoming placement drive. "
     "Eligible students should update their profiles.", "STUDENT", False),
]


class Command(BaseCommand):
    help = "Seed the database with demo University Management System data."

    def add_arguments(self, parser):
        parser.add_argument("--keep", action="store_true",
                            help="Do not wipe existing demo data before seeding.")

    def handle(self, *args, **options):
        if not options["keep"]:
            self.stdout.write("Clearing previous data...")
            for model in (Payment, FeeInvoice, Result, Exam, Submission, Assignment,
                          Attendance, Enrollment, Course, Program, Department,
                          Event, Notice, AcademicTerm):
                model.objects.all().delete()
            StudentProfile.objects.all().delete()
            FacultyProfile.objects.all().delete()
            User.objects.exclude(is_superuser=True).delete()

        today = date.today()
        year = today.year

        # --- Academic terms -------------------------------------------------
        term = AcademicTerm.objects.create(
            name=f"Fall {year}", start_date=date(year, 7, 1),
            end_date=date(year, 12, 20), is_current=True)
        AcademicTerm.objects.create(
            name=f"Spring {year}", start_date=date(year, 1, 5),
            end_date=date(year, 5, 30), is_current=False)

        # --- Departments & programs ----------------------------------------
        dept_map = {}
        for name, code, icon, color, desc in DEPARTMENTS:
            dept_map[code] = Department.objects.create(
                name=name, code=code, icon=icon, color=color, description=desc)

        prog_map = {}
        for name, code, dcode, level, dur in PROGRAMS:
            prog_map[code] = Program.objects.create(
                name=name, code=code, department=dept_map[dcode],
                level=level, duration_years=dur)

        # --- Admin ----------------------------------------------------------
        admin = self._make_user("admin", "System", "Administrator", Role.ADMIN)
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        self.stdout.write(self.style.SUCCESS("Admin login:  admin / demo1234"))

        # --- Faculty --------------------------------------------------------
        designations = ["Professor", "Associate Professor", "Assistant Professor"]
        faculty_list = []
        dept_codes = list(dept_map.keys())
        for i in range(10):
            fn = FIRST_NAMES[i]
            ln = random.choice(LAST_NAMES)
            uname = f"prof.{ln.lower()}" if i else "prof.rao"
            uname = self._unique_username(uname)
            fln = ("Rao" if uname == "prof.rao" else ln)
            u = self._make_user(uname, fn, fln, Role.FACULTY)
            dcode = dept_codes[i % len(dept_codes)]
            fp = FacultyProfile.objects.create(
                user=u, employee_id=f"FAC{1000 + i}", department=dept_map[dcode],
                designation=random.choice(designations),
                specialization=random.choice(
                    ["AI & ML", "Networks", "Robotics", "Finance", "Structures",
                     "Genomics", "Signal Processing", "Marketing"]),
                joining_date=date(year - random.randint(1, 12), random.randint(1, 12),
                                  random.randint(1, 28)))
            faculty_list.append(fp)
        self.stdout.write(self.style.SUCCESS("Faculty login: prof.rao / demo1234"))

        # --- Courses --------------------------------------------------------
        course_list = []
        for idx, (code, title, dcode, sem) in enumerate(COURSES):
            dept = dept_map[dcode]
            dept_faculty = [f for f in faculty_list if f.department_id == dept.id]
            faculty = random.choice(dept_faculty) if dept_faculty else random.choice(faculty_list)
            program = next((p for p in prog_map.values() if p.department_id == dept.id), None)
            course_list.append(Course.objects.create(
                code=code, title=title, department=dept, program=program,
                faculty=faculty, credits=random.choice([3, 4, 4, 5]),
                semester_no=sem,
                description=f"An in-depth study of {title.lower()} with practical labs, "
                            "projects and continuous assessment."))

        # --- Students -------------------------------------------------------
        student_list = []
        prog_codes = list(prog_map.keys())
        for i in range(45):
            fn = FIRST_NAMES[i % len(FIRST_NAMES)]
            ln = random.choice(LAST_NAMES)
            uname = f"stu.{fn.lower()}" if i else "stu.aarav"
            uname = self._unique_username(uname)
            u = self._make_user(uname, fn, ln, Role.STUDENT)
            program = prog_map[prog_codes[i % len(prog_codes)]]
            sp = StudentProfile.objects.create(
                user=u, roll_no=f"UMS{year}{i + 1:04d}", program=program,
                current_semester=random.choice([1, 3, 5, 7]),
                gender=random.choice(["M", "F", "O"]),
                date_of_birth=date(year - random.randint(18, 24),
                                   random.randint(1, 12), random.randint(1, 28)),
                admission_date=date(year, random.randint(1, 8), random.randint(1, 28)),
                guardian_name=f"{random.choice(FIRST_NAMES)} {ln}")
            student_list.append(sp)
        self.stdout.write(self.style.SUCCESS("Student login: stu.aarav / demo1234"))

        # --- Enrollments (spread across months for trend chart) -------------
        enrollments = []
        for sp in student_list:
            dept_courses = [c for c in course_list
                            if c.program_id == sp.program_id or c.department_id ==
                            (sp.program.department_id if sp.program else None)]
            if len(dept_courses) < 4:
                dept_courses = course_list
            chosen = random.sample(dept_courses, k=min(random.randint(4, 6), len(dept_courses)))
            for c in chosen:
                month = random.randint(1, today.month)
                day = random.randint(1, 28)
                e = Enrollment.objects.create(
                    student=sp, course=c, term=term,
                    enrolled_on=date(year, month, day),
                    status=Enrollment.ACTIVE)
                enrollments.append(e)

        # --- Attendance -----------------------------------------------------
        class_dates = [today - timedelta(days=d) for d in range(2, 40, 3)]
        att_objs = []
        for e in enrollments:
            for d in class_dates:
                r = random.random()
                status = (Attendance.PRESENT if r < 0.78 else
                          Attendance.LATE if r < 0.88 else Attendance.ABSENT)
                att_objs.append(Attendance(enrollment=e, date=d, status=status))
        Attendance.objects.bulk_create(att_objs, batch_size=500)

        # --- Assignments + submissions --------------------------------------
        for c in course_list:
            roster = [e.student for e in enrollments if e.course_id == c.id]
            for a_i in range(2):
                assignment = Assignment.objects.create(
                    course=c, title=f"{c.code} Assignment {a_i + 1}",
                    description="Complete the given problem set and submit your solution "
                                "with clear explanations and references.",
                    max_marks=random.choice([50, 100]),
                    assigned_on=today - timedelta(days=20 - a_i * 5),
                    due_date=today + timedelta(days=random.randint(-5, 12)))
                for sp in roster:
                    r = random.random()
                    if r < 0.5:
                        marks = random.randint(int(assignment.max_marks * 0.4),
                                               assignment.max_marks)
                        Submission.objects.create(
                            assignment=assignment, student=sp,
                            content="Submitted solution with detailed working.",
                            submitted_on=timezone.now() - timedelta(days=random.randint(1, 10)),
                            marks=marks, feedback="Well structured. Keep it up!",
                            status=Submission.GRADED)
                    elif r < 0.8:
                        Submission.objects.create(
                            assignment=assignment, student=sp,
                            content="Submitted solution, awaiting evaluation.",
                            submitted_on=timezone.now() - timedelta(days=random.randint(1, 6)),
                            status=Submission.SUBMITTED)
                    # else: leave as pending (no submission row)

        # --- Exams + results ------------------------------------------------
        for c in course_list:
            roster = [e.student for e in enrollments if e.course_id == c.id]
            for name, offset in [("Mid Term", 25), ("Final Term", 5)]:
                exam = Exam.objects.create(
                    course=c, term=term, name=name,
                    date=today - timedelta(days=offset), max_marks=100)
                for sp in roster:
                    base = random.gauss(68, 15)
                    marks = max(20, min(100, round(base)))
                    Result.objects.create(exam=exam, student=sp,
                                          marks_obtained=Decimal(marks))

        # --- Fees (spread across months for collection chart) ---------------
        for sp in student_list:
            for m_i, tuition in enumerate([45000, 42000]):
                month = random.randint(1, today.month)
                amount = Decimal(tuition)
                paid_ratio = random.choice([1.0, 1.0, 0.6, 0.5, 0.0])
                paid = (amount * Decimal(str(paid_ratio))).quantize(Decimal("1"))
                inv = FeeInvoice.objects.create(
                    student=sp, term=term,
                    title=f"Semester Tuition Fee ({'Installment ' + str(m_i + 1)})",
                    amount=amount, amount_paid=paid,
                    issued_on=date(year, month, random.randint(1, 28)),
                    due_date=date(year, min(12, month + 1), 15))
                if paid > 0:
                    Payment.objects.create(
                        invoice=inv, amount=paid, paid_on=inv.issued_on,
                        method=random.choice(["Online", "UPI", "Card", "Net Banking"]),
                        reference=f"TXN-{random.randint(100000, 999999)}")

        # --- Events & notices ----------------------------------------------
        for i, (title, desc, cat, loc, icon) in enumerate(EVENTS):
            Event.objects.create(
                title=title, description=desc, category=cat, location=loc, icon=icon,
                date=today + timedelta(days=random.randint(3, 45)))

        for title, body, aud, pinned in NOTICES:
            Notice.objects.create(title=title, body=body, audience=aud,
                                  is_pinned=pinned, created_by=admin,
                                  created_at=timezone.now() - timedelta(
                                      days=random.randint(0, 14)))

        self.stdout.write(self.style.SUCCESS(
            f"\nSeed complete! "
            f"{StudentProfile.objects.count()} students, "
            f"{FacultyProfile.objects.count()} faculty, "
            f"{Course.objects.count()} courses, "
            f"{Enrollment.objects.count()} enrollments, "
            f"{Attendance.objects.count()} attendance records."))
        self.stdout.write(self.style.WARNING(
            "\nDemo logins (password: demo1234)\n"
            "  Admin   -> admin\n  Faculty -> prof.rao\n  Student -> stu.aarav"))

    # -- helpers ------------------------------------------------------------
    def _make_user(self, username, first, last, role):
        # Drop any pre-existing account (e.g. a surviving demo superuser) so the
        # seeder is safe to re-run.
        User.objects.filter(username=username).delete()
        u = User(username=username, first_name=first, last_name=last,
                 email=f"{username}@{EMAIL_DOMAIN}", role=role, phone=PHONE)
        u.set_password(PASSWORD)
        u.save()
        return u

    def _unique_username(self, base):
        username = base
        n = 1
        while User.objects.filter(username=username).exists():
            n += 1
            username = f"{base}{n}"
        return username
