from django.contrib import admin
from src.models import Subject, StudentClass, Session, Term, Student, StudentResult, StudentBehaviouralAssessment, signature, sets

class StudentAdmin(admin.ModelAdmin):
    search_fields = ['id','student_name',]
    list_display = ['student_name', 'student_class']


# Register your models here.
admin.site.register(Subject)
admin.site.register(StudentClass)
admin.site.register(Session)
admin.site.register(Term)
admin.site.register(Student, StudentAdmin)
admin.site.register(StudentResult)
admin.site.register(StudentBehaviouralAssessment)
admin.site.register(signature)
admin.site.register(sets)

