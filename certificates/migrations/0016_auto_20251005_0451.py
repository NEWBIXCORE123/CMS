# brgy_cms/migrations/0016_create_groups.py
from django.db import migrations
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

def create_groups(apps, schema_editor):
    # Create Groups
    staff_group, _ = Group.objects.get_or_create(name='Staff')
    admin_group, _ = Group.objects.get_or_create(name='Admin')
    superadmin_group, _ = Group.objects.get_or_create(name='Superadmin')

    # Create Custom Permissions for Dashboard and Reports
    dashboard_ct, _ = ContentType.objects.get_or_create(
        app_label='certificates',
        model='dashboard'
    )
    reports_ct, _ = ContentType.objects.get_or_create(
        app_label='certificates',
        model='reports'
    )

    Permission.objects.get_or_create(
        codename='view_dashboard',
        name='Can view dashboard',
        content_type=dashboard_ct
    )
    Permission.objects.get_or_create(
        codename='view_reports',
        name='Can view reports',
        content_type=reports_ct
    )

    # Define Permissions (based on admin screenshot and requirements)
    staff_perms = [
        'view_certificate',  # certificates | certificate | Can view certificate
        'add_certificate',   # certificates | certificate | Can add certificate
        'view_dashboard',    # custom permission
    ]
    admin_perms = staff_perms + [
        'view_activitylog',  # certificates | activity log | Can view activity log
        'view_reports',      # custom permission
    ]
    superadmin_perms = admin_perms + [
        'add_adminsignature',      # certificates | admin signature | Can add admin signature
        'change_adminsignature',   # certificates | admin signature | Can change admin signature
        'view_adminsignature',     # certificates | admin signature | Can view admin signature
        'delete_adminsignature',   # certificates | admin signature | Can delete admin signature
        'add_certificatetemplate',    # certificates | certificate template | Can add certificate template
        'change_certificatetemplate', # certificates | certificate template | Can change certificate template
        'view_certificatetemplate',   # certificates | certificate template | Can view certificate template
        'delete_certificatetemplate', # certificates | certificate template | Can delete certificate template
    ]

    # Assign Permissions
    for perm in staff_perms:
        try:
            permission = Permission.objects.get(codename=perm)
            staff_group.permissions.add(permission)
        except Permission.DoesNotExist:
            print(f"Permission {perm} not found. Ensure models are migrated.")
    for perm in admin_perms:
        try:
            permission = Permission.objects.get(codename=perm)
            admin_group.permissions.add(permission)
        except Permission.DoesNotExist:
            print(f"Permission {perm} not found. Ensure models are migrated.")
    for perm in superadmin_perms:
        try:
            permission = Permission.objects.get(codename=perm)
            superadmin_group.permissions.add(permission)
        except Permission.DoesNotExist:
            print(f"Permission {perm} not found. Ensure models are migrated.")

    # Superadmin gets all permissions for full access
    superadmin_group.permissions.add(*Permission.objects.all())

def remove_groups(apps, schema_editor):
    # Optional: Remove groups if rolling back migration
    Group.objects.filter(name__in=['Staff', 'Admin', 'Superadmin']).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('certificates', '0015_activitylog_user'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]
    operations = [
        migrations.RunPython(create_groups, remove_groups)
    ]