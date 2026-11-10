"""Report views: class report cards, broadsheet, single result, subject analysis.

All class reports are built by `build_class_report`, so report cards, the
broadsheet, the public result checker and e-signature snapshots agree. The
averages, class positions and highest average use the same formulas as the
original system. Students are listed alphabetically and each student's
behavioural assessment is matched by student (the original paired them by
list position, which could print another student's assessment).
"""
import datetime
import re

from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Sum
from django.shortcuts import render

from src.access import require, scoped_class
from src.models import (Session, StudentBehaviouralAssessment, StudentClass, StudentResult, Subject, Term, sets)
from src.signing import active_approvals, verification_for


def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n}{suffix}'


def name_key(student):
    return re.sub(r'\s+', ' ', student.student_name or '').strip().lower()


def build_class_report(student_class, session, term):
    """Per-student totals, averages, positions and behaviour for one class/term.

    Returns (students, subjects): `students` is an ordered dict keyed by
    student (alphabetical), `subjects` the subject columns in first-entered order.
    """
    results = (StudentResult.objects.filter(session=session, term=term, student_class=student_class)
               .select_related('student', 'subject', 'session', 'term', 'student_class').order_by('id'))
    by_student = {}
    subjects = []
    for r in results:
        by_student.setdefault(r.student, []).append(r)
        if r.subject not in subjects:
            subjects.append(r.subject)
    behaviour = {}
    for b in (StudentBehaviouralAssessment.objects.filter(session=session, term=term, student_class=student_class)
              .order_by('id')):
        behaviour.setdefault(b.student_id, b)   # first one if a duplicate slipped in

    report = {}
    for student in sorted(by_student, key=lambda s: (name_key(s), s.id)):
        rows = by_student[student]
        total = sum(r.total for r in rows)
        by_subject = {r.subject_id: r for r in rows}
        report[student] = {
            'student': student,
            'subjects': rows,
            'cells': [by_subject.get(s.id) for s in subjects],
            'total': total,
            'overal_total': total,
            'average': round(total / len(rows), 2),
            'terms': rows[0].term,
            'sesss': rows[0].session,
            'classs': rows[0].student_class,
            'bhv': behaviour.get(student.id),
        }
    averages = [r['average'] for r in report.values()]
    for r in report.values():
        r['position'] = 1 + sum(a > r['average'] for a in averages)
        r['c_pos'] = ordinal(r['position'])
    return report, subjects, averages


def percentage(part, whole):
    """Whole-number percentage, rounding halves up (65 of 71 is 92)."""
    return int(part * 100 / whole + 0.5) if whole else 0


def build_result_analysis(student_class, session, term):
    """Class results sheet: per-student summaries and per-subject grade counts.

    `report` is build_class_report's, with each student's earlier terms of this
    session, session cumulative, failed and absent subjects added. A subject's
    total counts only students with a result in it, because the school has no
    course registration and classes can have optional subjects. Students absent
    from the exam count in the total but not as passed.
    """
    report, subjects, averages = build_class_report(student_class, session, term)
    earlier = {row['student']: row for row in (
        StudentResult.objects.filter(student__in=report, session=session, term_id__lt=term.id)
        .values('student').order_by().annotate(subjects=Count('id'), total=Sum('total')))}
    for student, r in report.items():
        before = earlier.get(student.id, {'subjects': 0, 'total': 0})
        count = before['subjects'] + len(r['subjects'])
        total = before['total'] + r['total']
        r['earlier'] = {'subjects': before['subjects'], 'total': before['total'],
                        'average': round(before['total'] / before['subjects'], 2) if before['subjects'] else None}
        r['cumulative'] = {'subjects': count, 'total': total, 'average': round(total / count, 2)}
        r['failed'] = [str(c.subject) for c in r['subjects'] if c.grade() == 'F']
        r['absent'] = [str(c.subject) for c in r['subjects'] if c.exam_absent]

    analysis = []
    for index, subject in enumerate(subjects):
        cells = [r['cells'][index] for r in report.values() if r['cells'][index] is not None]
        grades = [c.grade() for c in cells]
        passed = sum(g not in ('F', 'ABS') for g in grades)
        analysis.append({'subject': subject, 'counts': [grades.count(g) for g in 'ABCDEF'],
                         'absent': grades.count('ABS'),
                         'no_result': len(report) - len(cells), 'total': len(cells), 'passed': passed,
                         'percent': percentage(passed, len(cells))})
    return report, subjects, analysis


def card_context(request, student_class, session, term, student_ids=None):
    report, subjects, averages = build_class_report(student_class, session, term)
    approvals = active_approvals(student_class, session, term)
    head = approvals.get('head')
    for r in report.values():
        r['verify'] = verification_for(request, head, r['student']) if head else None
    if student_ids is not None:
        report = {s: r for s, r in report.items() if s.id in student_ids}
    section = student_class.section
    return {
        'date': datetime.datetime.now(),
        'f_classs': str(student_class),
        'section': section,
        'senior': is_senior(student_class),
        'show_class_position': settings.REPORT_SHOW_CLASS_POSITION,
        'results': report,
        'some_images': sets.objects.first(),
        'p_term': term.term_name,
        'allAvr': averages,
        'noInClass': len(averages),
        'classHighestAverage': max(averages) if averages else '',
        'approvals': approvals,
    }


def is_senior(student_class):
    """Secondary classes are signed by the Form Master and Principal."""
    section = student_class.section
    return section is not None and section.section_name == settings.SENIOR_SECTION


