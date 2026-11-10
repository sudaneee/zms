"""Public result links: the QR code printed on every report card.

A link opens one student's result for one class, session and term, without
logging in. It carries the four ids and a 128-bit code computed from them
with the server's secret key, so:

- changing any id in the link (another student, term or class) makes the
  code wrong, and the page refuses it;
- the code cannot be guessed (2^128 possibilities) and is checked in
  constant time;
- a wrong link and a link to a result that does not exist get the same
  answer, so the page reveals nothing about which students exist.

Raising RESULT_LINK_VERSION in settings invalidates every link printed so far
(for example after a printed batch is lost).
"""
import base64

import segno
from django.conf import settings
from django.shortcuts import render
from django.urls import reverse
from django.utils.crypto import constant_time_compare, salted_hmac
from django.views.decorators.cache import never_cache

from src.models import Session, StudentClass, StudentResult, Term
from src.signing import active_approvals


def _code(payload):
    salt = f'zms.result-link.v{settings.RESULT_LINK_VERSION}'
    digest = salted_hmac(salt, payload, algorithm='sha256').digest()[:16]
    return base64.urlsafe_b64encode(digest).decode().rstrip('=')


def _payload(student_id, class_id, session_id, term_id):
    return f'{student_id}-{class_id}-{session_id}-{term_id}'


def result_link(request, student, student_class, session, term):
    """Absolute URL and QR image (SVG data URI) for one student's card."""
    payload = _payload(student.id, student_class.id, session.id, term.id)
    path = reverse('public_result', args=[payload, _code(payload)])
    base = settings.PUBLIC_BASE_URL.rstrip('/')
    url = f'{base}{path}' if base else request.build_absolute_uri(path)
    return {'url': url, 'qr': segno.make(url, error='m').svg_data_uri(scale=3, border=1)}


def _refuse(request):
    response = render(request, 'src/public_result_invalid.html', status=404)
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response


@never_cache
def public_result(request, payload, code):
    parts = payload.split('-')
    if len(parts) != 4 or not all(p.isdigit() for p in parts) or not constant_time_compare(code, _code(payload)):
        return _refuse(request)
    student_id, class_id, session_id, term_id = map(int, parts)
    student_class = StudentClass.objects.filter(pk=class_id).select_related('section').first()
    session = Session.objects.filter(pk=session_id).first()
    term = Term.objects.filter(pk=term_id).first()
    if None in (student_class, session, term) or not StudentResult.objects.filter(
            student_id=student_id, student_class=student_class, session=session, term=term).exists():
        return _refuse(request)

    from src.reports import card_context, card_template
    context = card_context(request, student_class, session, term, student_ids={student_id})
    if not context['results']:
        return _refuse(request)
    approvals = active_approvals(student_class, session, term)
    context.update(public_view=True, head_approval=approvals.get('head'))
    if approvals.get('head'):
        from src.signing import approval_status
        context['approval_status'] = approval_status(approvals['head'], student_id)
    response = render(request, card_template(student_class), context)
    response['X-Robots-Tag'] = 'noindex, nofollow'
    response['Referrer-Policy'] = 'no-referrer'
    return response
