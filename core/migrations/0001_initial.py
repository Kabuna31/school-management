# Generated migration — matches current models.py exactly
# term field replaced with exam, Timetable model added

from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [

        # ── School ──────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='School',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('code', models.CharField(max_length=20, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),

        # ── User ────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False)),
                ('username', models.CharField(max_length=150, unique=True)),
                ('first_name', models.CharField(blank=True, max_length=150)),
                ('last_name', models.CharField(blank=True, max_length=150)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('is_staff', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
                ('role', models.CharField(
                    choices=[
                        ('system_admin',   'System Admin'),
                        ('headteacher',    'School Administrator'),
                        ('bursar',         'School Bursar'),
                        ('nurse',          'School Nurse'),
                        ('librarian',      'School Librarian'),
                        ('lab_technician', 'Lab Technician'),
                        ('dos',            'Director of Studies'),
                        ('class_teacher',  'Class Teacher'),
                        ('teacher',        'Teacher'),
                        ('parent',         'Parent'),
                        ('student',        'Student'),
                    ],
                    default='teacher', max_length=20,
                )),
                ('groups', models.ManyToManyField(blank=True, related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
                ('school', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.school')),
            ],
            options={'abstract': False},
        ),

        # ── Stream ──────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='Stream',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=50)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.school')),
            ],
        ),
        migrations.AlterUniqueTogether(name='stream', unique_together={('school', 'name')}),

        # ── EmployeeProfile ─────────────────────────────────────────────────
        migrations.CreateModel(
            name='EmployeeProfile',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('staff_id', models.CharField(max_length=50)),
                ('hire_date', models.DateField(blank=True, null=True)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.school')),
            ],
        ),
        migrations.AlterUniqueTogether(name='employeeprofile', unique_together={('school', 'staff_id')}),

        # ── ParentProfile ───────────────────────────────────────────────────
        migrations.CreateModel(
            name='ParentProfile',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('phone_number', models.CharField(blank=True, max_length=15)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.school')),
            ],
        ),

        # ── ClassLevel ──────────────────────────────────────────────────────
        migrations.CreateModel(
            name='ClassLevel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=50)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.school')),
                ('class_teacher', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.employeeprofile')),
            ],
        ),
        migrations.AlterUniqueTogether(name='classlevel', unique_together={('school', 'name')}),

        # ── StudentProfile ──────────────────────────────────────────────────
        migrations.CreateModel(
            name='StudentProfile',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('admission_number', models.CharField(max_length=20)),
                ('gender', models.CharField(choices=[('M', 'Male'), ('F', 'Female')], max_length=1)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.school')),
                ('class_level', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.classlevel')),
                ('stream', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.stream')),
                ('parent', models.ManyToManyField(blank=True, related_name='children', to='core.parentprofile')),
            ],
        ),
        migrations.AlterUniqueTogether(name='studentprofile', unique_together={('school', 'admission_number')}),

        # ── Subject ─────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=10)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.school')),
            ],
        ),
        migrations.AlterUniqueTogether(name='subject', unique_together={('school', 'code')}),

        # ── Mark (uses exam field — 6 slots per year) ────────────────────────
        migrations.CreateModel(
            name='Mark',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('exam', models.CharField(
                    choices=[
                        ('T1_Mid', 'Term 1 — Mid Term'),
                        ('T1_End', 'Term 1 — End of Term'),
                        ('T2_Mid', 'Term 2 — Mid Term'),
                        ('T2_End', 'Term 2 — End of Term'),
                        ('T3_Mid', 'Term 3 — Mid Term'),
                        ('T3_End', 'Term 3 — End of Term'),
                    ],
                    max_length=10,
                )),
                ('score', models.DecimalField(decimal_places=2, default='0.00', max_digits=5)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.school')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.studentprofile')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.subject')),
                ('teacher', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.employeeprofile')),
            ],
        ),
        migrations.AlterUniqueTogether(name='mark', unique_together={('school', 'student', 'subject', 'exam')}),

        # ── Timetable ───────────────────────────────────────────────────────
        migrations.CreateModel(
            name='Timetable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('day', models.CharField(choices=[('Mon','Monday'),('Tue','Tuesday'),('Wed','Wednesday'),('Thu','Thursday'),('Fri','Friday')], max_length=3)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('room', models.CharField(blank=True, max_length=50)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.school')),
                ('class_level', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.classlevel')),
                ('stream', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.stream')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.subject')),
                ('teacher', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.employeeprofile')),
            ],
            options={'ordering': ['day', 'start_time']},
        ),
    ]
