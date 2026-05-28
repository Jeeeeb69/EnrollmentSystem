# views.py

import logging
import smtplib

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.conf import settings
from django.core.mail import send_mail
import requests

from django.contrib.auth import get_user_model

from rest_framework import (
    viewsets,
    status,
    filters,
    generics,
    serializers
)

from rest_framework.response import Response

from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny,
    IsAdminUser
)

from rest_framework.decorators import (
    action,
    api_view,
    permission_classes,
    parser_classes
)

from rest_framework.parsers import (
    JSONParser,
    MultiPartParser,
    FormParser
)
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import (
    Student,
    Subject,
    Section,
    Enrollment
)

from .serializers import (
    StudentSerializer,
    StudentRegistrationSerializer,
    SubjectSerializer,
    SectionSerializer,
    EnrollmentSerializer,
    first_model_error,
    RegisterSerializer,
    ActivationVerifySerializer,
    ActivationResendSerializer,
    ActiveTokenObtainPairSerializer
)

from .permissions import IsAdminOrReadOnly

User = get_user_model()
logger = logging.getLogger(__name__)


def send_activation_email(user):
    using_console_email = (
        settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend'
    )

    if (
        not using_console_email
        and (not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD)
    ):
        raise ImproperlyConfigured(
            "Gmail SMTP is not configured. Set GMAIL_EMAIL and GMAIL_APP_PASSWORD."
        )

    if not user.activation_code:
        user.generate_activation_code()
        user.save(update_fields=[
            'activation_code',
            'activation_code_expires_at',
        ])

    subject = 'Student Enrollment Account Verification'
    message = (
        f'Hello,\n\n'
        f'Your Student Enrollment System verification code is: {user.activation_code}\n\n'
        f'This code expires in 15 minutes. If you did not create this account, '
        f'please ignore this email.\n'
    )

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except smtplib.SMTPAuthenticationError as exc:
        raise ImproperlyConfigured(
            "Gmail rejected the sender login. Generate a new Google App Password "
            "for the same Gmail account in GMAIL_EMAIL, then update GMAIL_APP_PASSWORD."
        ) from exc


def first_serializer_error(errors):
    if isinstance(errors, dict):
        for field, messages in errors.items():
            message = first_serializer_error(messages)
            return f"{field}: {message}" if field != "non_field_errors" else message

    if isinstance(errors, list) and errors:
        return first_serializer_error(errors[0])

    return str(errors)


def build_chatbot_context(user):
    try:
        student = Student.objects.get(user=user)
    except Student.DoesNotExist:
        student = None

    if student:
        profile = (
            f"Student: {student.full_name}; student number: "
            f"{student.student_number or 'N/A'}; course: {student.course or 'N/A'}; "
            f"year level: {student.year_level or 'N/A'}; semester: {student.semester or 'N/A'}."
        )
    elif user.is_staff:
        profile = f"User is an admin/staff account: {user.email}."
    else:
        profile = "No student profile is linked to this user."

    subjects = Subject.objects.order_by('subject_code')
    if student and not user.is_staff:
        subjects = subjects.filter(
            Q(course=student.course) | Q(course='GENERAL'),
            year_level=student.year_level,
            semester=student.semester
        )
    subject_lines = [
        (
            f"- {subject.subject_code}: {subject.subject_name}, {subject.units} unit(s), "
            f"{subject.course}, {subject.year_level}, {subject.semester}"
        )
        for subject in subjects[:12]
    ]

    sections = Section.objects.select_related('subject').order_by(
        'subject__subject_code',
        'section_name'
    )
    if student and not user.is_staff:
        sections = sections.filter(
            Q(subject__course=student.course) | Q(subject__course='GENERAL'),
            subject__year_level=student.year_level,
            subject__semester=student.semester
        )
    section_lines = [
        (
            f"- {section.subject.subject_code} section {section.section_name}: "
            f"{section.available_slots} available slot(s), room {section.room or 'N/A'}, "
            f"schedule {section.schedule or 'N/A'}"
        )
        for section in sections[:12]
    ]

    enrollments = Enrollment.objects.select_related(
        'student',
        'subject',
        'section'
    ).order_by('-created_at')
    if not user.is_staff:
        enrollments = enrollments.filter(student=student)
    enrollment_lines = [
        (
            f"- {enrollment.subject.subject_code}: {enrollment.status}, "
            f"semester {enrollment.semester}, section "
            f"{enrollment.section.section_name if enrollment.section else 'not assigned'}"
        )
        for enrollment in enrollments[:12]
    ]

    return "\n".join([
        profile,
        "Relevant subjects:",
        "\n".join(subject_lines) or "- None found.",
        "Relevant sections:",
        "\n".join(section_lines) or "- None found.",
        "Recent enrollments:",
        "\n".join(enrollment_lines) or "- None found.",
    ])


