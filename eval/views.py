"""Teacher lesson evaluations: record, list and print.

Administrators and Heads of Section record evaluations; a Head of Section
works with the classes of their own section only.
"""
import datetime

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from src import audit
from src.access import require, scoped_class, scoped_classes, sees_all_sections
from src.models import Subject
from eval.models import RATINGS, SECTION_TITLES, Evaluation, EvaluationScore, General_Questions


def _questions():
    grouped = {}
    for q in General_Questions.objects.all():
        grouped.setdefault(q.section, []).append(q)
    return [(SECTION_TITLES.get(k, f'Section {k}'), items) for k, items in sorted(grouped.items())]


def _visible(user):
    """Evaluations the user may see: all for administrators, else their section's classes."""
    evaluations = Evaluation.objects.select_related('student_class', 'subject')
    if sees_all_sections(user):
        return evaluations
    return evaluations.filter(student_class__in=scoped_classes(user, include_archived=True))


def _parse_date(value):
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


@require('evaluate_teachers')
def evaluation(request):
    """The evaluation form (the URL name predates the upgrade)."""
    questions = _questions()
    context = {'questions': questions, 'ratings': RATINGS, 'subjects': Subject.objects.all(),
               'today': datetime.date.today(), 'values': {}, 'chosen': {}}
    if request.method != 'POST':
        return render(request, 'eval/form.html', context)

    data = request.POST
    values = {k: data.get(k, '').strip() for k in
              ('teacher_name', 'class', 'subject', 'topic', 'sub_topic', 'general_comment', 'assessor', 'date')}
    errors = []
    for field, label in (('teacher_name', "the teacher's name"), ('topic', 'the topic'),
                         ('assessor', "the assessor's name")):
        if not values[field]:
            errors.append(f'Enter {label}.')
    subject = Subject.objects.filter(pk=values['subject']).first() if values['subject'].isdigit() else None
    if subject is None:
        errors.append('Choose a subject.')
    student_class = scoped_class(request.user, values['class']) if values['class'] else None
    if student_class is None:
        errors.append('Choose the class taught.')
    date = _parse_date(values['date'])
    if date is None or date > datetime.date.today():
        errors.append('Enter the date of the lesson (not in the future).')
    valid = {str(r) for r, _ in RATINGS}
    scores = {}
    for _, items in questions:
        for q in items:
            raw = data.get(f'q{q.id}', '')
            if raw in valid:
                scores[q] = int(raw)
            else:
                errors.append(f'Rate "{q.item}".')
    if errors:
        for e in errors[:8]:
            messages.error(request, e)
        if len(errors) > 8:
            messages.error(request, f'... and {len(errors) - 8} more.')
        context['values'] = values
        context['chosen'] = {f'q{q.id}': str(v) for q, v in scores.items()}
        return render(request, 'eval/form.html', context)

    with transaction.atomic():
        record = Evaluation.objects.create(
            teacher_name=values['teacher_name'], student_class=student_class, subject=subject,
            topic=values['topic'], sub_topic=values['sub_topic'], general_comment=values['general_comment'],
            assessor=values['assessor'], date=date, recorded_by=request.user)
        EvaluationScore.objects.bulk_create(
            [EvaluationScore(evaluation=record, question=q, score=v) for q, v in scores.items()])
        audit.log('create', model='Evaluation', object_id=record.pk, object_repr=str(record),
                  section_id=student_class.section_id,
                  details={'total': record.total(), 'maximum': record.maximum()})
    messages.success(request, f'Evaluation of {record.teacher_name} saved ({record.total()}/{record.maximum()}).')
    return redirect('evaluation-detail', record.pk)


@require('evaluate_teachers')
def evaluation_view(request):
    """List evaluations with filters; print all of the filtered ones at once."""
    evaluations = _visible(request.user)
    start, end = _parse_date(request.GET.get('from')), _parse_date(request.GET.get('to'))
    teacher = request.GET.get('teacher', '').strip()
    if start:
        evaluations = evaluations.filter(date__gte=start)
    if end:
        evaluations = evaluations.filter(date__lte=end)
    if teacher:
        evaluations = evaluations.filter(Q(teacher_name__icontains=teacher) | Q(assessor__icontains=teacher))
    evaluations = list(evaluations.prefetch_related('scores'))
    if request.GET.get('print'):
        return render(request, 'eval/print.html', {'evaluations': evaluations})
    query = request.GET.copy()
    query.pop('print', None)
    return render(request, 'eval/list.html', {
        'evaluations': evaluations, 'filters': {'from': start, 'to': end, 'teacher': teacher},
        'query': query.urlencode()})


@require('evaluate_teachers')
def evaluation_detail(request, pk):
    record = get_object_or_404(_visible(request.user), pk=pk)
    return render(request, 'eval/print.html', {'evaluations': [record]})
