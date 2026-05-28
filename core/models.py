import re
import secrets

from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from django.utils import timezone
from django.db.models.functions import Lower


NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]*$")
STUDENT_NUMBER_RE = re.compile(r"^[A-Za-z0-9-]{4,50}$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9 -]{6,18}$")
SUBJECT_CODE_RE = re.compile(r"^[A-Za-z0-9-]{2,20}$")
SECTION_RE = re.compile(r"^[A-Za-z0-9-]{1,50}$")


def compact_text(value):
    return " ".join(value.strip().split()) if isinstance(value, str) else value


# =========================================================
# CUSTOM USER MANAGER
# =========================================================
class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):

        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("email_verified", True)
        return self.create_user(
            email,
            password,
            **extra_fields
        )


# =========================================================
# CUSTOM USER
# =========================================================
class User(AbstractUser):

    username = None

    email = models.EmailField(
        unique=True
    )

    email_verified = models.BooleanField(
        default=False
    )

    activation_code = models.CharField(
        max_length=6,
        blank=True
    )

    activation_code_expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower('email'),
                name='unique_user_email_ci',
            ),
        ]

    def __str__(self):
        return self.email

    def generate_activation_code(self):
        self.activation_code = f"{secrets.randbelow(1000000):06d}"
        self.activation_code_expires_at = timezone.now() + timezone.timedelta(minutes=15)
        return self.activation_code

    def clear_activation_code(self):
        self.activation_code = ""
        self.activation_code_expires_at = None

    def activation_code_is_valid(self, code):
        return (
            self.activation_code
            and self.activation_code == str(code).strip()
            and self.activation_code_expires_at
            and self.activation_code_expires_at >= timezone.now()
        )


