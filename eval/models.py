from django.conf import settings
from django.db import models

from src.models import StudentClass, Subject

# Rating scale used on the evaluation form and printout.
RATINGS = (
    (5, 'Above Average'),
    (4, 'Average'),
    (3, 'Satisfactory'),
    (2, 'Not satisfactory'),
    (1, 'Deficient'),
)
RATING_LABELS = dict(RATINGS)

SECTION_TITLES = {
    'A': 'Section A: Lesson Preparation and Presentation',
    'B': 'Section B: Class Management and Communication Skills',
    'C': 'Section C: Evaluation Skills and Personality/Attitude',
}


class General_Questions(models.Model):
    """An item on the evaluation form; `section` is A, B or C."""
    item = models.CharField(max_length=250)
    section = models.CharField(max_length=10)

    class Meta:
        ordering = ('section', 'id')
        verbose_name = 'evaluation question'

    def __str__(self):
        return self.item


class General_Info(models.Model):
    """Evaluations recorded before the upgrade: one row per question, grouped
    only by teacher name and date. Kept unchanged; migration 0004 copied them
    into Evaluation/EvaluationScore."""
    teacher_name = models.CharField(max_length=100)
    classs = models.ForeignKey(StudentClass, null=True, on_delete=models.SET_NULL)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    topic = models.CharField(max_length=100)
    sub_topic = models.CharField(max_length=200)
    questions_items = models.ForeignKey(General_Questions, null=True, on_delete=models.SET_NULL)
    score = models.IntegerField(default=0)
    general_comment = models.TextField()
    assessor = models.CharField(max_length=100)
    upload_date = models.DateField()

    class Meta:
        verbose_name = 'legacy evaluation row'

    def __str__(self):
        return f"{self.teacher_name}"


class Evaluation(models.Model):
    """One lesson observation of one teacher."""
    teacher_name = models.CharField(max_length=100)
    student_class = models.ForeignKey(StudentClass, null=True, blank=True, on_delete=models.PROTECT)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    topic = models.CharField(max_length=200)
    sub_topic = models.CharField(max_length=200, blank=True)
    general_comment = models.TextField(blank=True)
    assessor = models.CharField(max_length=100)
    date = models.DateField(db_index=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.PROTECT, related_name='+')
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-date', '-id')

    def __str__(self):
        return f'{self.teacher_name}, {self.subject}, {self.date:%d-%m-%Y}'

    def sections(self):
        """[(title, [score rows], subtotal, maximum)] in form order."""
        rows = {}
        for s in self.scores.select_related('question').order_by('question__section', 'question_id'):
            rows.setdefault(s.question.section, []).append(s)
        return [(SECTION_TITLES.get(key, f'Section {key}'), items, sum(i.score for i in items), 5 * len(items))
                for key, items in sorted(rows.items())]

    def total(self):
        return sum(s.score for s in self.scores.all())

    def maximum(self):
        return 5 * self.scores.count()

    def percent(self):
        maximum = self.maximum()
        return round(self.total() * 100 / maximum) if maximum else 0


class EvaluationScore(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name='scores')
    question = models.ForeignKey(General_Questions, on_delete=models.PROTECT)
    score = models.PositiveSmallIntegerField(choices=RATINGS)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('evaluation', 'question'), name='one_score_per_question')]

    @property
    def remark(self):
        return RATING_LABELS.get(self.score, '')