def build_chatbot_response(user, message):
    payload = {
        "model": settings.OLLAMA_CHAT_MODEL,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the Student Enrollment System assistant. Answer in a helpful, "
                    "concise way using the provided school data. If the data does not answer "
                    "the question, say so and suggest what the student can check in the app. "
                    "Do not invent subjects, enrollment statuses, rooms, schedules, or student details."
                ),
            },
            {
                "role": "system",
                "content": f"Current app data:\n{build_chatbot_context(user)}",
            },
            {
                "role": "user",
                "content": message,
            },
        ],
        "options": {
            "temperature": 0.2,
            "num_predict": 180,
        },
    }

    try:
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=settings.OLLAMA_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        logger.exception("Ollama chatbot request failed")
        return (
            "Ollama chatbot is unavailable right now. Make sure Ollama is running "
            "and the qwen2.5:0.5b model is installed."
        )
    except ValueError:
        logger.exception("Ollama chatbot returned invalid JSON")
        return "Ollama chatbot returned an invalid response."

    reply = data.get('message', {}).get('content', '').strip()
    if not reply:
        return "Ollama chatbot did not return a reply."

    return reply


def auto_enroll_student(student):
    subjects = Subject.objects.filter(
        Q(course=student.course) | Q(course='GENERAL'),
        year_level=student.year_level,
        semester=student.semester
    )

    enrollments_created = 0
    waitlisted_count = 0

    for subject in subjects:
        enrollment, created = Enrollment.objects.get_or_create(
            student=student,
            subject=subject,
            semester=subject.semester,
            defaults={'status': 'ENROLLED'}
        )

        if not created:
            continue

        enrollments_created += 1

        if enrollment.status == 'WAITLISTED':
            waitlisted_count += 1

    return enrollments_created, waitlisted_count


def auto_enroll_subject(subject):
    Section.objects.get_or_create(
        subject=subject,
        section_name='A',
        defaults={
            'max_capacity': 40,
            'current_count': 0,
            'room': '',
            'schedule': '',
        }
    )

    students = Student.objects.filter(
        course=subject.course if subject.course != 'GENERAL' else None
    ) if subject.course != 'GENERAL' else Student.objects.all()

    students = students.filter(
        year_level=subject.year_level,
        semester=subject.semester
    )

    enrollments_created = 0

    for student in students:
        _, created = Enrollment.objects.get_or_create(
            student=student,
            subject=subject,
            semester=subject.semester,
            defaults={'status': 'ENROLLED'}
        )

        if created:
            enrollments_created += 1

    return enrollments_created