# =========================================================
# SUBJECT
# =========================================================
class Subject(models.Model):

    COURSE_CHOICES = [
        ('Information Technology', 'Information Technology'),
        ('Computer Science', 'Computer Science'),
        ('Technology Communication Management', 'Technology Communication Management'),
        ('GENERAL', 'GENERAL'),
    ]

    YEAR_CHOICES = [
        ('1st Year', '1st Year'),
        ('2nd Year', '2nd Year'),
        ('3rd Year', '3rd Year'),
        ('4th Year', '4th Year'),
    ]

    SEMESTER_CHOICES = [
        ('1st Sem', '1st Sem'),
        ('2nd Sem', '2nd Sem'),
    ]

    subject_code = models.CharField(
        max_length=20,
        unique=True
    )

    subject_name = models.CharField(
        max_length=255
    )

    description = models.TextField(
        blank=True
    )

    units = models.PositiveIntegerField()

    course = models.CharField(
        max_length=100,
        choices=COURSE_CHOICES,
        default="GENERAL"
    )

    year_level = models.CharField(
        max_length=20,
        choices=YEAR_CHOICES,
        default="1st Year"
    )

    semester = models.CharField(
        max_length=20,
        choices=SEMESTER_CHOICES,
        default="1st Sem"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['subject_code']

    def __str__(self):
        return f"{self.subject_code} - {self.subject_name}"

    def clean(self):
        self.subject_code = compact_text(self.subject_code).upper()
        self.subject_name = compact_text(self.subject_name)
        self.description = compact_text(self.description)

        errors = {}

        if not self.subject_code or not SUBJECT_CODE_RE.fullmatch(self.subject_code):
            errors["subject_code"] = (
                "Subject code must be 2-20 characters and use only letters, numbers, and hyphens."
            )

        if not self.subject_name:
            errors["subject_name"] = "Subject name is required."

        if self.units < 1 or self.units > 6:
            errors["units"] = "Units must be between 1 and 6."

        if self.description and len(self.description) > 1000:
            errors["description"] = "Description must be 1000 characters or fewer."

        if errors:
            raise ValidationError(errors)


# =========================================================
# STUDENT
# =========================================================
class Student(models.Model):

    YEAR_CHOICES = [
        ('1st Year', '1st Year'),
        ('2nd Year', '2nd Year'),
        ('3rd Year', '3rd Year'),
        ('4th Year', '4th Year'),
    ]

    COURSE_CHOICES = [
        ('Information Technology', 'Information Technology'),
        ('Computer Science', 'Computer Science'),
        ('Technology Communication Management', 'Technology Communication Management'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile',
        null=True,
        blank=True
    )

    # BASIC INFORMATION
    first_name = models.CharField(max_length=100)

    middle_name = models.CharField(
        max_length=100,
        blank=True
    )

    last_name = models.CharField(max_length=100)

    email = models.EmailField(
        unique=True
    )

    student_number = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True
    )

    parent_name = models.CharField(
        max_length=255,
        blank=True
    )

    contact_number = models.CharField(
        max_length=20,
        blank=True
    )

    home_address = models.TextField(
        blank=True
    )

    birthday = models.DateField(
        null=True,
        blank=True
    )

    course = models.CharField(
        max_length=100,
        choices=COURSE_CHOICES,
        blank=True
    )

    year_level = models.CharField(
        max_length=20,
        choices=YEAR_CHOICES,
        blank=True
    )

    semester = models.CharField(
        max_length=20,
        choices=Subject.SEMESTER_CHOICES,
        blank=True,
        null=True
    )

    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        null=True,
        blank=True
    )

    enrolled_date = models.DateField(
        auto_now_add=True
    )

    max_units = models.PositiveIntegerField(
        default=50
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['last_name', 'first_name']
        constraints = [
            models.UniqueConstraint(
                Lower('email'),
                name='unique_student_email_ci',
            ),
            models.UniqueConstraint(
                Lower('student_number'),
                condition=models.Q(student_number__isnull=False),
                name='unique_student_number_ci',
            ),
            models.UniqueConstraint(
                Lower('first_name'),
                Lower('middle_name'),
                Lower('last_name'),
                name='unique_student_full_name_ci',
            ),
        ]

    def __str__(self):
        return self.full_name

    def clean(self):
        self.first_name = compact_text(self.first_name)
        self.middle_name = compact_text(self.middle_name)
        self.last_name = compact_text(self.last_name)
        self.parent_name = compact_text(self.parent_name)
        self.student_number = compact_text(self.student_number)
        self.contact_number = compact_text(self.contact_number)
        self.home_address = compact_text(self.home_address)
        self.email = self.email.lower().strip() if self.email else self.email

        errors = {}

        for field, label in (
            ("first_name", "First name"),
            ("last_name", "Last name"),
        ):
            value = getattr(self, field)

            if not value or not NAME_RE.fullmatch(value):
                errors[field] = (
                    f"{label} may only contain letters, spaces, apostrophes, periods, and hyphens."
                )

        for field, label in (
            ("middle_name", "Middle name"),
            ("parent_name", "Parent name"),
        ):
            value = getattr(self, field)

            if value and not NAME_RE.fullmatch(value):
                errors[field] = (
                    f"{label} may only contain letters, spaces, apostrophes, periods, and hyphens."
                )

        if self.student_number:
            if not STUDENT_NUMBER_RE.fullmatch(self.student_number):
                errors["student_number"] = (
                    "Student number must be 4-50 characters and use only letters, numbers, and hyphens."
                )
            else:
                self.student_number = self.student_number.upper()

        if self.contact_number and not PHONE_RE.fullmatch(self.contact_number):
            errors["contact_number"] = (
                "Contact number must be 7-19 digits and may include spaces, hyphens, or a leading plus."
            )

        if self.home_address and len(self.home_address) > 500:
            errors["home_address"] = "Home address must be 500 characters or fewer."

        if self.birthday:
            today = timezone.now().date()

            if self.birthday > today:
                errors["birthday"] = "Birthday cannot be in the future."
            else:
                age = (
                    today.year
                    - self.birthday.year
                    - ((today.month, today.day) < (self.birthday.month, self.birthday.day))
                )

                if age < 15:
                    errors["birthday"] = "Student must be at least 15 years old."
                elif age > 100:
                    errors["birthday"] = "Birthday is outside the allowed range."

        if self.max_units < 1 or self.max_units > 50:
            errors["max_units"] = "Max units must be between 1 and 50."

        if errors:
            raise ValidationError(errors)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def calculated_age(self):

        if not self.birthday:
            return None

        today = timezone.now().date()

        return (
            today.year
            - self.birthday.year
            - (
                (today.month, today.day)
                < (self.birthday.month, self.birthday.day)
            )
        )

    @property
    def total_units(self):

        enrollments = self.enrollments.filter(
            status='ENROLLED'
        ).select_related(
            'subject'
        )

        return sum(
            enrollment.subject.units
            for enrollment in enrollments
            if enrollment.subject
        )


# =========================================================
# SECTION
# =========================================================
class Section(models.Model):

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='sections'
    )

    section_name = models.CharField(
        max_length=50
    )

    max_capacity = models.PositiveIntegerField()

    current_count = models.PositiveIntegerField(
        default=0
    )

    room = models.CharField(
        max_length=100,
        blank=True
    )

    schedule = models.CharField(
        max_length=255,
        blank=True
    )

    class Meta:
        unique_together = ('subject', 'section_name')
        ordering = ['section_name']

    def __str__(self):
        return f"{self.subject.subject_code} - {self.section_name}"

    def clean(self):
        self.section_name = compact_text(self.section_name).upper()
        self.room = compact_text(self.room)
        self.schedule = compact_text(self.schedule)

        errors = {}

        if not self.section_name or not SECTION_RE.fullmatch(self.section_name):
            errors["section_name"] = (
                "Section name must be 1-50 characters and use only letters, numbers, and hyphens."
            )

        if self.max_capacity < 1 or self.max_capacity > 100:
            errors["max_capacity"] = "Max capacity must be between 1 and 100."

        if self.current_count > self.max_capacity:
            errors["current_count"] = "Current count cannot exceed max capacity."

        if errors:
            raise ValidationError(errors)

    @property
    def available_slots(self):
        return self.max_capacity - self.current_count

    def has_slot(self):
        return self.current_count < self.max_capacity


