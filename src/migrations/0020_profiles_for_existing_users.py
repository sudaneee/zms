"""Give every existing ZMS account a role profile.

Until now every signed-in user could do everything. Mapping (defaults; an
administrator can change any of them on the Users page):

  superuser                 -> Administrator, all sections
  zmsnp1 .. zmsnp5          -> Staff, Nursery & Primary
  teacher1 .. teacher13     -> Staff, Secondary
  everyone else             -> Staff with no section (sees nothing until an
                               administrator chooses a section)

The numbered accounts are shared logins, so they are flagged as legacy shared
accounts for the administrator to replace with personal accounts.
"""
import re

from django.db import migrations

NURSERY_PRIMARY = 'Nursery & Primary'
SECONDARY = 'Secondary'


def profile_for(user):
    """(role, section name, legacy shared) for an existing account."""
    name = user.username.lower()
    if user.is_superuser:
        return 'admin', None, False
    if re.fullmatch(r'zmsnp\d+', name):
        return 'staff', NURSERY_PRIMARY, True
    if re.fullmatch(r'teacher\d+', name):
        return 'staff', SECONDARY, True
    return 'staff', None, False


def create_profiles(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Section = apps.get_model('src', 'Section')
    UserProfile = apps.get_model('src', 'UserProfile')
    sections = {s.section_name: s for s in Section.objects.all()}
    for user in User.objects.all():
        if UserProfile.objects.filter(user=user).exists():
            continue
        role, section, shared = profile_for(user)
        UserProfile.objects.create(user=user, role=role, section=sections.get(section),
                                   is_legacy_shared=shared)


def remove_profiles(apps, schema_editor):
    apps.get_model('src', 'UserProfile').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('src', '0019_roles_audit_soft_delete'),
    ]

    operations = [
        migrations.RunPython(create_profiles, remove_profiles),
    ]