# =========================================================
# REGISTER USER
# =========================================================
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    try:
        serializer = StudentRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():

            student = serializer.save()

            enrollments_created, waitlisted_count = auto_enroll_student(
                student
            )

            send_activation_email(student.user)

            return Response({
                "message": "Registration successful. Please check your email for the verification code.",
                "student_id": student.id,
                "email": student.email,
                "is_active": student.user.is_active,
                "auto_enrolled_count": enrollments_created,
                "waitlisted_count": waitlisted_count
            })

    except ValidationError as e:
        return Response({
            "error": first_model_error(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except serializers.ValidationError as e:
        return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
    except IntegrityError:
        return Response({
            "error": "Duplicate student name, student number, or email address is not allowed."
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# =========================================================
# ACCOUNT ACTIVATION
# =========================================================
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_activation_code(request):
    serializer = ActivationVerifySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    code = serializer.validated_data['code']

    try:
        user = User.objects.select_related('student_profile').get(email__iexact=email)
    except User.DoesNotExist:
        return Response(
            {"error": "Account not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if user.is_active:
        return Response({
            "message": "Account is already active.",
            "is_active": True,
        })

    if not user.activation_code_is_valid(code):
        return Response(
            {"error": "Invalid or expired verification code."},
            status=status.HTTP_400_BAD_REQUEST
        )

    user.is_active = True
    user.clear_activation_code()
    user.save(update_fields=[
        'is_active',
        'activation_code',
        'activation_code_expires_at',
    ])

    if hasattr(user, 'student_profile'):
        user.student_profile.is_active = True
        user.student_profile.save(update_fields=['is_active'])

    return Response({
        "message": "Account verified successfully. You can now log in.",
        "is_active": True,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_activation_code(request):
    serializer = ActivationResendSerializer(data=request.data)

    try:
        serializer.is_valid(raise_exception=True)
    except serializers.ValidationError as e:
        return Response({
            "error": first_serializer_error(e.detail)
        }, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email']

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response(
            {"error": "Account not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if user.is_active:
        return Response({
            "message": "Account is already active.",
            "is_active": True,
        })

    user.generate_activation_code()
    user.save(update_fields=[
        'activation_code',
        'activation_code_expires_at',
    ])
    send_activation_email(user)

    return Response({
        "message": "A new verification code has been sent to your email.",
        "is_active": False,
    })


class ActiveTokenObtainPairView(TokenObtainPairView):
    serializer_class = ActiveTokenObtainPairSerializer


# =========================================================
# STUDENTS
# =========================================================
class StudentViewSet(viewsets.ModelViewSet):

    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAdminUser]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'first_name',
        'last_name',
        'email',
        'student_number'
    ]

    ordering_fields = [
        'first_name',
        'last_name',
        'created_at'
    ]

    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_context(self):
        return {'request': self.request}

    def get_queryset(self):

        queryset = Student.objects.select_related('user').filter(
            Q(user__isnull=True) | Q(user__is_staff=False)
        ).exclude(
            first_name='',
            last_name=''
        )

        course = self.request.query_params.get('course')
        year_level = self.request.query_params.get('year_level')
        semester = self.request.query_params.get('semester')

        if course:
            queryset = queryset.filter(course=course)

        if year_level:
            queryset = queryset.filter(year_level=year_level)

        if semester:
            queryset = queryset.filter(semester=semester)

        return queryset

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def activate(self, request, pk=None):
        student = self.get_object()
        student.is_active = True
        student.save(update_fields=['is_active'])

        if student.user:
            student.user.is_active = True
            student.user.save(update_fields=['is_active'])

        return Response(StudentSerializer(student, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def deactivate(self, request, pk=None):
        student = self.get_object()
        student.is_active = False
        student.save(update_fields=['is_active'])

        if student.user:
            student.user.is_active = False
            student.user.save(update_fields=['is_active'])

        return Response(StudentSerializer(student, context={'request': request}).data)


# =========================================================
# SUBJECTS
# =========================================================
class SubjectViewSet(viewsets.ModelViewSet):

    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):

        queryset = Subject.objects.all()
        user = self.request.user

        course = self.request.query_params.get('course')
        year_level = self.request.query_params.get('year_level')
        semester = self.request.query_params.get('semester')

        if not user.is_staff:
            try:
                student = Student.objects.get(user=user)
            except Student.DoesNotExist:
                return Subject.objects.none()

            queryset = queryset.filter(
                Q(course=student.course) | Q(course='GENERAL'),
                year_level=student.year_level,
                semester=student.semester
            )

        if course:
            queryset = queryset.filter(
                Q(course=course) | Q(course='GENERAL')
            )

        if year_level:
            queryset = queryset.filter(year_level=year_level)

        if semester:
            queryset = queryset.filter(semester=semester)

        return queryset

    def perform_create(self, serializer):

        subject = serializer.save()

        auto_enroll_subject(subject)

    def perform_update(self, serializer):

        subject = serializer.save()

        auto_enroll_subject(subject)


# =========================================================
# SECTIONS
# =========================================================
class SectionViewSet(viewsets.ModelViewSet):

    queryset = Section.objects.select_related('subject').all()
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):

        queryset = Section.objects.select_related('subject').all()
        user = self.request.user
        subject = self.request.query_params.get('subject')

        if not user.is_staff:
            try:
                student = Student.objects.get(user=user)
            except Student.DoesNotExist:
                return Section.objects.none()

            queryset = queryset.filter(
                Q(subject__course=student.course)
                | Q(subject__course='GENERAL'),
                subject__year_level=student.year_level,
                subject__semester=student.semester
            )

        if subject:
            queryset = queryset.filter(subject_id=subject)

        return queryset


# =========================================================
# ENROLLMENTS
# =========================================================
class EnrollmentViewSet(viewsets.ModelViewSet):

    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):

        if self.action in ['list', 'retrieve', 'create']:
            return [IsAuthenticated()]

        return [IsAdminUser()]

    def get_queryset(self):

        user = self.request.user

        queryset = Enrollment.objects.select_related(
            'student',
            'subject',
            'section'
        )

        status_param = self.request.query_params.get('status')
        course = self.request.query_params.get('course')
        year_level = self.request.query_params.get('year_level')
        semester = self.request.query_params.get('semester')

        if not user.is_staff:
            queryset = queryset.filter(student__user=user)

        if status_param:
            queryset = queryset.filter(status=status_param)

        if course:
            queryset = queryset.filter(student__course=course)

        if year_level:
            queryset = queryset.filter(student__year_level=year_level)

        if semester:
            queryset = queryset.filter(semester=semester)

        return queryset

    def create(self, request, *args, **kwargs):

        subject_id = request.data.get('subject')

        if not subject_id:
            return Response(
                {"error": "Subject is required."},
                status=400
            )

        try:
            student = Student.objects.get(user=request.user)
            subject = Subject.objects.get(pk=subject_id)

        except Student.DoesNotExist:
            return Response(
                {"error": "Student profile not found."},
                status=404
            )

        except Subject.DoesNotExist:
            return Response(
                {"error": "Subject not found."},
                status=404
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = serializer.save(
                student=student,
                semester=subject.semester,
                status='PENDING'
            )

            return Response(
                EnrollmentSerializer(enrollment).data,
                status=201
            )

        except ValidationError as e:
            return Response(
                {"error": first_model_error(e)},
                status=400
            )

    def _update_enrollment_status(self, request, method_name):
        enrollment = self.get_object()
        remarks = request.data.get('remarks', '')
        section_id = request.data.get('section')
        section = None

        if section_id:
            try:
                section = Section.objects.get(pk=section_id)
            except Section.DoesNotExist:
                return Response(
                    {"error": "Section not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

        try:
            if method_name in ['approve', 're_enroll']:
                getattr(enrollment, method_name)(section=section, remarks=remarks)
            else:
                getattr(enrollment, method_name)(remarks=remarks)

            serializer = self.get_serializer(enrollment)
            return Response(serializer.data)

        except ValidationError as e:
            return Response(
                {"error": first_model_error(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._update_enrollment_status(request, 'approve')

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._update_enrollment_status(request, 'reject')

    @action(detail=True, methods=['post'])
    def drop(self, request, pk=None):
        return self._update_enrollment_status(request, 'drop')

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_enrollment(self, request, pk=None):
        return self._update_enrollment_status(request, 'cancel')

    @action(detail=True, methods=['post'], url_path='re-enroll')
    def re_enroll(self, request, pk=None):
        return self._update_enrollment_status(request, 're_enroll')


# =========================================================
# PROFILE
# =========================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    user = request.user

    return Response({
        "id": user.id,
        "email": user.email,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "is_active": user.is_active,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):

    try:
        student = Student.objects.select_related(
            'user'
        ).get(user=request.user)

        serializer = StudentSerializer(
            student,
            context={'request': request}
        )

        return Response(serializer.data)

    except Student.DoesNotExist:
        return Response(
            {"error": "Student profile not found."},
            status=404
        )


# =========================================================
# UPDATE PROFILE
# =========================================================
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_student_profile(request):

    try:
        student = Student.objects.get(user=request.user)

        serializer = StudentSerializer(
            student,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    except Student.DoesNotExist:
        return Response(
            {"error": "Student not found."},
            status=404
        )


# =========================================================
# PROFILE PICTURE
# =========================================================
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_profile_picture(request):

    try:
        student = Student.objects.get(user=request.user)

        image = request.FILES.get('profile_picture')

        if not image:
            return Response(
                {"error": "No image uploaded."},
                status=400
            )

        allowed_types = {
            'image/jpeg',
            'image/png',
            'image/webp',
        }

        if image.content_type not in allowed_types:
            return Response(
                {"error": "Only JPG, PNG, or WEBP images are allowed."},
                status=400
            )

        max_size = 2 * 1024 * 1024

        if image.size > max_size:
            return Response(
                {"error": "Profile picture must be 2MB or smaller."},
                status=400
            )

        student.profile_picture = image
        student.save()

        return Response({
            "message": "Profile picture updated successfully",
            "profile_picture": request.build_absolute_uri(
                student.profile_picture.url
            )
        })

    except Student.DoesNotExist:
        return Response(
            {"error": "Student not found."},
            status=404
        )


# =========================================================
# REGISTER CLASS BASED VIEW
# =========================================================
class RegisterView(generics.CreateAPIView):

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


# =========================================================
# CHATBOT
# =========================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chatbot(request):

    message = request.data.get('message', '')

    if not isinstance(message, str):
        return Response(
            {"message": ["Message must be text."]},
            status=status.HTTP_400_BAD_REQUEST
        )

    message = message.strip()

    if not message:
        return Response(
            {"message": ["Message is required."]},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(message) > 500:
        return Response(
            {"message": ["Message must be 500 characters or fewer."]},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response({
        "reply": build_chatbot_response(request.user, message)
    })
