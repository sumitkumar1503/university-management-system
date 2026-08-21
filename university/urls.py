from django.urls import path

from . import views

app_name = "university"

urlpatterns = [
    # Public
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("catalog/", views.courses_public, name="courses_public"),

    # Dashboard router
    path("dashboard/", views.dashboard, name="dashboard"),

    # Admin — students
    path("manage/students/", views.admin_students, name="admin_students"),
    path("manage/students/new/", views.student_create, name="student_create"),
    path("manage/students/<int:pk>/", views.student_detail, name="student_detail"),
    path("manage/students/<int:pk>/edit/", views.student_edit, name="student_edit"),
    path("manage/students/<int:pk>/delete/", views.student_delete, name="student_delete"),

    # Admin — faculty
    path("manage/faculty/", views.admin_faculty, name="admin_faculty"),
    path("manage/faculty/new/", views.faculty_create, name="faculty_create"),
    path("manage/faculty/<int:pk>/", views.faculty_detail, name="faculty_detail"),
    path("manage/faculty/<int:pk>/edit/", views.faculty_edit, name="faculty_edit"),
    path("manage/faculty/<int:pk>/delete/", views.faculty_delete, name="faculty_delete"),

    # Admin — departments & programs
    path("manage/departments/", views.admin_departments, name="admin_departments"),
    path("manage/departments/new/", views.department_create, name="department_create"),
    path("departments/<int:pk>/", views.department_detail, name="department_detail"),
    path("manage/departments/<int:pk>/edit/", views.department_edit, name="department_edit"),
    path("manage/departments/<int:pk>/delete/", views.department_delete, name="department_delete"),
    path("manage/programs/new/", views.program_create, name="program_create"),
    path("manage/programs/<int:pk>/edit/", views.program_edit, name="program_edit"),
    path("manage/programs/<int:pk>/delete/", views.program_delete, name="program_delete"),

    # Courses (admin CRUD + enrollment)
    path("courses/", views.admin_courses, name="admin_courses"),
    path("courses/new/", views.course_create, name="course_create"),
    path("courses/<int:pk>/", views.course_detail, name="course_detail"),
    path("courses/<int:pk>/edit/", views.course_edit, name="course_edit"),
    path("courses/<int:pk>/delete/", views.course_delete, name="course_delete"),
    path("courses/<int:pk>/enroll/", views.course_enroll, name="course_enroll"),
    path("enrollments/<int:pk>/remove/", views.enrollment_remove, name="enrollment_remove"),

    # Fees
    path("manage/fees/", views.admin_fees, name="admin_fees"),
    path("manage/fees/new/", views.fee_create, name="fee_create"),
    path("manage/fees/<int:pk>/pay/", views.record_payment, name="record_payment"),

    # Notices & events
    path("notices/", views.notices, name="notices"),
    path("notices/<int:pk>/delete/", views.notice_delete, name="notice_delete"),
    path("events/", views.events, name="events"),
    path("events/new/", views.event_create, name="event_create"),
    path("events/<int:pk>/edit/", views.event_edit, name="event_edit"),
    path("events/<int:pk>/delete/", views.event_delete, name="event_delete"),

    # Faculty
    path("teach/courses/", views.faculty_courses, name="faculty_courses"),
    path("teach/attendance/<int:pk>/", views.faculty_attendance, name="faculty_attendance"),
    path("teach/attendance/<int:pk>/history/", views.faculty_attendance_history,
         name="faculty_attendance_history"),
    path("teach/assignments/", views.faculty_assignments, name="faculty_assignments"),
    path("teach/assignments/new/", views.assignment_create, name="assignment_create"),
    path("teach/assignments/<int:pk>/edit/", views.assignment_edit, name="assignment_edit"),
    path("teach/assignments/<int:pk>/delete/", views.assignment_delete, name="assignment_delete"),
    path("teach/grade/<int:pk>/", views.faculty_grade, name="faculty_grade"),
    path("assignments/<int:pk>/", views.assignment_detail, name="assignment_detail"),
    path("exams/new/", views.exam_create, name="exam_create"),
    path("exams/<int:pk>/edit/", views.exam_edit, name="exam_edit"),
    path("exams/<int:pk>/delete/", views.exam_delete, name="exam_delete"),

    # Student
    path("me/courses/", views.student_courses, name="student_courses"),
    path("me/attendance/", views.student_attendance, name="student_attendance"),
    path("me/results/", views.student_results, name="student_results"),
    path("me/assignments/", views.student_assignments, name="student_assignments"),
    path("me/assignments/<int:pk>/submit/", views.submit_assignment, name="submit_assignment"),
    path("me/fees/", views.student_fees, name="student_fees"),

    # AI
    path("ai/assistant/", views.ai_assistant, name="ai_assistant"),
    path("ai/reply/", views.ai_reply, name="ai_reply"),
    path("ai/insights/", views.ai_insights, name="ai_insights"),
]
