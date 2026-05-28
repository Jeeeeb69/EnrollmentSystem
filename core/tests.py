from datetime import date
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher
from django.core.exceptions import ValidationError
from django.core import mail
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Enrollment, Section, Student, Subject
from .serializers import StudentRegistrationSerializer, SubjectSerializer


User = get_user_model()


class ValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="student@example.com",
            password="StrongPass123"
        )

        self.student = Student.objects.create(
            user=self.user,
            email="student@example.com",
            first_name="Juan",
            last_name="Dela Cruz",
            student_number="STU-1001",
            birthday=date(2000, 1, 1),
            course="Information Technology",
            year_level="1st Year",
            semester="1st Sem",
        )

        self.subject = Subject.objects.create(
            subject_code="IT101",
            subject_name="Programming 1",
            units=3,
            course="Information Technology",
            year_level="1st Year",
            semester="1st Sem",
        )

    def test_registration_rejects_weak_password_and_bad_phone(self):
        serializer = StudentRegistrationSerializer(data={
            "email": "newstudent@example.com",
            "password": "12345678",
            "first_name": "Maria",
            "last_name": "Santos",
            "student_number": "STU-1002",
            "contact_number": "abc",
            "birthday": "2001-01-01",
            "course": "Information Technology",
            "year_level": "1st Year",
            "semester": "1st Sem",
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)
        self.assertIn("contact_number", serializer.errors)

    def valid_registration_payload(self, **overrides):
        payload = {
            "email": "unique@example.com",
            "password": "StrongPass123!",
            "first_name": "Maria",
            "middle_name": "",
            "last_name": "Santos",
            "student_number": "STU-1002",
            "birthday": "2001-01-01",
            "course": "Information Technology",
            "year_level": "1st Year",
            "semester": "1st Sem",
        }
        payload.update(overrides)
        return payload

    def test_registration_rejects_duplicate_email_ignoring_case(self):
        serializer = StudentRegistrationSerializer(data=self.valid_registration_payload(
            email="STUDENT@EXAMPLE.COM",
            student_number="STU-1003",
        ))

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_registration_rejects_duplicate_student_number_ignoring_case(self):
        serializer = StudentRegistrationSerializer(data=self.valid_registration_payload(
            student_number="stu-1001",
        ))

        self.assertFalse(serializer.is_valid())
        self.assertIn("student_number", serializer.errors)

    def test_registration_rejects_duplicate_full_name_ignoring_case(self):
        serializer = StudentRegistrationSerializer(data=self.valid_registration_payload(
            email="another@example.com",
            first_name="juan",
            last_name="DELA CRUZ",
            student_number="STU-1004",
        ))

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_register_endpoint_rejects_duplicate_email_student_number_and_name(self):
        client = APIClient()

        duplicate_cases = [
            (
                {"email": "STUDENT@EXAMPLE.COM", "student_number": "STU-1003"},
                "email",
            ),
            (
                {"email": "student-number-check@example.com", "student_number": "stu-1001"},
                "student_number",
            ),
            (
                {
                    "email": "student-name-check@example.com",
                    "first_name": "juan",
                    "last_name": "DELA CRUZ",
                    "student_number": "STU-1004",
                },
                "non_field_errors",
            ),
        ]

        for overrides, expected_field in duplicate_cases:
            response = client.post(
                "/api/auth/register/",
                self.valid_registration_payload(**overrides),
                format="json"
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn(expected_field, response.data)

    def test_database_rejects_duplicate_student_identity_ignoring_case(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Student.objects.create(
                email="case-student@example.com",
                first_name="Case",
                last_name="Check",
                student_number="STU-9001",
                birthday=date(2000, 1, 1),
                course="Information Technology",
                year_level="1st Year",
                semester="1st Sem",
            )
            Student.objects.create(
                email="other-case-student@example.com",
                first_name="case",
                last_name="CHECK",
                student_number="STU-9002",
                birthday=date(2000, 1, 1),
                course="Information Technology",
                year_level="1st Year",
                semester="1st Sem",
            )

    def test_subject_serializer_rejects_invalid_units(self):
        serializer = SubjectSerializer(data={
            "subject_code": "IT999",
            "subject_name": "Too Many Units",
            "units": 9,
            "course": "Information Technology",
            "year_level": "1st Year",
            "semester": "1st Sem",
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("units", serializer.errors)

    def test_section_rejects_count_above_capacity(self):
        section = Section(
            subject=self.subject,
            section_name="A",
            max_capacity=10,
            current_count=11,
        )

        with self.assertRaises(ValidationError):
            section.full_clean()

    def test_enrollment_rejects_course_mismatch(self):
        subject = Subject.objects.create(
            subject_code="CS101",
            subject_name="Computer Science Intro",
            units=3,
            course="Computer Science",
            year_level="1st Year",
            semester="1st Sem",
        )

        enrollment = Enrollment(
            student=self.student,
            subject=subject,
            semester=subject.semester,
        )

        with self.assertRaises(ValidationError):
            enrollment.full_clean()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccountActivationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.payload = {
            "email": "activate@example.com",
            "password": "StrongPass123!",
            "first_name": "Mika",
            "middle_name": "",
            "last_name": "Rivera",
            "student_number": "STU-7001",
            "birthday": "2001-01-01",
            "course": "Information Technology",
            "year_level": "1st Year",
            "semester": "1st Sem",
        }

    def test_registration_requires_email_verification_and_admin_activation_before_login(self):
        register_response = self.client.post(
            "/api/auth/register/",
            self.payload,
            format="json"
        )

        self.assertEqual(register_response.status_code, 200, register_response.data)
        self.assertFalse(register_response.data["is_active"])
        self.assertEqual(len(mail.outbox), 1)

        user = User.objects.get(email="activate@example.com")
        student = Student.objects.get(email="activate@example.com")
        self.assertFalse(user.email_verified)
        self.assertFalse(user.is_active)
        self.assertFalse(student.is_active)

        login_response = self.client.post(
            "/api/auth/login/",
            {
                "email": self.payload["email"],
                "password": self.payload["password"],
            },
            format="json"
        )

        self.assertEqual(login_response.status_code, 401, login_response.data)
        self.assertIn("verify your email", login_response.data["detail"].lower())

        verify_response = self.client.post(
            "/api/auth/verify/",
            {
                "email": self.payload["email"],
                "code": user.activation_code,
            },
            format="json"
        )

        self.assertEqual(verify_response.status_code, 200)

        user.refresh_from_db()
        student.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertFalse(user.is_active)
        self.assertFalse(student.is_active)

        login_response = self.client.post(
            "/api/auth/login/",
            {
                "email": self.payload["email"],
                "password": self.payload["password"],
            },
            format="json"
        )

        self.assertEqual(login_response.status_code, 401, login_response.data)
        self.assertIn("admin activates", login_response.data["detail"].lower())

        student.is_active = True
        student.save(update_fields=["is_active"])
        user.is_active = True
        user.save(update_fields=["is_active"])

        login_response = self.client.post(
            "/api/auth/login/",
            {
                "email": self.payload["email"],
                "password": self.payload["password"],
            },
            format="json"
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertIn("access", login_response.data)


class ChatbotTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="chat@example.com",
            password="StrongPass123"
        )
        self.student = Student.objects.create(
            user=self.user,
            email="chat@example.com",
            first_name="Ana",
            last_name="Reyes",
            student_number="STU-2001",
            birthday=date(2000, 1, 1),
            course="Information Technology",
            year_level="1st Year",
            semester="1st Sem",
        )
        self.subject = Subject.objects.create(
            subject_code="IT102",
            subject_name="Web Development",
            units=3,
            course="Information Technology",
            year_level="1st Year",
            semester="1st Sem",
        )

    def test_chatbot_requires_authentication(self):
        response = self.client.post("/api/chatbot/", {"message": "hello"})

        self.assertEqual(response.status_code, 401)

    def test_chatbot_rejects_empty_message(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post("/api/chatbot/", {"message": "   "})

        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    @patch("core.views.requests.post")
    def test_chatbot_uses_ollama_for_subject_questions(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {
            "message": {
                "content": "IT102 - Web Development is available."
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/chatbot/",
            {"message": "What subjects are available?"},
            format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("IT102", response.data["reply"])
        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "qwen2.5:0.5b")
        self.assertIn("IT102", payload["messages"][1]["content"])


class SecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="security-admin@example.com",
            password="StrongPass123"
        )
        self.user = User.objects.create_user(
            email="secure@example.com",
            password="StrongPass123"
        )
        self.student = Student.objects.create(
            user=self.user,
            email="secure@example.com",
            first_name="Nico",
            last_name="Santos",
            student_number="STU-4001",
            birthday=date(2000, 1, 1),
            course="Information Technology",
            year_level="1st Year",
            semester="1st Sem",
        )

    def test_password_is_hashed(self):
        self.assertNotEqual(self.user.password, "StrongPass123")
        self.assertTrue(self.user.check_password("StrongPass123"))
        self.assertIsNotNone(identify_hasher(self.user.password))

    def test_protected_api_requires_authentication(self):
        protected_urls = [
            "/api/profile/",
            "/api/students/",
            "/api/subjects/",
            "/api/sections/",
            "/api/enrollments/",
            "/api/chatbot/",
        ]

        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 401, url)

    def test_authenticated_user_can_access_profile(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/profile/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "secure@example.com")

    def test_authenticated_user_can_check_role(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_staff"])

    def test_student_directory_requires_admin(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/students/")

        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_student_directory(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/students/")

        self.assertEqual(response.status_code, 200)


class EnrollmentWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="StrongPass123"
        )
        self.user = User.objects.create_user(
            email="workflow@example.com",
            password="StrongPass123"
        )
        self.student = Student.objects.create(
            user=self.user,
            email="workflow@example.com",
            first_name="Lia",
            last_name="Garcia",
            student_number="STU-5001",
            birthday=date(2000, 1, 1),
            course="Information Technology",
            year_level="1st Year",
            semester="1st Sem",
        )
        self.subject = Subject.objects.create(
            subject_code="IT201",
            subject_name="Data Structures",
            units=3,
            course="Information Technology",
            year_level="1st Year",
            semester="1st Sem",
        )
        self.section = Section.objects.create(
            subject=self.subject,
            section_name="A",
            max_capacity=2,
            current_count=0,
            schedule="MWF 9:00-10:00",
            room="101",
        )

    def test_student_enrollment_request_starts_pending(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/enrollments/",
            {"subject": self.subject.id},
            format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "PENDING")
        self.section.refresh_from_db()
        self.assertEqual(self.section.current_count, 0)

    def test_admin_can_approve_and_drop_enrollment(self):
        enrollment = Enrollment.objects.create(
            student=self.student,
            subject=self.subject,
            semester=self.subject.semester,
            status="PENDING",
        )
        self.client.force_authenticate(user=self.admin)

        approve_response = self.client.post(
            f"/api/enrollments/{enrollment.id}/approve/",
            {},
            format="json"
        )

        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.data["status"], "ENROLLED")
        self.section.refresh_from_db()
        self.assertEqual(self.section.current_count, 1)

        drop_response = self.client.post(
            f"/api/enrollments/{enrollment.id}/drop/",
            {"remarks": "Student requested cancellation."},
            format="json"
        )

        self.assertEqual(drop_response.status_code, 200)
        self.assertEqual(drop_response.data["status"], "DROPPED")
        self.section.refresh_from_db()
        self.assertEqual(self.section.current_count, 0)

    def test_student_cannot_approve_enrollment(self):
        enrollment = Enrollment.objects.create(
            student=self.student,
            subject=self.subject,
            semester=self.subject.semester,
            status="PENDING",
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            f"/api/enrollments/{enrollment.id}/approve/",
            {},
            format="json"
        )

        self.assertEqual(response.status_code, 403)
