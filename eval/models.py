from django.db import models
from src.models import Subject, StudentClass, Term
import datetime

class General_Questions(models.Model):
	item = models.CharField(max_length=250)
	section = models.CharField(max_length=10)

	def __str__(self):
		return self.item

class General_Info(models.Model):
	teacher_name = models.CharField(max_length=100)
	classs = models.ForeignKey(StudentClass, null=True, on_delete=models.SET_NULL)
	subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
	topic = models.CharField(max_length=100)
	sub_topic = models.CharField(max_length=200)
	questions_items = models.ForeignKey(General_Questions, null=True, on_delete=models.SET_NULL)
	score = models.IntegerField(default=0)
	general_comment = models.TextField()
	assessor = models.CharField(max_length=100)
	upload_date = models.DateField(default=datetime.date.today)

	def __str__(self):
		return f"{self.teacher_name}"

