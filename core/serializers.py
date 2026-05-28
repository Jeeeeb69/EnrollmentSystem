import re

from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    Student,
    Subject,
    Section,
    Enrollment
)

User = get_user_model()

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]*$")
STUDENT_NUMBER_RE = re.compile(r"^[A-Za-z0-9-]{4,50}$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9 -]{6,18}$")
SUBJECT_CODE_RE = re.compile(r"^[A-Za-z0-9-]{2,20}$")
SECTION_RE = re.compile(r"^[A-Za-z0-9-]{1,50}$")


def normalize_text(value):
    if isinstance(value, str):
        return " ".join(value.strip().split())
    return value


def validate_name(value, field_name):
    value = normalize_text(value)

    if not value:
        raise serializers.ValidationError(f"{field_name} is required.")

    if len(value) > 100 or not NAME_RE.fullmatch(value):
        raise serializers.ValidationError(
            f"{field_name} may only contain letters, spaces, apostrophes, periods, and hyphens."
        )

    return value


def validate_optional_name(value, field_name):
    value = normalize_text(value)

    if value and (len(value) > 255 or not NAME_RE.fullmatch(value)):
        raise serializers.ValidationError(
            f"{field_name} may only contain letters, spaces, apostrophes, periods, and hyphens."
        )

    return value


def validate_birthdate(value):
    if not value:
        return value

    today = timezone.now().date()

    if value > today:
        raise serializers.ValidationError("Birthday cannot be in the future.")

    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))

    if age < 15:
        raise serializers.ValidationError("Student must be at least 15 years old.")

    if age > 100:
        raise serializers.ValidationError("Birthday is outside the allowed range.")

    return value


def first_model_error(error):
    if hasattr(error, "message_dict"):
        messages = []
        for field, field_messages in error.message_dict.items():
            messages.append(f"{field}: {field_messages[0]}")
        return messages[0] if messages else "Invalid data."

    return error.messages[0] if hasattr(error, "messages") else str(error)


def student_name_exists(first_name, middle_name, last_name, instance=None):
    queryset = Student.objects.filter(
        first_name__iexact=first_name,
        middle_name__iexact=middle_name or "",
        last_name__iexact=last_name,
    )

    if instance:
        queryset = queryset.exclude(pk=instance.pk)

    return queryset.exists()

# =========================================================
# STUDENT SERIALIZER
# =========================================================
class StudentSerializer(serializers.ModelSerializer):

    full_name = serializers.ReadOnlyField()
    calculated_age = serializers.ReadOnlyField()
    total_units = serializers.ReadOnlyField()

    # FULL IMAGE URL
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = Student

        fields = [
            'id',

            'first_name',
            'middle_name',
            'last_name',
            'full_name',

            'email',
            'student_number',

            'parent_name',
            'contact_number',
            'home_address',

            'birthday',
            'calculated_age',

            'course',
            'year_level',
            'semester',

            'profile_picture',

            'max_units',
            'total_units',

            'is_active',
            'enrolled_date',

            'created_at',
            'updated_at',
        ]

    # =====================================================
    # RETURN FULL IMAGE URL
    # =====================================================
    def get_profile_picture(self, obj):

        request = self.context.get('request')

        if obj.profile_picture:

            if request:
                return request.build_absolute_uri(
                    obj.profile_picture.url
                )

            return obj.profile_picture.url

        return None

    # =====================================================
    # VALIDATE EMAIL
    # =====================================================
    def validate_email(self, value):
        value = User.objects.normalize_email(value).lower()

        queryset = Student.objects.filter(
            email__iexact=value
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():

            raise serializers.ValidationError(
                "Student email already exists."
            )

        return value

    def validate_first_name(self, value):
        return validate_name(value, "First name")

    def validate_middle_name(self, value):
        return validate_optional_name(value, "Middle name")

    def validate_last_name(self, value):
        return validate_name(value, "Last name")

    def validate_parent_name(self, value):
        return validate_optional_name(value, "Parent name")

    def validate_student_number(self, value):
        value = normalize_text(value)

        if not value:
            return value

        if not STUDENT_NUMBER_RE.fullmatch(value):
            raise serializers.ValidationError(
                "Student number must be 4-50 characters and use only letters, numbers, and hyphens."
            )

        queryset = Student.objects.filter(student_number__iexact=value)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError("Student number already exists.")

        return value.upper()

    def validate_contact_number(self, value):
        value = normalize_text(value)

        if value and not PHONE_RE.fullmatch(value):
            raise serializers.ValidationError(
                "Contact number must be 7-19 digits and may include spaces, hyphens, or a leading plus."
            )

        return value

    def validate_home_address(self, value):
        value = normalize_text(value)

        if value and len(value) > 500:
            raise serializers.ValidationError("Home address must be 500 characters or fewer.")

        return value

    def validate_birthday(self, value):
        return validate_birthdate(value)

    def validate_max_units(self, value):
        if value < 1 or value > 50:
            raise serializers.ValidationError("Max units must be between 1 and 50.")

        return value

    def validate(self, attrs):
        first_name = attrs.get("first_name", getattr(self.instance, "first_name", ""))
        middle_name = attrs.get("middle_name", getattr(self.instance, "middle_name", ""))
        last_name = attrs.get("last_name", getattr(self.instance, "last_name", ""))

        if (
            first_name
            and last_name
            and student_name_exists(first_name, middle_name, last_name, self.instance)
        ):
            raise serializers.ValidationError({
                "non_field_errors": "A student with this full name already exists."
            })

        return attrs


# =========================================================
# REGISTER SERIALIZER
# =========================================================
class RegisterSerializer(serializers.ModelSerializer):

    class Meta:
        model = User

        fields = [
            'id',
            'email',
            'password'
        ]

        extra_kwargs = {
            'password': {
                'write_only': True
            }
        }

    def validate_email(self, value):
        value = User.objects.normalize_email(value).lower()

        if User.objects.filter(
            email__iexact=value
        ).exists():

            raise serializers.ValidationError(
                "Email already exists."
            )

        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)

        return value

    def create(self, validated_data):

        return User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password']
        )


