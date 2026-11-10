"""Score limits agreed with the school, and subject position calculation."""
from bisect import bisect_right

from src.models import StudentResult

CA1_MAX = 20
CA2_MAX = 20
EXAM_MAX = 60
BEHAVIOUR_MAX = 5
ABSENT = 'ABS'
BEHAVIOUR_FIELDS = ('conduct', 'punctuality', 'dedication', 'participation',
                    'hospitality', 'neatness', 'creativity', 'physical')


def _as_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().lstrip('-').isdigit():
        return int(value.strip())
    return None


def is_absent(value):
    return isinstance(value, str) and value.strip().upper() == ABSENT


def exam_cell(value):
    """An exam entry as it is shown: 'ABS' or a number (None if neither)."""
    return ABSENT if is_absent(value) else _as_int(value)


def exam_fields(value):
    """The StudentResult fields for a validated exam entry."""
    if is_absent(value):
        return {'exams': 0, 'exam_absent': True}
    return {'exams': _as_int(value), 'exam_absent': False}


def score_errors(ca1, ca2, exams):
    """Return a list of problems with one student's scores (empty if valid).

    Exams may also be ABS for a student absent from the exam.
    """
    errors = []
    for label, value, maximum in (('1st C.A', ca1, CA1_MAX), ('2nd C.A', ca2, CA2_MAX),
                                  ('Exams', exams, EXAM_MAX)):
        if label == 'Exams' and is_absent(value):
            continue
        number = _as_int(value)
        if number is None:
            hint = ' or ABS if absent' if label == 'Exams' else ''
            errors.append(f'{label} must be a whole number{hint} (got "{value}")')
        elif not 0 <= number <= maximum:
            errors.append(f'{label} must be between 0 and {maximum} (got {number})')
    return errors


def behaviour_errors(values):
    """`values` maps each behavioural field name to its submitted value."""
    errors = []
    for field in BEHAVIOUR_FIELDS:
        number = _as_int(values.get(field))
        if number is None or not 0 <= number <= BEHAVIOUR_MAX:
            errors.append(f'{field} must be a whole number from 0 to {BEHAVIOUR_MAX} (got "{values.get(field)}")')
    return errors


def positions_for(totals):
    """Position of each total: 1 + number of strictly higher totals (ties share)."""
    ordered = sorted(totals)
    return [1 + len(ordered) - bisect_right(ordered, t) for t in totals]


def expected_positions(results):
    """Map result id -> position: 1 + number of strictly higher totals."""
    results = list(results)
    return dict(zip((r.id for r in results), positions_for([r.total for r in results])))


def recompute_positions(student_class_id, subject_id, session_id, term_id):
    """Recalculate subject positions for one class/subject/session/term."""
    results = list(StudentResult.objects.filter(
        student_class_id=student_class_id, subject_id=subject_id,
        session_id=session_id, term_id=term_id))
    positions = expected_positions(results)
    changed = [r for r in results if r.subject_position != positions[r.id]]
    for r in changed:
        r.subject_position = positions[r.id]
    StudentResult.objects.bulk_update(changed, ['subject_position'])
    return len(changed)
