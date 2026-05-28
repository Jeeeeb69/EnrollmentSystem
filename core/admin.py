import csv

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.http import HttpResponse
from django import forms

from .models import User, Student, Subject, Section, Enrollment


# =====================================
# USER CREATION FORM
# =====================================
class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('email',)

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match")

        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()

        return user


# =====================================
# USER CHANGE FORM
# =====================================
class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ('email', 'password', 'email_verified', 'is_active', 'is_staff')


# =====================================
# CUSTOM USER ADMIN
# =====================================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('email', 'email_verified', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    list_filter = ('email_verified', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    actions = ['activate_accounts', 'deactivate_accounts']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {
            'fields': (
                'is_active',
                'email_verified',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'
            )
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'password1',
                'password2',
                'is_staff',
                'is_superuser'
            ),
        }),
    )

    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions')

    @admin.action(description='Activate selected accounts')
    def activate_accounts(self, request, queryset):
        updated = queryset.update(is_active=True, email_verified=True)
        self.message_user(request, f'{updated} account(s) activated.', messages.SUCCESS)

    @admin.action(description='Deactivate selected accounts')
    def deactivate_accounts(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} account(s) deactivated.', messages.SUCCESS)


# =====================================
# STUDENT ADMIN
# =====================================
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'student_number',
        'full_name',
        'email',
        'course',
        'year_level',
        'semester',
        'is_active',
        'total_units',
        'latest_enrollment_status',
    )
    search_fields = (
        'first_name',
        'middle_name',
        'last_name',
        'email',
        'student_number',
        'contact_number',
    )
    list_filter = ('is_active', 'course', 'year_level', 'semester', 'created_at')
    readonly_fields = ('full_name', 'calculated_age', 'total_units', 'created_at', 'updated_at')
    actions = ['activate_students', 'deactivate_students', 'export_student_records']

    fieldsets = (
        ('Account', {
            'fields': ('user', 'email', 'student_number', 'is_active')
        }),
        ('Profile', {
            'fields': (
                'first_name',
                'middle_name',
                'last_name',
                'full_name',
                'profile_picture',
                'birthday',
                'calculated_age',
            )
        }),
        ('Contact Information', {
            'fields': ('contact_number', 'home_address', 'parent_name')
        }),
        ('Academic Information', {
            'fields': ('course', 'year_level', 'semester', 'max_units', 'total_units')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def latest_enrollment_status(self, obj):
        enrollment = obj.enrollments.order_by('-created_at').first()
        return enrollment.status if enrollment else 'No records'
    latest_enrollment_status.short_description = 'Enrollment Status'

    @admin.action(description='Activate selected students')
    def activate_students(self, request, queryset):
        updated = queryset.update(is_active=True)
        User.objects.filter(student_profile__in=queryset).update(
            is_active=True,
            email_verified=True,
            activation_code='',
            activation_code_expires_at=None,
        )
        self.message_user(request, f'{updated} student(s) activated.', messages.SUCCESS)

    @admin.action(description='Deactivate selected students')
    def deactivate_students(self, request, queryset):
        updated = queryset.update(is_active=False)
        User.objects.filter(student_profile__in=queryset).update(is_active=False)
        self.message_user(request, f'{updated} student(s) deactivated.', messages.SUCCESS)

    @admin.action(description='Export selected student records')
    def export_student_records(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="student-records.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Student Number',
            'Full Name',
            'Email',
            'Contact Number',
            'Course',
            'Year Level',
            'Semester',
            'Total Units',
            'Active',
        ])

        for student in queryset:
            writer.writerow([
                student.student_number,
                student.full_name,
                student.email,
                student.contact_number,
                student.course,
                student.year_level,
                student.semester,
                student.total_units,
                student.is_active,
            ])

        return response


# =====================================
# SUBJECT ADMIN
# =====================================
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('subject_code', 'subject_name', 'units', 'course', 'year_level', 'semester')
    search_fields = ('subject_code', 'subject_name')
    list_filter = ('course', 'year_level', 'semester')


# =====================================
# SECTION ADMIN
# =====================================
@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = (
        'section_name',
        'subject',
        'schedule',
        'room',
        'max_capacity',
        'current_count',
        'available_slots',
    )
    search_fields = ('section_name', 'subject__subject_code', 'subject__subject_name')
    list_filter = ('subject__course', 'subject__year_level', 'subject__semester')


# =====================================
# ENROLLMENT ADMIN
# =====================================
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'student',
        'student_number',
        'student_year',
        'subject',
        'section',
        'status',
        'semester',
        'enrollment_date',
    )
    search_fields = (
        'student__first_name',
        'student__last_name',
        'student__email',
        'subject__subject_code',
        'subject__subject_name',
        'section__section_name',
    )
    list_filter = (
        'status',
        'student__course',
        'student__year_level',
        'semester',
        'enrollment_date',
    )
    readonly_fields = ('enrollment_date', 'created_at', 'updated_at')
    actions = [
        'approve_enrollments',
        'reject_enrollments',
        'drop_enrollments',
        'cancel_enrollments',
        'reenroll_students',
        'export_enrolled_student_list',
        'export_enrollment_forms',
    ]

    # Custom method to show student year level
    def student_year(self, obj):
        return obj.student.year_level
    student_year.short_description = 'Year Level'

    def student_number(self, obj):
        return obj.student.student_number
    student_number.short_description = 'Student Number'

    def _run_lifecycle_action(self, request, queryset, method_name, success_label):
        success_count = 0

        for enrollment in queryset.select_related('student', 'subject', 'section'):
            try:
                getattr(enrollment, method_name)()
                success_count += 1
            except Exception as error:
                self.message_user(
                    request,
                    f'{enrollment}: {error}',
                    messages.ERROR
                )

        if success_count:
            self.message_user(
                request,
                f'{success_count} enrollment(s) {success_label}.',
                messages.SUCCESS
            )

    @admin.action(description='Approve selected enrollment requests')
    def approve_enrollments(self, request, queryset):
        self._run_lifecycle_action(request, queryset, 'approve', 'approved')

    @admin.action(description='Reject selected enrollment requests')
    def reject_enrollments(self, request, queryset):
        self._run_lifecycle_action(request, queryset, 'reject', 'rejected')

    @admin.action(description='Drop selected enrollments')
    def drop_enrollments(self, request, queryset):
        self._run_lifecycle_action(request, queryset, 'drop', 'dropped')

    @admin.action(description='Cancel selected enrollments')
    def cancel_enrollments(self, request, queryset):
        self._run_lifecycle_action(request, queryset, 'cancel', 'cancelled')

    @admin.action(description='Re-enroll selected students')
    def reenroll_students(self, request, queryset):
        self._run_lifecycle_action(request, queryset, 're_enroll', 're-enrolled')

    @admin.action(description='Export enrolled student list')
    def export_enrolled_student_list(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="enrolled-students.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Student Number',
            'Student Name',
            'Course',
            'Year Level',
            'Subject Code',
            'Subject Name',
            'Section',
            'Schedule',
            'Room',
            'Status',
        ])

        for enrollment in queryset.filter(status='ENROLLED').select_related('student', 'subject', 'section'):
            writer.writerow([
                enrollment.student.student_number,
                enrollment.student.full_name,
                enrollment.student.course,
                enrollment.student.year_level,
                enrollment.subject.subject_code,
                enrollment.subject.subject_name,
                enrollment.section.section_name if enrollment.section else '',
                enrollment.section.schedule if enrollment.section else '',
                enrollment.section.room if enrollment.section else '',
                enrollment.status,
            ])

        return response

    @admin.action(description='Export enrollment forms')
    def export_enrollment_forms(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="enrollment-forms.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Form ID',
            'Student Number',
            'Student Name',
            'Email',
            'Course',
            'Year Level',
            'Semester',
            'Subject',
            'Units',
            'Section',
            'Status',
            'Remarks',
        ])

        for enrollment in queryset.select_related('student', 'subject', 'section'):
            writer.writerow([
                enrollment.id,
                enrollment.student.student_number,
                enrollment.student.full_name,
                enrollment.student.email,
                enrollment.student.course,
                enrollment.student.year_level,
                enrollment.semester,
                f'{enrollment.subject.subject_code} - {enrollment.subject.subject_name}',
                enrollment.subject.units,
                enrollment.section.section_name if enrollment.section else '',
                enrollment.status,
                enrollment.remarks,
            ])

        return response