# =========================================================
# ENROLLMENT
# =========================================================
class Enrollment(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('ENROLLED', 'Enrolled'),
        ('REJECTED', 'Rejected'),
        ('DROPPED', 'Dropped'),
        ('CANCELLED', 'Cancelled'),
        ('WAITLISTED', 'Waitlisted'),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )

    section = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enrollments'
    )

    semester = models.CharField(
        max_length=20,
        choices=Subject.SEMESTER_CHOICES
    )

    enrollment_date = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    remarks = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        unique_together = ('student', 'subject', 'semester')
        ordering = ['-created_at']

    def clean(self):

        # SEMESTER AUTO ASSIGN
        if self.subject and not self.semester:
            self.semester = self.subject.semester

        existing = Enrollment.objects.filter(
            student=self.student,
            subject=self.subject,
            semester=self.semester
        ).exclude(pk=self.pk)

        if existing.exists():
            raise ValidationError(
                "Student already has an enrollment record for this subject and semester."
            )

        # COURSE VALIDATION
        if (
            self.subject.course != "GENERAL"
            and self.student.course != self.subject.course
        ):
            raise ValidationError(
                "Student course does not match subject course."
            )

        # YEAR VALIDATION
        if (
            self.student.year_level
            != self.subject.year_level
        ):
            raise ValidationError(
                "Student year level does not match subject year level."
            )

        # SEMESTER VALIDATION
        if (
            self.student.semester
            and self.student.semester != self.subject.semester
        ):
            raise ValidationError(
                "Student semester does not match."
            )

        if (
            self.section
            and self.section.subject_id != self.subject_id
        ):
            raise ValidationError(
                "Section does not belong to the selected subject."
            )

        # UNIT VALIDATION
        if self.status == "ENROLLED":

            enrolled_subjects = self.student.enrollments.filter(
                status='ENROLLED'
            ).exclude(pk=self.pk).select_related('subject')

            current_units = sum(
                enrollment.subject.units
                for enrollment in enrolled_subjects
                if enrollment.subject
            )

            if self.subject:
                current_units += self.subject.units

            if current_units > self.student.max_units:
                raise ValidationError(
                    f"Maximum allowed units is {self.student.max_units}."
                )

    def assign_section(self):

        sections = Section.objects.filter(
            subject=self.subject
        ).order_by('current_count')

        for section in sections:

            if section.has_slot():
                return section

        return None

    def approve(self, section=None, remarks=''):
        if section is not None:
            self.section = section
        self.status = 'ENROLLED'
        if remarks:
            self.remarks = remarks
        self.save()

    def reject(self, remarks=''):
        self.status = 'REJECTED'
        if remarks:
            self.remarks = remarks
        self.save()

    def drop(self, remarks=''):
        self.status = 'DROPPED'
        if remarks:
            self.remarks = remarks
        self.save()

    def cancel(self, remarks=''):
        self.status = 'CANCELLED'
        if remarks:
            self.remarks = remarks
        self.save()

    def re_enroll(self, section=None, remarks=''):
        self.approve(section=section, remarks=remarks)

    @staticmethod
    def _decrement_section(section_id):
        if not section_id:
            return

        section = Section.objects.select_for_update().get(pk=section_id)
        section.current_count = max(section.current_count - 1, 0)
        section.save(update_fields=['current_count'])

    def save(self, *args, **kwargs):

        is_new = self.pk is None

        with transaction.atomic():
            old_status = None
            old_section_id = None

            if not is_new:
                old = Enrollment.objects.select_for_update().get(pk=self.pk)
                old_status = old.status
                old_section_id = old.section_id

            if self.subject and not self.semester:
                self.semester = self.subject.semester

            if self.status == "ENROLLED":

                section = self.section or self.assign_section()

                if section:

                    section = Section.objects.select_for_update().get(
                        pk=section.pk
                    )

                    if old_status == "ENROLLED" and old_section_id == section.pk:
                        self.section = section

                    elif section.has_slot():

                        self.section = section

                        section.current_count += 1
                        section.save(update_fields=['current_count'])

                    else:

                        self.section = None
                        self.status = "WAITLISTED"

                else:

                    self.status = "WAITLISTED"

            self.full_clean()

            super().save(*args, **kwargs)

            if (
                old_status == "ENROLLED"
                and old_section_id
                and (
                    self.status != "ENROLLED"
                    or self.section_id != old_section_id
                )
            ):
                self._decrement_section(old_section_id)
