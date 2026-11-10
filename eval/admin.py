from django.contrib import admin

from eval.models import Evaluation, EvaluationScore, General_Info, General_Questions


class EvaluationScoreInline(admin.TabularInline):
    model = EvaluationScore
    extra = 0


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('teacher_name', 'subject', 'student_class', 'date', 'assessor')
    search_fields = ('teacher_name', 'assessor', 'topic')
    list_filter = ('date',)
    inlines = [EvaluationScoreInline]


@admin.register(General_Questions)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('item', 'section')


@admin.register(General_Info)
class LegacyAdmin(admin.ModelAdmin):
    """Pre-upgrade rows, kept for reference only."""
    list_display = ('teacher_name', 'upload_date', 'questions_items', 'score')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