# =========================================================
# STUDENT REGISTRATION SERIALIZER
# =========================================================
class StudentRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=100)
    middle_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100)
    student_number = serializers.CharField(max_length=50)
    parent_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    contact_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    home_address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    birthday = serializers.DateField(required=False, allow_null=True)
    course = serializers.ChoiceField(choices=Student.COURSE_CHOICES)
    year_level = serializers.ChoiceField(choices=Student.YEAR_CHOICES)
    semester = serializers.ChoiceField(choices=Subject.SEMESTER_CHOICES)

    def validate_email(self, value):
        value = User.objects.normalize_email(value).lower()

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already exists.")

        if Student.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Student email already exists.")

        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)

        return value

    def validate_first_name(self, value):
        return validate_name(value, "First name")

    def validate_middle_name(self, value):
        return validate_optional_name(value, "Middle name")

    def validate_last_name(self, value):
        return validate_name(value, "Last name")

    def validate_parent_name(self, value):
        return validate_optional_name(value, "Parent name")

    def validate_student_number(self, value):
        value = normalize_text(value)

        if not STUDENT_NUMBER_RE.fullmatch(value):
            raise serializers.ValidationError(
                "Student number must be 4-50 characters and use only letters, numbers, and hyphens."
            )

        if Student.objects.filter(student_number__iexact=value).exists():
            raise serializers.ValidationError("Student number already exists.")

        return value.upper()

    def validate_contact_number(self, value):
        value = normalize_text(value)

        if value and not PHONE_RE.fullmatch(value):
            raise serializers.ValidationError(
                "Contact number must be 7-19 digits and may include spaces, hyphens, or a leading plus."
            )

        return value

    def validate_home_address(self, value):
        return normalize_text(value)

    def validate_birthday(self, value):
        return validate_birthdate(value)

    def validate(self, attrs):
        if student_name_exists(
            attrs.get("first_name"),
            attrs.get("middle_name", ""),
            attrs.get("last_name"),
        ):
            raise serializers.ValidationError({
                "non_field_errors": "A student with this full name already exists."
            })

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")

        user = User.objects.create_user(
            email=validated_data["email"],
            password=password,
            is_active=False,
            email_verified=False,
        )

        user.generate_activation_code()
        user.save(update_fields=[
            "activation_code",
            "activation_code_expires_at",
            "is_active",
            "email_verified",
        ])

        return Student.objects.create(
            user=user,
            is_active=False,
            **validated_data
        )


# =========================================================
# ACCOUNT ACTIVATION SERIALIZERS
# =========================================================
class ActivationVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_email(self, value):
        return User.objects.normalize_email(value).lower()

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Activation code must contain 6 digits.")

        return value


class ActivationResendSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return User.objects.normalize_email(value).lower()


class ActiveTokenObtainPairSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        "email_not_verified": "Please verify your email first using the code sent to your Gmail account.",
        "pending_admin_activation": "Email verified. Please wait until the admin activates your account.",
    }

    def validate(self, attrs):
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            "password": attrs["password"],
        }
        request = self.context.get("request")

        if request:
            authenticate_kwargs["request"] = request

        self.user = authenticate(**authenticate_kwargs)

        if self.user is None:
            email = User.objects.normalize_email(attrs[self.username_field]).lower()
            user = User.objects.filter(email__iexact=email).first()

            if user and user.check_password(attrs["password"]) and not user.is_active:
                message_key = (
                    "pending_admin_activation"
                    if user.email_verified
                    else "email_not_verified"
                )
                raise AuthenticationFailed(
                    self.error_messages[message_key],
                    code=message_key
                )

        return super().validate(attrs)


