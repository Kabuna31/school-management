# core/resources.py
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import (
    School, User, EmployeeProfile, ParentProfile,
    Stream, ClassLevel, StudentProfile, Subject, Mark, Timetable
)


class UserResource(resources.ModelResource):
    """User resource with password hashing on import"""
    
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email', 'first_name', 'last_name', 
                 'role', 'school', 'is_active', 'is_staff', 'is_superuser')
        export_order = ('id', 'username', 'email', 'first_name', 'last_name', 
                       'role', 'school', 'is_active')
        import_id_fields = ('id', 'username')
    
    def before_import(self, dataset, **kwargs):
        """Process the dataset before import"""
        # Check if password column exists
        if 'password' in dataset.headers:
            # Show warning that passwords will be hashed
            print("⚠ Passwords will be hashed during import.")
        return dataset
    
    def before_import_row(self, row, **kwargs):
        """Hash password before importing each row"""
        # Only hash if password is provided and not already hashed
        if 'password' in row and row['password']:
            password = row['password']
            
            # Check if password is already hashed (starts with pbkdf2_sha256)
            if not password.startswith('pbkdf2_sha256'):
                try:
                    # Hash the password
                    row['password'] = make_password(password)
                except Exception as e:
                    print(f"⚠ Error hashing password for user: {row.get('username', 'Unknown')} - {e}")
                    # If hashing fails, set a default password
                    row['password'] = make_password('default123')
        
        return row
    
    def after_import_row(self, row, row_result, **kwargs):
        """Log import results"""
        if row_result.errors:
            print(f"⚠ Error importing row: {row.get('username', 'Unknown')}")
        else:
            print(f"✓ Imported: {row.get('username', 'Unknown')}")
        return row
    
    def export_resource_class(self):
        """Export without password field for security"""
        class UserExportResource(UserResource):
            class Meta(UserResource.Meta):
                # Exclude password and sensitive fields from export
                exclude = ('password', 'is_superuser')
                fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                         'role', 'school', 'is_active', 'is_staff', 'date_joined')
                export_order = ('id', 'username', 'email', 'first_name', 'last_name', 
                               'role', 'school', 'is_active', 'is_staff', 'date_joined')
        return UserExportResource


class SchoolResource(resources.ModelResource):
    class Meta:
        model = School
        fields = ('id', 'name', 'code', 'address', 'phone', 'email')
        export_order = fields


class EmployeeProfileResource(resources.ModelResource):
    class Meta:
        model = EmployeeProfile
        fields = ('id', 'user', 'staff_id', 'hire_date', 'school')
        export_order = fields


class ParentProfileResource(resources.ModelResource):
    class Meta:
        model = ParentProfile
        fields = ('id', 'user', 'phone_number', 'school')
        export_order = fields


class StreamResource(resources.ModelResource):
    class Meta:
        model = Stream
        fields = ('id', 'name', 'school')
        export_order = fields


class ClassLevelResource(resources.ModelResource):
    class Meta:
        model = ClassLevel
        fields = ('id', 'name', 'school', 'class_teacher')
        export_order = fields


class StudentProfileResource(resources.ModelResource):
    class Meta:
        model = StudentProfile
        fields = ('id', 'user', 'admission_number', 'gender', 'class_level', 'stream', 'school')
        export_order = fields


class SubjectResource(resources.ModelResource):
    class Meta:
        model = Subject
        fields = ('id', 'name', 'code', 'school')
        export_order = fields


class MarkResource(resources.ModelResource):
    class Meta:
        model = Mark
        fields = ('id', 'student', 'subject', 'teacher', 'term', 'exam', 'mid_term', 'end_term', 'school')
        export_order = fields


class TimetableResource(resources.ModelResource):
    class Meta:
        model = Timetable
        fields = ('id', 'class_level', 'stream', 'subject', 'teacher', 'day', 'start_time', 'end_time', 'school')
        export_order = fields