"""Result summary: charts and tables for one class, a section or the school.

Figures follow the report cards: a subject's grade comes from its total
(A 70+, B 60+, C 50+, D 45+, E 40+, else F; ABS when absent from the exam), a
student's average is their total divided by their number of subjects, and a
subject counts as passed at grade E or better.
"""
import statistics
from collections import Counter, defaultdict

from django.contrib import messages
from django.shortcuts import render

from src.access import require, scoped_class, scoped_classes, sees_all_sections, user_section
from src.models import Section, Session, StudentResult, Subject, Term

GRADES = ('A', 'B', 'C', 'D', 'E', 'F')
GRADE_FLOORS = (('A', 70), ('B', 60), ('C', 50), ('D', 45), ('E', 40))
PASS_MARK = 40


def grade_of(total, absent):
    if absent:
        return 'ABS'
    return next((g for g, floor in GRADE_FLOORS if total >= floor), 'F')


def gender_of(value):
    value = (value or '').strip().lower()
    if value in ('m', 'male'):
        return 'Male'
    if value in ('f', 'female'):
        return 'Female'
    return 'Not recorded'


def percent(part, whole):
    return round(part * 100 / whole) if whole else 0


def _rows(classes, session, term, subject=None):
    results = StudentResult.objects.filter(student_class__in=classes, session=session, term=term)
    if subject is not None:
        results = results.filter(subject=subject)
    return list(results.values('student_id', 'student__student_name', 'student__gender', 'student_class_id',
                               'student_class__name', 'subject_id', 'subject__subject_name', 'total',
                               'exam_absent'))


def _students(rows):
    """Per-student totals and averages, best average first."""
    by_student = {}
    for r in rows:
        s = by_student.setdefault(r['student_id'], {
            'id': r['student_id'], 'name': r['student__student_name'], 'class': r['student_class__name'],
            'gender': gender_of(r['student__gender']), 'total': 0, 'subjects': 0, 'failed': 0, 'absent': 0})
        s['total'] += r['total']
        s['subjects'] += 1
        grade = grade_of(r['total'], r['exam_absent'])
        s['failed'] += grade == 'F'
        s['absent'] += grade == 'ABS'
    for s in by_student.values():
        s['average'] = round(s['total'] / s['subjects'], 2)
    return sorted(by_student.values(), key=lambda s: (-s['average'], s['name'].lower()))


def _subjects(rows):
    by_subject = defaultdict(list)
    names = {}
    for r in rows:
        by_subject[r['subject_id']].append(r)
        names[r['subject_id']] = r['subject__subject_name']
    subjects = []
    for sid, items in by_subject.items():
        grades = Counter(grade_of(r['total'], r['exam_absent']) for r in items)
        passed = sum(grades[g] for g in GRADES[:-1])
        subjects.append({
            'id': sid, 'name': names[sid], 'students': len(items),
            'average': round(statistics.mean(r['total'] for r in items), 1),
            'highest': max(r['total'] for r in items), 'lowest': min(r['total'] for r in items),
            'grades': {g: grades[g] for g in GRADES + ('ABS',)},
            'passed': passed, 'pass_rate': percent(passed, len(items)),
        })
    return sorted(subjects, key=lambda s: (-s['average'], s['name']))


