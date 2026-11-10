"""Wording used on report cards (kept exactly as the school's cards print it)."""
from django import template

register = template.Library()


@register.filter
def ordinal(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return n
    suffix = 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n}{suffix}'


@register.filter
def remark(result):
    """Subject remark from the grading key: Excellent, Good, Credit, Pass, Fail."""
    if result.exam_absent:
        return 'Absent'
    total = result.total
    if total >= 70:
        return 'Excellent'
    if total >= 60:
        return 'Good'
    if total >= 50:
        return 'Credit'
    if total >= 40:
        return 'Pass'
    return 'Fail'


RATING = {5: 'Excellent', 4: 'Good', 3: 'Fair', 2: 'Weak', 1: 'Poor'}


@register.filter
def rating(value):
    """Behaviour score with its word from the guide (5 Excellent ... 1 Poor)."""
    word = RATING.get(value) if isinstance(value, int) else None
    return word or ''


COMMENTS = (
    (70, 'Excellent performance, keep it up', 'Promoted!'),
    (60, 'Very good performance, put more effort', 'Promoted!'),
    (50, 'Good performance, you need to be more serious', 'Promoted!'),
    (40, 'Fair performance, you need to be serious with your studies', 'Promoted on Trial'),
    (0, 'Very weak performance, you need to be serious with your studies please', 'Repeated!'),
)


@register.simple_tag
def general_comment(average, term_name):
    """The general comment the school's cards print, by average; Third Term adds the promotion decision."""
    for floor, comment, decision in COMMENTS:
        if average >= floor or floor == 0:
            return f'{comment}. {decision}' if term_name == 'Third Term' else comment
