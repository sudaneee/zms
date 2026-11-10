from django.shortcuts import render, redirect
from django.http import HttpResponse
from src.models import Subject, StudentClass, Session, Term, Student, StudentResult, StudentBehaviouralAssessment, signature, sets
from django.db import connection
from django.contrib.auth import authenticate
from django.contrib import messages
from django.contrib.auth.models import User, auth
import openpyxl
from openpyxl import Workbook
import datetime
from openpyxl.writer.excel import save_virtual_workbook
from eval.models import General_Info, General_Questions
from itertools import chain
# cursor to move around the database

def evaluation(request):
    global section_a
    global section_b
    global section_c
    global classs
    global subject
    global context
    global section_a_id
    global section_b_id
    global section_c_id
    global items_id
    global items


    section_a =General_Questions.objects.filter(section="A").all()
    section_b =General_Questions.objects.filter(section="B").all()
    section_c =General_Questions.objects.filter(section="C").all()
    classs = StudentClass.objects.all()
    subject = Subject.objects.all()
    context = {
    'classs': classs,
    'subject': subject,
    'section_a': section_a,
    'section_b': section_b,
    'section_c': section_c,

    }		


    items_id = [i.id for i in General_Questions.objects.all()]



    if request.method == 'POST':
        name = request.POST['name']
        tbl1_score = request.POST.getlist('tbl1-grade')
        tbl2_score = request.POST.getlist('tbl2-grade')
        tbl3_score = request.POST.getlist('tbl3-grade')
        a_scores = []
        b_scores = []
        c_scores = []

        #--------------- getting inputs for table 1------------------
        for i in tbl1_score:
            if i == "Above Average":
                score = 5
            elif i == "Average":
                score = 4
            elif i == "Satisfactory":
                score = 3
            elif i == "Not satisfactory":
                score == 2
            elif i == "Deficient":
                score = 1
            else: 
                score = 0
            a_scores.append(score)

        print(a_scores)

        #--------------- getting inputs for table 2------------------
        for i in tbl2_score:
            if i == "Above Average":
                score = 5
            elif i == "Average":
                score = 4
            elif i == "Satisfactory":
                score = 3
            elif i == "Not satisfactory":
                score == 2
            elif i == "Deficient":
                score = 1
            else: 
                score = 0
            b_scores.append(score)

        print(b_scores)

        #--------------- getting inputs for table 3------------------
        for i in tbl3_score:
            if i == "Above Average":
                score = 5
            elif i == "Average":
                score = 4
            elif i == "Satisfactory":
                score = 3
            elif i == "Not satisfactory":
                score == 2
            elif i == "Deficient":
                score = 1
            else: 
                score = 0
            c_scores.append(score)

        print(b_scores)

        teacher_name = request.POST['name']
        class_taught = request.POST['class']
        subject_taught = request.POST['subject']
        topic_taught = request.POST['topic']
        sub_topic_taught = request.POST['sub-topic']
        general_comment = request.POST['g_comment']
        assessors_name = request.POST['a_name']
        all_scores = a_scores + b_scores + c_scores
        
        for i, j in zip(all_scores, General_Questions.objects.all()):
            temp = General_Info(teacher_name = teacher_name,
                classs = StudentClass.objects.get(class_name=class_taught),
                subject = Subject.objects.get(subject_name=subject_taught),
                topic = topic_taught,
                sub_topic = sub_topic_taught,
                questions_items = General_Questions.objects.get(id=j.id),
                score = i,
                general_comment = general_comment,
                assessor = assessors_name
                )
            temp.save()
    
        messages.success(request, 'Submitted Successfully')

        #print(another)

        return render(request, "eval/index.html", context)
        
    else:
        return render(request, "eval/index.html", context)

def evaluation_view(request):

    if request.method == 'POST' and "form1" in request.POST:
        date = request.POST['date']

        somedate = datetime.date.today()
        results = General_Info.objects.filter(upload_date=date).all()

        bulk = {}

        for result in results:
            a_score = 0
            a_items = []
            t_score = []
            for questions_items in results:
                if questions_items.teacher_name == result.teacher_name:
                    a_items.append(questions_items)
                    a_score += questions_items.score
                    classs =questions_items.classs
                    subject =questions_items.subject
                    topic =questions_items.topic
                    sub_topic =questions_items.sub_topic
                    general_comment =questions_items.general_comment
                    upload_date = questions_items.upload_date
                    assessor =questions_items.assessor
                    t_score.append(questions_items.score)
                    t_score_a = t_score[0:8]
                    t_score_b = t_score[8:14]
                    t_score_c = t_score[14:20]
                    a_t_score = sum(t_score_a)
                    b_t_score = sum(t_score_b)
                    c_t_score = sum(t_score_c)
                    t_total = sum(t_score)


        
                    

                bulk[result.teacher_name] = {
                "teacher_name": result.teacher_name,
                "a_items": a_items,
                "a_score": a_score,
                "classs": classs,
                "subject": subject,
                "topic": topic,
                "sub_topic": sub_topic,
                "general_comment": general_comment,
                "assessor": assessor,
                't_total': t_total,
                "t_score_a": t_score_a,
                "a_t_score": a_t_score,
                "b_t_score": b_t_score,
                "c_t_score": c_t_score,
                "upload_date":upload_date,

                }

        context = {
            'results': bulk
        }

        return render(request, 'eval/eval-resut.html', context)
    else:
        classes = StudentClass.objects.all()
        context = {
            'classes': classes
        }
        return render(request, 'eval/eval_resut1.html', context)