def _histogram(students):
    bins = [{'label': f'{low}–{low + 9}' if low < 90 else '90–100', 'low': low, 'count': 0}
            for low in range(0, 100, 10)]
    for s in students:
        bins[min(int(s['average'] // 10), 9)]['count'] += 1
    return bins


def _trend(classes, session):
    """Mean student average for each term of the session that has results."""
    totals = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in (StudentResult.objects.filter(student_class__in=classes, session=session)
              .values('term_id', 'student_id', 'total')):
        t = totals[r['term_id']][r['student_id']]
        t[0] += r['total']
        t[1] += 1
    terms = {t.id: t.term_name for t in Term.objects.filter(pk__in=totals)}
    return [{'label': terms[tid], 'value': round(statistics.mean(total / count for total, count in by.values()), 1),
             'students': len(by)} for tid, by in sorted(totals.items())]


def build_summary(classes, session, term, subject=None):
    rows = _rows(classes, session, term, subject)
    if not rows:
        return None
    students = _students(rows)
    subjects = _subjects(rows)
    grades = Counter(grade_of(r['total'], r['exam_absent']) for r in rows)
    averages = [s['average'] for s in students]
    by_gender = defaultdict(list)
    for s in students:
        by_gender[s['gender']].append(s['average'])
    by_class = defaultdict(list)
    for s in students:
        by_class[s['class']].append(s['average'])
    passed_overall = sum(a >= PASS_MARK for a in averages)
    return {
        'stats': {
            'students': len(students), 'subjects': len(subjects), 'results': len(rows),
            'mean': round(statistics.mean(averages), 1), 'median': round(statistics.median(averages), 1),
            'pass_rate': percent(passed_overall, len(students)), 'passed': passed_overall,
            'subject_pass_rate': percent(sum(grades[g] for g in GRADES[:-1]), len(rows)),
            'absent': grades['ABS'], 'top': students[0],
        },
        'grades': [{'grade': g, 'count': grades[g]} for g in GRADES + ('ABS',)],
        'subjects': subjects,
        'students': students,
        'histogram': _histogram(students),
        'gender': [{'label': g, 'value': round(statistics.mean(v), 1), 'students': len(v)}
                   for g, v in sorted(by_gender.items()) if v],
        'classes': sorted(({'label': c, 'value': round(statistics.mean(v), 1), 'students': len(v)}
                           for c, v in by_class.items()), key=lambda c: c['label']),
        'top': students[:10],
        'support': [s for s in students if s['average'] < PASS_MARK or s['failed'] >= 3][::-1][:25],
    }


def _scope(request):
    """(classes queryset, label, chosen class or None) for the form's scope value."""
    value = request.GET.get('scope', '')
    if value.startswith('class-'):
        student_class = scoped_class(request.user, value[6:], include_archived=True)
        return [student_class], student_class.name, student_class
    if value.startswith('section-') and value[8:].isdigit():
        section = Section.objects.filter(pk=value[8:]).first()
        if section is not None and (sees_all_sections(request.user) or section == user_section(request.user)):
            return list(scoped_classes(request.user, include_archived=True).filter(section=section)), \
                section.section_name, None
    if value == 'school' and sees_all_sections(request.user):
        return list(scoped_classes(request.user, include_archived=True)), 'Whole school', None
    return None, '', None


@require('view_reports')
def result_summary(request):
    sections = (Section.objects.order_by('section_name') if sees_all_sections(request.user)
                else Section.objects.filter(pk=getattr(user_section(request.user), 'pk', None)))
    context = {'subjects_list': Subject.objects.all(), 'sections': sections, 'chosen': request.GET}
    if not request.GET:
        latest = StudentResult.objects.order_by('-session_id', '-term_id').values('session_id', 'term_id').first()
        context['chosen'] = {'session': str(latest['session_id']), 'term': str(latest['term_id'])} if latest else {}
        return render(request, 'src/result_summary.html', context)

    session = Session.objects.filter(pk=request.GET.get('session') or 0).first()
    term = Term.objects.filter(pk=request.GET.get('term') or 0).first()
    classes, scope_label, student_class = _scope(request)
    subject = Subject.objects.filter(pk=request.GET.get('subject') or 0).first()
    if session is None or term is None or classes is None:
        messages.error(request, 'Choose a session, term and class or section.')
        return render(request, 'src/result_summary.html', context)
    summary = build_summary(classes, session, term, subject)
    if summary is None:
        messages.error(request, f'No results for {scope_label}{", " + subject.subject_name if subject else ""}, '
                                f'{session}, {term}.')
        return render(request, 'src/result_summary.html', context)
    summary['trend'] = _trend(classes, session) if subject is None else []
    charts = {k: summary[k] for k in ('grades', 'subjects', 'histogram', 'gender', 'classes', 'trend')}
    context.update(summary=summary, charts=charts, scope_label=scope_label,
                   student_class=student_class, session=session, term=term, subject=subject,
                   many_classes=len(classes) > 1)
    return render(request, 'src/result_summary.html', context)
