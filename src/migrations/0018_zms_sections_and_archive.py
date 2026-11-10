"""ZMS data setup: sections and archived classes.

1. Create the two sections, "Nursery & Primary" and "Secondary" (JS/SS), and
   put each class in one by its name. Classes whose name gives no section
   ("Class 1", "________", "2616") are left without one; only administrators
   see them until a section is chosen in the admin panel.
2. Archive the classes with no results in 2025/2026 (graduated sets, holding
   classes, old rosters), listed by id and name as found on 2026-11-10. They
   stay available for viewing reports but leave the data-entry dropdowns.
   A class is only archived if its id and name both still match, so running
   this on another database (tests, a fresh install) changes nothing.

Both steps are recorded in the data review log so they can be seen and undone.
"""
import re

from django.db import migrations

NURSERY_PRIMARY = 'Nursery & Primary'
SECONDARY = 'Secondary'


def section_for(name):
    name = (name or '').lower()
    if re.search(r'nursery|primary|\bn\d', name):
        return NURSERY_PRIMARY
    if re.search(r'\bj\.?s|\bs\.?s|jss', name):
        return SECONDARY
    return None


ARCHIVE = {
    18: 'ZPrimary 1A', 20: 'Primary 3', 24: 'SS 3', 31: 'Primary 5', 32: 'Class 1',
    35: 'Class of 2021 SS3 A', 36: 'Class of 2021 SS3 B', 37: 'Class of 2021 JSS3 A',
    38: 'Class of 2021 JS3 B', 40: 'SS2C 2021', 42: 'Class of 2021 Primary 5', 44: 'Nursery 3B',
    45: 'ZPrimary 1B', 47: 'SS 3A SCIENCE', 48: 'SS 3B SCIENCE', 49: '________',
    50: 'Class of 2022 JS3A', 51: 'Class of 2022 JS3B', 53: 'SS3A Science Class of 2022',
    54: 'SS3A Art Class of 2022', 55: 'SS3B Science Class of 2022', 56: 'SS2C2022',
    57: 'Primary 5 class of 2022', 68: 'Pre SS1 2023', 69: 'Class 2023 SS3A', 70: 'Class 2023 SS3B',
    71: 'CLASS OF 2023 JS3A', 72: 'CLASS OF 2023 JS3B', 73: 'CLASS OF 2023 JS3C',
    74: 'Class 2023 SS3C', 75: 'Class 2023 Primary 5', 76: 'JS 3D', 77: 'Pre SS 1', 80: '2616',
    81: 'Confused Class N2a&2b', 82: 'Pre SS1 2023', 87: 'SS1', 92: 'CLASS OF 2024 JS3',
    94: 'CLASS OF 2024 SS3', 96: 'Nursery 1 Ananymous', 97: 'SS 3 Class of 2025',
    99: 'Primary 5 class of 2025', 102: 'LOST CLASS PRIMARY 2025',
}


def setup(apps, schema_editor):
    Section = apps.get_model('src', 'Section')
    StudentClass = apps.get_model('src', 'StudentClass')
    ReviewDecision = apps.get_model('src', 'ReviewDecision')

    classes = list(StudentClass.objects.filter(section__isnull=True))
    if not classes:
        return
    sections = {name: Section.objects.get_or_create(section_name=name)[0]
                for name in (NURSERY_PRIMARY, SECONDARY)}
    before = [{'id': c.id, 'name': c.name, 'section_id': None, 'is_archived': c.is_archived} for c in classes]
    assigned = {}
    archived = []
    for c in classes:
        section = section_for(c.name)
        if section:
            c.section = sections[section]
            assigned.setdefault(section, []).append(c.id)
        if ARCHIVE.get(c.id) == c.name and not c.is_archived:
            c.is_archived = True
            archived.append(c.id)
        c.save()
    unassigned = [c.id for c in classes if c.section_id is None]
    ReviewDecision.objects.create(
        kind='class_section', target='zms-sections-2026-11', action='assign',
        summary=(f'Put {sum(len(v) for v in assigned.values())} classes into sections by name '
                 f'({len(unassigned)} left without one) and archived {len(archived)} classes '
                 'with no 2025/2026 results.'),
        before={'classes': before},
        after={'sections': {name: s.id for name, s in sections.items()}, 'assigned': assigned,
               'unassigned': unassigned, 'archived': archived},
        note='Data migration 0018 (ZMS upgrade).',
    )


def undo(apps, schema_editor):
    StudentClass = apps.get_model('src', 'StudentClass')
    ReviewDecision = apps.get_model('src', 'ReviewDecision')
    decision = ReviewDecision.objects.filter(target='zms-sections-2026-11').first()
    if decision is None:
        return
    for row in decision.before['classes']:
        StudentClass.objects.filter(pk=row['id']).update(section=None, is_archived=row['is_archived'])
    decision.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('src', '0017_class_archive_and_review_log'),
    ]

    operations = [
        migrations.RunPython(setup, undo),
    ]