def card_template(student_class):
    return 'src/single_result_view.html'


def _class_term(request):
    """Selected class (in scope, archived allowed), session and term, or None with a message."""
    if not all(request.POST.get(k, '').isdigit() for k in ('session', 'term', 'class')):
        messages.error(request, 'Choose a session, term and class.')
        return None
    student_class = scoped_class(request.user, request.POST['class'], include_archived=True)
    session = Session.objects.filter(pk=request.POST['session']).first()
    term = Term.objects.filter(pk=request.POST['term']).first()
    if session is None or term is None:
        messages.error(request, 'Choose a session, term and class.')
        return None
    if not StudentResult.objects.filter(session=session, term=term, student_class=student_class).exists():
        messages.error(request, 'No results have been entered for that class, session and term.')
        return None
    return student_class, session, term


@require('view_reports')
def result_view(request):
    if request.method == 'POST' and 'form1' in request.POST:
        chosen = _class_term(request)
        if chosen is None:
            return render(request, 'src/result_view.html', {})
        student_class, session, term = chosen
        return render(request, card_template(student_class), card_context(request, student_class, session, term))
    return render(request, 'src/result_view.html', {})


def single_result_view(request):
    """Public result checker: session, term and student ID number."""
    if request.method == 'POST' and 'form1' in request.POST:
        session = request.POST.get('session', '')
        term = request.POST.get('term', '')
        # ZMS students check results with their numeric student ID; a number
        # written with a prefix (e.g. "ZMS/SS/123") is read as its last part.
        found = re.search(r'(\d+)\s*$', request.POST.get('student_id', ''))
        final_student_id = found.group(1) if found else ''
        if not (session.isdigit() and term.isdigit() and final_student_id):
            messages.error(request, 'Choose a session and term, and enter the student ID number.')
            return render(request, 'src/single_result_view1.html')
        first = (StudentResult.objects.filter(session=session, term=term, student=final_student_id)
                 .select_related('student_class__section', 'session', 'term').order_by('id').first())
        if first is None:
            messages.error(request, 'No result was found for that student ID, session and term.')
            return render(request, 'src/single_result_view1.html')
        context = card_context(request, first.student_class, first.session, first.term,
                               student_ids={int(final_student_id)})
        return render(request, card_template(first.student_class), context)
    return render(request, 'src/single_result_view1.html')


@require('view_reports')
def class_summary(request):
    if request.method == 'POST' and 'form1' in request.POST:
        classs, term, session, subject = (request.POST.get(k, '') for k in ('class', 'term', 'session', 'subject'))
        if not all(v.isdigit() for v in (classs, term, session, subject)):
            messages.error(request, 'Choose a class, term, session and subject.')
            return render(request, 'src/class_summary.html', {'subjects': Subject.objects.all()})
        student_class = scoped_class(request.user, classs, include_archived=True)
        subject = Subject.objects.filter(pk=subject).first()
        result_summary = sorted(
            StudentResult.objects.filter(subject=subject, student_class=student_class, session=session, term=term)
            .select_related('student'), key=lambda r: (name_key(r.student), r.student_id))
        bands = {'a_count': 70, 'b_count': 60, 'c_count': 50, 'd_count': 45, 'e_count': 40}
        counts = dict.fromkeys(list(bands) + ['f_count', 'abs_count'], 0)
        for r in result_summary:
            band = next((k for k, floor in bands.items() if r.total >= floor), 'f_count')
            counts['abs_count' if r.exam_absent else band] += 1
        context = dict(counts, summary=result_summary, total_students=len(result_summary),
                       subject=subject.subject_name if subject else '', classs=student_class.class_name)
        return render(request, 'src/summary_page.html', context)
    return render(request, 'src/class_summary.html', {'subjects': Subject.objects.all()})


@require('view_reports')
def class_result_summary(request):
    if request.method == 'POST' and 'form1' in request.POST:
        chosen = _class_term(request)
        if chosen is None:
            return render(request, 'src/result_view.html', {})
        student_class, session, term = chosen
        report, subjects, _ = build_class_report(student_class, session, term)
        senior = is_senior(student_class)
        context = {
            'date': datetime.datetime.now(),
            'f_classs': str(student_class),
            'results': report,
            'some_images': sets.objects.first(),
            'p_term': term.term_name,
            'eachSubject': subjects,
            'session': session.session_name,
            'term': term.term_name,
            'class': student_class,
            'directorAcadamic': 'Director Acadamic & Examination',
            'pcHeadTeacher': 'Principal' if senior else 'Head Teacher',
            'approvals': active_approvals(student_class, session, term),
        }
        return render(request, 'src/class_result_summary.html', context)
    return render(request, 'src/result_view.html', {})


@require('view_reports')
def result_analysis(request):
    if request.method == 'POST' and 'form1' in request.POST:
        chosen = _class_term(request)
        if chosen is None:
            return render(request, 'src/result_view.html', {})
        student_class, session, term = chosen
        report, subjects, analysis = build_result_analysis(student_class, session, term)
        senior = is_senior(student_class)
        return render(request, 'src/class_result_analysis.html', {
            'results': report, 'subjects': subjects, 'analysis': analysis, 'student_class': student_class,
            'session': session, 'term': term, 'has_earlier': any(r['earlier']['subjects'] for r in report.values()),
            'headLabel': 'Principal' if senior else 'Head Teacher',
            'approvals': active_approvals(student_class, session, term),
        })
    return render(request, 'src/result_view.html', {})