# =========================================================
# SUBJECT SERIALIZER
# =========================================================
class SubjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subject
        fields = '__all__'

    def validate_subject_code(self, value):
        value = normalize_text(value).upper()

        if not SUBJECT_CODE_RE.fullmatch(value):
            raise serializers.ValidationError(
                "Subject code must be 2-20 characters and use only letters, numbers, and hyphens."
            )

        queryset = Subject.objects.filter(subject_code__iexact=value)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError("Subject code already exists.")

        return value

    def validate_subject_name(self, value):
        value = normalize_text(value)

        if not value:
            raise serializers.ValidationError("Subject name is required.")

        if len(value) > 255:
            raise serializers.ValidationError("Subject name must be 255 characters or fewer.")

        return value

    def validate_description(self, value):
        value = normalize_text(value)

        if value and len(value) > 1000:
            raise serializers.ValidationError("Description must be 1000 characters or fewer.")

        return value

    def validate_units(self, value):
        if value < 1 or value > 6:
            raise serializers.ValidationError("Units must be between 1 and 6.")

        return value


# =========================================================
# SECTION SERIALIZER
# =========================================================
class SectionSerializer(serializers.ModelSerializer):
    subject_code = serializers.CharField(
        source='subject.subject_code',
        read_only=True
    )

    subject_name = serializers.CharField(
        source='subject.subject_name',
        read_only=True
    )

    class Meta:
        model = Section
        fields = [
            'id',
            'subject',
            'subject_code',
            'subject_name',
            'section_name',
            'max_capacity',
            'current_count',
            'room',
            'schedule',
        ]

    def validate_section_name(self, value):
        value = normalize_text(value).upper()

        if not SECTION_RE.fullmatch(value):
            raise serializers.ValidationError(
                "Section name must be 1-50 characters and use only letters, numbers, and hyphens."
            )

        return value

    def validate_max_capacity(self, value):
        if value < 1 or value > 100:
            raise serializers.ValidationError("Max capacity must be between 1 and 100.")

        return value

    def validate_current_count(self, value):
        if value < 0:
            raise serializers.ValidationError("Current count cannot be negative.")

        return value

    def validate(self, attrs):
        subject = attrs.get("subject", getattr(self.instance, "subject", None))
        section_name = attrs.get("section_name", getattr(self.instance, "section_name", None))
        max_capacity = attrs.get("max_capacity", getattr(self.instance, "max_capacity", None))
        current_count = attrs.get("current_count", getattr(self.instance, "current_count", 0))

        if max_capacity is not None and current_count is not None and current_count > max_capacity:
            raise serializers.ValidationError({
                "current_count": "Current count cannot exceed max capacity."
            })

        if subject and section_name:
            queryset = Section.objects.filter(
                subject=subject,
                section_name__iexact=section_name
            )

            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError({
                    "section_name": "Section already exists for this subject."
                })

        return attrs


# =========================================================
# ENROLLMENT SERIALIZER
# =========================================================
class EnrollmentSerializer(serializers.ModelSerializer):

    student_name = serializers.CharField(
        source='student.full_name',
        read_only=True
    )

    subject_name = serializers.CharField(
        source='subject.subject_name',
        read_only=True
    )

    section_name = serializers.CharField(
        source='section.section_name',
        read_only=True
    )

    class Meta:
        model = Enrollment
        fields = '__all__'
        read_only_fields = [
            'student',
            'semester',
            'status',
            'remarks',
            'enrollment_date',
            'created_at',
            'updated_at',
        ]

    def validate_subject(self, value):
        request = self.context.get("request")

        if request and request.user and not request.user.is_staff:
            try:
                student = Student.objects.get(user=request.user)
            except Student.DoesNotExist:
                raise serializers.ValidationError("Student profile not found.")

            if value.course != "GENERAL" and student.course != value.course:
                raise serializers.ValidationError("Subject is not available for your course.")

            if student.year_level != value.year_level:
                raise serializers.ValidationError("Subject is not available for your year level.")

            if student.semester and student.semester != value.semester:
                raise serializers.ValidationError("Subject is not available for your semester.")

        return value

    def validate(self, attrs):
        subject = attrs.get("subject", getattr(self.instance, "subject", None))
        section = attrs.get("section", getattr(self.instance, "section", None))

        if section and subject and section.subject_id != subject.id:
            raise serializers.ValidationError({
                "section": "Section does not belong to the selected subject."
            })

        return attrs
