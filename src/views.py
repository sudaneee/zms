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
import numpy as np

# cursor to move around the database

c = connection.cursor()

allSessions = Session.objects.all()
allTerms = Term.objects.all()
allClasses = StudentClass.objects.all()
allSubjects = Subject.objects.all()
generalContext = {
    'sessions': allSessions,
    'terms': allTerms,
    'classes': allClasses,
    'subjects': allSubjects,
    }

def home(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = auth.authenticate(username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return render(request, 'src/dashboard.html')

        else:
            messages.error(request, 'Incorrect Login-in Details')
            return render(request, 'src/welcome.html')

    else:
        return render(request, 'src/welcome.html')
def side_nav(request):
    return render(request, 'src/index.html')
def ResultUpload(request):
    if request.user.is_authenticated:
        classes = StudentClass.objects.all()
        subjects = Subject.objects.all()
        context = {
            'subjects': allSubjects,
            'classes': allClasses,
            'sessions': allSessions,
            'terms': allTerms,
        }
        if "GET" == request.method:
            return render(request, 'src/stdupload.html', generalContext)
        else:

            session = request.POST['session']
            term = request.POST['term']
            classs = request.POST['class']
            subject = request.POST['subject']

            #---------------Getting IDs of the Subjects, Session, and Class---------------------
            ses = Session.objects.get(session_name=session)
            session_id = ses.id

            trm = Term.objects.get(term_name=term)
            term_id = trm.id

            clas = StudentClass.objects.get(class_name=classs)
            class_id = clas.id

            subj = Subject.objects.get(subject_name=subject)
            subject_id = subj.id

            excel_file = request.FILES["excel_file"]

            # you may put validations here to check extension or file size

            wb = openpyxl.load_workbook(excel_file)

            # getting a particular sheet by name out of many sheets
            worksheet = wb["result"]
            ids = []
            ca1s = []
            ca2s = []
            exams = []
            ses_ids = []
            trm_ids = []
            clas_ids = []
            subj_ids =[]
            total_score = []
            for i, j, k, l in zip((worksheet['A']), (worksheet['C']), (worksheet['D']), (worksheet['E'])):
                ids.append(i.value)
                ca1s.append(j.value)
                ca2s.append(k.value)
                exams.append(l.value)
                ses_ids.append(session_id)
                trm_ids.append(term_id)
                clas_ids.append(class_id)
                subj_ids.append(subject_id)


            #------------removing first row of the excel-----------
            f_ids = ids[1:]
            f_ca1s = ca1s[1:]
            f_ca2s = ca2s[1:]
            f_exams = exams[1:]

            #-----------coverting to interger list----------------
            a_ids = [int(i) for i in f_ids]
            a_ca1s = [int(i) for i in f_ca1s]
            a_ca2s = [int(i) for i in f_ca2s]
            a_exams = [int(i) for i in f_exams]

            #--------------sumation of the CA to get Total Marks
            for i in range(len(f_ca1s)):
                total_score.append(a_ca1s[i] + a_ca2s[i] + a_exams[i])
            print(total_score)

            position = []
            for total in total_score:
                count = 0
                for pos in total_score:
                    if pos > total:
                        count += 1
                position.append(count +1)


            clso = int(class_id)
            sess = int(session_id)
            trm = int(term_id)
            sbj = int(subject_id)

            c = connection.cursor()



            queryset = StudentResult.objects.filter(session=sess, term=trm, student_class=clso, subject=sbj).exists()
            if queryset:
                print("record is already there")
            else:

                c.executemany('INSERT INTO src_studentresult (ca1, ca2, exams, total, subject_position, student_id, student_class_id, subject_id, session_id, term_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', zip(a_ca1s, a_ca2s, a_exams, total_score, position, a_ids, clas_ids, subj_ids, ses_ids, trm_ids))
                connection.commit()
                c.close()
                messages.info(request, 'Result Uploaded Successfully')

            s = "ZMS/SS/12"



        return render(request,'src/stdupload.html', context)
    else:
        return render(request, 'src/welcome.html')


def stdcreate(request):
    if request.user.is_authenticated:
        classes = StudentClass.objects.all()
        context = {
            'classes': allClasses,
        }



        if "GET" == request.method:
            return render(request, 'src/stdcreate.html', context)
        else:
            classs = request.POST['class']


            #---------------Getting IDs of the Class---------------------

            clas = StudentClass.objects.get(class_name=classs)
            class_id = clas.id

            excel_file = request.FILES["excel_file"]

            # you may put validations here to check extension or file size

            wb = openpyxl.load_workbook(excel_file)

            # getting a particular sheet by name out of many sheets
            worksheet = wb["Sheet1"]
            print(worksheet)
            names = []
            clas_ids = []

            for i in worksheet['A']:
                names.append(i.value)
                clas_ids.append(class_id)

            #------------removing first row of the excel-----------

            f_names = names
            f_clas_ids = clas_ids
            a_clas_ids = [int(i) for i in f_clas_ids]
            print(f_clas_ids)




            c = connection.cursor()

            c.executemany('INSERT INTO src_student (student_name, student_class_id) VALUES (?, ?)', zip(f_names, a_clas_ids))
            connection.commit()
            c.close()
            messages.info(request, 'Record Uploaded Successfully')

            status_set = Student.objects.filter(student_class=clas).all()
            for i in status_set:
                i.status = True
                i.gender = "Male"
                i.category = "Normal"
                i.save()



        return render(request, 'src/stdcreate.html', context)
    else:
        return render(request, 'src/welcome.html')

def resultcreate(request):
    global students
    global subject
    global term
    global session
    global classs
    global class_id
    global session_id
    global term_id
    global subject_id
    global student_id

    if request.user.is_authenticated:

        if request.method == 'POST' and "form1" in request.POST:

            session = request.POST['session']
            term = request.POST['term']
            classs = request.POST['class']
            subject = request.POST['subject']

            ses = Session.objects.get(session_name=session)
            session_id = ses.id

            trm = Term.objects.get(term_name=term)
            term_id = trm.id

            clas = StudentClass.objects.get(class_name=classs)
            class_id = clas.id

            subj = Subject.objects.get(subject_name=subject)
            subject_id = subj.id

            students = Student.objects.filter(student_class=class_id, status=True).all()
            student_id = []
            for i in students:
                student_id.append(i.id)


            subjects = Subject.objects.all()
            classes = StudentClass.objects.all()
            sessions = Session.objects.all()
            terms = Term.objects.all()
            generalContext['students'] = students
            context = {
                'subjects': subjects,
                'classes': classes,
                'sessions': sessions,
                'terms': terms,
                'students': students
            }

            return render(request, 'src/resultcreate.html', generalContext)

        if request.method == 'POST' and "form2" in request.POST:
            ses_ids = []
            trm_ids = []
            clas_ids = []
            subj_ids =[]
            total_score = []

            #ids = request.POST.getlist('id')
            names = request.POST.getlist('name')
            ca1s = request.POST.getlist('ca1')
            ca1s2 = [int(i) for i in ca1s]
            ca2s = request.POST.getlist('ca2')
            ca2s2 = [int(i) for i in ca2s]
            exams = request.POST.getlist('exams')
            exams2 = [int(i) for i in exams]
            for i in range(len(ca1s2)):
                total_score.append(ca1s2[i] + ca2s2[i] + exams2[i])

            position = []
            for total in total_score:
                count = 0
                for pos in total_score:
                    if pos > total:
                        count += 1
                position.append(count +1)

            for i in students:
                ses_ids.append(session_id)
                trm_ids.append(term_id)
                clas_ids.append(class_id)
                subj_ids.append(subject_id)

            clso = int(class_id)
            sess = int(session_id)
            trm = int(term_id)
            sbj = int(subject_id)

            c = connection.cursor()

            queryset = StudentResult.objects.filter(session=sess, term=trm, student_class=clso, subject=sbj).exists()
            if queryset:
                print("record is already there")
            else:
                c.executemany('INSERT INTO src_studentresult (ca1, ca2, exams, total, subject_position, student_id, student_class_id, subject_id, session_id, term_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', zip(ca1s, ca2s, exams, total_score, position, student_id, clas_ids, subj_ids, ses_ids, trm_ids))
                connection.commit()
                c.close()
                messages.info(request, 'Result Uploaded Successfully')




            subjects = Subject.objects.all()
            classes = StudentClass.objects.all()
            sessions = Session.objects.all()
            terms = Term.objects.all()
            context = {
                'subjects': subjects,
                'classes': classes,
                'students': students
            }

            return render(request, 'src/resultcreate.html', context)


        else:
            subjects = Subject.objects.all()
            classes = StudentClass.objects.all()
            context = {
                'subjects': subjects,
                'classes': classes
            }
            return render(request, 'src/resultcreate.html', generalContext)
    else:
        return render(request, 'src/welcome.html')

def updateresult(request):
    global students
    global subject
    global term
    global session
    global classs
    global class_id
    global session_id
    global term_id
    global subject_id
    global result_ids
    if request.user.is_authenticated:

        if request.method == 'POST' and "form1" in request.POST:

            session = request.POST['session']
            term = request.POST['term']
            classs = request.POST['class']
            subject = request.POST['subject']

            ses = Session.objects.get(session_name=session)
            session_id = ses.id

            trm = Term.objects.get(term_name=term)
            term_id = trm.id

            clas = StudentClass.objects.get(class_name=classs)
            class_id = clas.id

            subj = Subject.objects.get(subject_name=subject)
            subject_id = subj.id

            students = Student.objects.filter(student_class=class_id).all()
            student_id = []




            all_results = StudentResult.objects.filter(session=session_id, term=term_id, student_class=class_id,subject=subject_id).all()

            result_ids = StudentResult.objects.filter(session=session_id, term=term_id, student_class=class_id,subject=subject_id).values_list('id', flat=True)
            print(result_ids)


            for i in students:
                student_id.append(i.id)

            subjects = Subject.objects.all()
            classes = StudentClass.objects.all()
            sessions = Session.objects.all()
            terms = Term.objects.all()

            result_students_list = zip(all_results, students)
            context = {
                'subjects': subjects,
                'classes': classes,
                'all_results': all_results,
                'result_students_list': result_students_list
            }

            return render(request, 'src/updateresult.html', context)

        if request.method == 'POST' and "form2" in request.POST:
            ses_ids = []
            trm_ids = []
            clas_ids = []
            subj_ids =[]
            total_score = []

            ids = request.POST.getlist('id')
            names = request.POST.getlist('name')
            ca1s = request.POST.getlist('ca1')
            ca1s2 = [int(i) for i in ca1s]
            ca2s = request.POST.getlist('ca2')
            ca2s2 = [int(i) for i in ca2s]
            exams = request.POST.getlist('exams')
            exams2 = [int(i) for i in exams]
            for i in range(len(ca1s2)):
                total_score.append(ca1s2[i] + ca2s2[i] + exams2[i])
            print(total_score)

            position = []
            for total in total_score:
                count = 0
                for pos in total_score:
                    if pos > total:
                        count += 1
                position.append(count +1)


            print(ca1s)

            for i in students:
                ses_ids.append(session_id)
                trm_ids.append(term_id)
                clas_ids.append(class_id)
                subj_ids.append(subject_id)

            c = connection.cursor()

            c.executemany("""UPDATE src_studentresult SET ca1=?, ca2=?, exams=?, total=?, subject_position=? WHERE
                id=? AND student_class_id=? AND subject_id=? AND session_id=? AND term_id=?""",
                zip(ca1s, ca2s, exams, total_score, position, result_ids, clas_ids, subj_ids, ses_ids, trm_ids))
            connection.commit()
            c.close()
            messages.info(request, 'Result Updated Successfully')

            subjects = Subject.objects.all()
            classes = StudentClass.objects.all()
            sessions = Session.objects.all()
            terms = Term.objects.all()
            context = {
                'subjects': subjects,
                'classes': classes,
                'students': students
            }

            return render(request, 'src/updateresult.html', context)
        else:
            subjects = Subject.objects.all()
            classes = StudentClass.objects.all()
            context = {
                'subjects': subjects,
                'classes': classes
            }
            return render(request, 'src/updateresult.html', generalContext)
    else:
        return render(request, 'src/welcome.html')


def single_result_update(request):
    global students
    global subject
    global term
    global session
    global classs
    global class_id
    global session_id
    global term_id
    global subject_id
    global student_qr_id
    global student_id


    if request.user.is_authenticated:

        if request.method == 'POST' and "form1" in request.POST:
            session = request.POST['session']
            term = request.POST['term']
            classs = request.POST['class']
            subject = request.POST['subject']
            student_id = request.POST['student_id']

            ses = Session.objects.get(session_name=session)
            session_id = ses.id

            trm = Term.objects.get(term_name=term)
            term_id = trm.id

            clas = StudentClass.objects.get(class_name=classs)
            class_id = clas.id

            subj = Subject.objects.get(subject_name=subject)
            subject_id = subj.id

            student = []
            student.append(student_id)


            get_student = StudentResult.objects.get(student=student_id, session=session_id, term=term_id, student_class=class_id, subject=subject_id)
            subjects = Subject.objects.all()
            classes = StudentClass.objects.all()
            context = {
                'subjects': subjects,
                'classes': classes,
                'get_student': get_student,
                'student_id': student_id
                }
            return render(request, 'src/single_result_update.html', context)




        if request.method == 'POST' and "form2" in request.POST:


            ca1 = request.POST['ca1']
            ca2 = request.POST['ca2']
            exams = request.POST['exams']

            total_score = int(ca1) + int(ca2) + int(exams)



            queryy = StudentResult.objects.get(student=student_id, session=session_id, term=term_id, student_class=class_id, subject=subject_id)

            queryy.ca1 = ca1
            queryy.save()
            queryy.ca2 = ca2
            queryy.save()
            queryy.exams = exams
            queryy.save()
            queryy.total = total_score
            queryy.save()


            subjects = Subject.objects.all()
            classes = StudentClass.objects.all()
            context = {
                'subjects': subjects,
                'classes': classes
                }
            return render(request, 'src/single_result_update.html', context)


        else:
            subjects = Subject.objects.all()
            classes = StudentClass.objects.all()
            context = {
                'subjects': subjects,
                'classes': classes
                }
            return render(request, 'src/single_result_update.html', generalContext)
    else:
        return render(request, 'src/welcome.html')


def result_view(request):
    global class_id
    global session_id
    global term_id

    if request.user.is_authenticated:

        if request.method == 'POST' and "form1" in request.POST:
            classes = StudentClass.objects.all()

            context = {
                'classes': classes
                }

            session = request.POST['session']
            term = request.POST['term']
            classs = request.POST['class']

            ses = Session.objects.get(session_name=session)
            session_id = ses.id

            trm = Term.objects.get(term_name=term)
            term_id = trm.id

            clas = StudentClass.objects.get(class_name=classs)
            class_id = clas.id

            results = StudentResult.objects.filter(session=session_id, term=term_id, student_class=class_id)
            bulk = {}



            for result in results:
                ca1_total = 0
                ca2_total = 0
                exams_total = 0
                total = 0
                subjects = []
                for subject in results:
                    if subject.student == result.student:
                        subjects.append(subject)
                        ca1_total += subject.ca1
                        ca2_total += subject.ca2
                        exams_total += subject.exams
                        total += subject.total
                        subject_pos = subject.subject_position
                        grade = subject.grade
                        terms = subject.term
                        sesss = subject.session
                        classs = subject.student_class
                        avr = total/len(subjects)



                    bulk[result.student] = {
                    "student": result.student,
                    "subjects": subjects,
                    "ca1_total": ca1_total,
                    "ca2_total": ca1_total,
                    "exams_total": exams_total,
                    "total": total,
                    "grade": grade,
                    "subject_pos": subject_pos,
                    "terms": terms,
                    "sesss": sesss,
                    "classs": classs,
                    "overal_total": total,
                    "average": round(avr, 2)



                    }
            print(result.student)
            classes = StudentClass.objects.all()
            bhv = StudentBehaviouralAssessment.objects.filter(session=session_id, term=term_id, student_class=class_id)
            signs = signature.objects.filter(classs=classs).first()
            some_images = sets.objects.first()

            f_classs = str(classs)
            date = datetime.datetime.now()

            context = {
                'date': date,
                'f_classs': f_classs,
                'classes': classes,
                'results': bulk,
                'bhv': bhv,
                'signs': signs,
                'some_images':some_images,
                'p_term': term,
            }



            return render(request, 'src/single_result_view.html', context)

        else:
            classes = StudentClass.objects.all()

            context = {
                'classes': classes
                }

            return render(request, 'src/result_view.html', generalContext)

    else:
        return render(request, 'src/welcome.html')

def setting_position(request):
    if request.user.is_authenticated:

        c = connection.cursor()

        c.execute("""UPDATE src_studentresult SET subject_position=( SELECT count(*) FROM src_studentresult AS i WHERE i.total > src_studentresult.total AND i.student_class_id = src_studentresult.student_class_id AND i.subject_id = src_studentresult.subject_id AND i.session_id = src_studentresult.session_id AND i.term_id = src_studentresult.term_id) + 1;""")
        connection.commit()
        c.close()
        messages.info(request, 'Position Set Successfully')
        return render(request, 'src/dashboard.html')
    else:
        pass

def settings(request):
    global students
    global subject
    global term
    global session
    global classs
    global class_id
    global session_id
    global term_id
    global subject_id
    global student_id
    if request.user.is_authenticated:



        if request.method == 'POST' and "form1" in request.POST:

            session = request.POST['session']
            term = request.POST['term']
            classs = request.POST['class']


            ses = Session.objects.get(session_name=session)
            session_id = ses.id

            trm = Term.objects.get(term_name=term)
            term_id = trm.id

            clas = StudentClass.objects.get(class_name=classs)
            class_id = clas.id

            students = Student.objects.filter(student_class=class_id).all()
            student_id = []

            for i in students:
                student_id.append(i.id)
            print(student_id)

            classes = StudentClass.objects.all()

            generalContext["students"] = students
            context = {
                'classes': classes,
                'students': students
                }

            return render(request, 'src/settings.html', generalContext)

        if request.method == 'POST' and "form2" in request.POST:

            ses_ids = []
            trm_ids = []
            clas_ids = []

            ids = request.POST.getlist('id')
            conduct = request.POST.getlist('conduct')
            punc = request.POST.getlist('punctuality')
            ded = request.POST.getlist('dedication')
            part = request.POST.getlist('participation')
            hosp = request.POST.getlist('hospitality')
            creat= request.POST.getlist('creativity')
            phy = request.POST.getlist('physical')
            neat = request.POST.getlist('neatness')

            for i in student_id:
                ses_ids.append(session_id)
                trm_ids.append(term_id)
                clas_ids.append(class_id)



            queryset = StudentBehaviouralAssessment.objects.filter(session=session_id, term=term_id, student_class=class_id).exists()
            if queryset:
                print("record is already there")
            else:
                c = connection.cursor()
                c.executemany("""INSERT INTO src_studentbehaviouralassessment (conduct, punctuality, dedication, participation, hospitality,
                    neatness, creativity, physical, session_id, student_id, student_class_id, term_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    zip(conduct, punc, ded, part, hosp, neat, creat, phy, ses_ids, student_id, clas_ids, trm_ids))
                connection.commit()
                c.close()


            classes = StudentClass.objects.all()

            context = {
                'classes': classes
                }

            return render(request, 'src/settings.html', generalContext)



        else:
            classes = StudentClass.objects.all()

            context = {
                'classes': classes
                }

            return render(request, 'src/settings.html', generalContext)
    else:
        return render(request, 'src/welcome.html')


def single_result_view(request):
    global subject
    global term
    global session
    global classs
    global class_id
    global session_id
    global term_id
    global subject_id
    global student_qr_id
    global students

    if request.method == 'POST' and "form1" in request.POST:
        session = request.POST['session']
        term = request.POST['term']
        student_id = request.POST['student_id']






        ses = Session.objects.get(session_name=session)
        session_id = ses.id

        trm = Term.objects.get(term_name=term)
        term_id = trm.id


        results = StudentResult.objects.filter(session=session_id, term=term_id, student=int(student_id))
        bulk = {}

        for result in results:
            ca1_total = 0
            ca2_total = 0
            exams_total = 0
            total = 0
            subjects = []
            for subject in results:
                if subject.student == result.student:
                    subjects.append(subject)
                    ca1_total += subject.ca1
                    ca2_total += subject.ca2
                    exams_total += subject.exams
                    total += subject.total
                    subject_pos = subject.subject_position
                    grade = subject.grade
                    terms = subject.term
                    sesss = subject.session
                    classs = subject.student_class
                    avr = total/len(subjects)



                bulk[result.student] = {
                "student": result.student,
                "subjects": subjects,
                "ca1_total": ca1_total,
                "ca2_total": ca1_total,
                "exams_total": exams_total,
                "total": total,
                "grade": grade,
                "subject_pos": subject_pos,
                "terms": terms,
                "sesss": sesss,
                "classs": classs,
                "overal_total": total,
                "average": round(avr, 2)



                }
        bhv = StudentBehaviouralAssessment.objects.filter(session=session_id, term=term_id, student=student_id)
        # signs = signature.objects.filter(classs=classs).first()
        some_images = sets.objects.first()
        print(some_images)


        context = {
            'results': bulk,
            'bhv': bhv,
            # 'signs': signs,
            'some_images':some_images
        }

        return render(request, 'src/single_result_view.html', context)

    else:

        return render(request, 'src/single_result_view1.html', generalContext)

def score_sheet(request):
    if request.method == 'POST' and "form1" in request.POST:
        classs = request.POST['class']
        class_id = StudentClass.objects.get(class_name=classs)
        class_id = class_id.id


        dukka = Student.objects.filter(student_class=class_id).all()
        context = {
            'classs':classs,
            'all': dukka
        }

        return render(request, 'src/score_sheet1.html', context)
    else:
        classes = StudentClass.objects.all()
        context = {
            'classes': classes
        }
        return render(request, 'src/score_sheet.html', context)

def excel_score_sheet(request):
    if request.user.is_authenticated:
        if request.method == 'POST' and "form1" in request.POST:
            classs = request.POST['class']
            subject = request.POST['subject']
            template_name = classs + "-" + subject

            class_id = StudentClass.objects.get(class_name=classs)
            class_id = class_id.id

            ids = []
            names = []
            ca1 = []
            ca2 = []
            exams = []

            dukka = Student.objects.filter(student_class=class_id).all()

            for i in dukka:
                ids.append(i.id)
                names.append(i.student_name)
                ca1.append(0)
                ca2.append(0)
                exams.append(0)


            book = Workbook()
            sheet = book.active
            sheet.title = 'result'


            sheet['A1'] = "ID NO"
            sheet['B1'] = "Names"
            sheet['C1'] = "1st C.A"
            sheet['D1'] = "2nd C.A"
            sheet['E1'] = "Exams"
            y=2

            for x in range(len(ids)):
                cell_to_write = sheet.cell(row=y, column=1)
                cell_to_write.value = ids[x]
                cell_to_write = sheet.cell(row=y, column=2)
                cell_to_write.value = names[x]
                cell_to_write = sheet.cell(row=y, column=3)
                cell_to_write.value = ca1[x]
                cell_to_write = sheet.cell(row=y, column=4)
                cell_to_write.value = ca2[x]
                cell_to_write = sheet.cell(row=y, column=5)
                cell_to_write.value = exams[x]
                y += 1

            response = HttpResponse(content=save_virtual_workbook(book), content_type='application/ms-excel',)
            response['Content-Disposition'] = 'attachment; filename="%s.xlsx"' % template_name
            return response

        else:
            classes = StudentClass.objects.all()
            subjects = Subject.objects.all()
            context = {
                'classes': classes,
                'subjects': subjects
            }
            return render(request, 'src/score_sheet.html', context)
    else:
        return render(request, 'src/welcome.html')


def logout(request):
    auth.logout(request)
    return redirect('/')

def not_uploaded_results(request):
    if request.user.is_authenticated:
        classes = StudentClass.objects.all()
        subjects = Subject.objects.all()
        context = {
            'subjects': subjects,
            'classes': classes
        }
        if "GET" == request.method:
            return render(request, 'src/stdupload.html', context)
        else:

            session = request.POST['session']
            term = request.POST['term']
            classs = request.POST['class']
            subject = request.POST['subject']

            #---------------Getting IDs of the Subjects, Session, and Class---------------------
            ses = Session.objects.get(session_name=session)
            session_id = ses.id

            trm = Term.objects.get(term_name=term)
            term_id = trm.id

            clas = StudentClass.objects.get(class_name=classs)
            class_id = clas.id

            subj = Subject.objects.get(subject_name=subject)
            subject_id = subj.id

            excel_file = request.FILES["excel_file"]

            # you may put validations here to check extension or file size

            wb = openpyxl.load_workbook(excel_file)

            # getting a particular sheet by name out of many sheets
            worksheet = wb["result"]
            ids = []
            ca1s = []
            ca2s = []
            exams = []
            ses_ids = []
            trm_ids = []
            clas_ids = []
            subj_ids =[]
            total_score = []
            for i, j, k, l in zip((worksheet['A']), (worksheet['C']), (worksheet['D']), (worksheet['E'])):
                ids.append(i.value)
                ca1s.append(j.value)
                ca2s.append(k.value)
                exams.append(l.value)
                ses_ids.append(session_id)
                trm_ids.append(term_id)
                clas_ids.append(class_id)
                subj_ids.append(subject_id)


            #------------removing first row of the excel-----------
            f_ids = ids[1:]
            f_ca1s = ca1s[1:]
            f_ca2s = ca2s[1:]
            f_exams = exams[1:]

            #-----------coverting to interger list----------------
            a_ids = [int(i) for i in f_ids]
            a_ca1s = [int(i) for i in f_ca1s]
            a_ca2s = [int(i) for i in f_ca2s]
            a_exams = [int(i) for i in f_exams]

            #--------------sumation of the CA to get Total Marks
            for i in range(len(f_ca1s)):
                total_score.append(a_ca1s[i] + a_ca2s[i] + a_exams[i])
            print(total_score)

            clso = int(class_id)
            sess = int(session_id)
            trm = int(term_id)
            sbj = int(subject_id)

            c = connection.cursor()





            c.executemany('INSERT INTO src_studentresult (ca1, ca2, exams, total, student_id, student_class_id, subject_id, session_id, term_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', zip(a_ca1s, a_ca2s, a_exams, total_score, a_ids, clas_ids, subj_ids, ses_ids, trm_ids))
            connection.commit()
            c.close()
            messages.info(request, 'Result Uploaded Successfully')

            s = "ZMS/SS/12"



            update_position_query = StudentResult.objects.filter(session=session_id, term=term_id, student_class=class_id, subject=subject_id).all()

            f_total = [x.total for x in update_position_query]

            position = []
            for total in f_total:
                count = 0
                for pos in f_total:
                    if pos > total:
                        count += 1
                position.append(count + 1)

            for i, j in zip(position, update_position_query):
                j.subject_position = i
                j.save()





        return render(request,'src/stdupload.html', generalContext)
    else:
        return render(request, 'src/welcome.html')


def bhvxl(request):
    global students
    global subject
    global term
    global session
    global classs
    global class_id
    global session_id
    global term_id
    global subject_id
    global student_id
    if request.user.is_authenticated:
        classes = StudentClass.objects.all()
        context = {
            'classes': classes
        }
        if "GET" == request.method:
            return render(request, 'src/behav.html', context)
        else:

            session = request.POST['session']
            term = request.POST['term']
            classs = request.POST['class']


            #---------------Getting IDs of the Subjects, Session, and Class---------------------
            ses = Session.objects.get(session_name=session)
            session_id = ses.id

            trm = Term.objects.get(term_name=term)
            term_id = trm.id

            clas = StudentClass.objects.get(class_name=classs)
            class_id = clas.id

            excel_file = request.FILES["excel_file"]

            # you may put validations here to check extension or file size

            wb = openpyxl.load_workbook(excel_file)

            # getting a particular sheet by name out of many sheets
            worksheet = wb["result"]
            ids = []
            ses_ids = []
            trm_ids = []
            clas_ids = []
            conduct = []
            punc = []
            ded = []
            part = []
            hosp = []
            creat = []
            phy = []
            neat = []


            for i, j, k, l, m, n, o, p, q in zip((worksheet['A']), (worksheet['C']), (worksheet['D']), (worksheet['E']), (worksheet['F']), (worksheet['G']), (worksheet['H']), (worksheet['I']), (worksheet['J'])):
                ids.append(i.value)
                ses_ids.append(session_id)
                trm_ids.append(term_id)
                clas_ids.append(class_id)
                conduct.append(j.value)
                punc.append(k.value)
                ded.append(l.value)
                part.append(m.value)
                hosp.append(n.value)
                creat.append(o.value)
                phy.append(p.value)
                neat.append(q.value)




            #------------removing first row of the excel-----------
            f_ids = ids[1:]
            conduct = conduct[1:]
            punc = punc[1:]
            ded = ded[1:]
            part = part[1:]
            hosp = hosp[1:]
            creat = creat[1:]
            phy = phy[1:]
            neat = neat[1:]

            #-----------coverting to interger list----------------
            a_ids = [int(i) for i in f_ids]


            #--------------sumation of the CA to get Total Marks


            clso = int(class_id)
            sess = int(session_id)
            trm = int(term_id)


            c = connection.cursor()




            queryset = StudentBehaviouralAssessment.objects.filter(session=session_id, term=term_id, student_class=class_id).exists()
            if queryset:
                print("record is already there")
            else:
                c = connection.cursor()
                c.executemany("""INSERT INTO src_studentbehaviouralassessment (conduct, punctuality, dedication, participation, hospitality,
                    neatness, creativity, physical, session_id, student_id, student_class_id, term_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    zip(conduct, punc, ded, part, hosp, neat, creat, phy, ses_ids, f_ids, clas_ids, trm_ids))
                connection.commit()
                c.close()

            s = "ZMS/SS/12"


        return render(request,'src/behav.html', generalContext)
    else:
        return render(request, 'src/welcome.html')
'''
    global students
    global subject
    global term
    global session
    global classs
    global class_id
    global session_id
    global term_id
    global subject_id
    global student_id
    if request.user.is_authenticated:


        if request.method == 'POST' and "form1" in request.POST:

            session = request.POST['session']
            term = request.POST['term']
            classs = request.POST['class']


            ses = Session.objects.get(session_name=session)
            session_id = ses.id

            trm = Term.objects.get(term_name=term)
            term_id = trm.id

            clas = StudentClass.objects.get(class_name=classs)
            class_id = clas.id

            students = Student.objects.filter(student_class=class_id).all()
            student_id = []

            for i in students:
                student_id.append(i.id)
            print(student_id)

            classes = StudentClass.objects.all()

            context = {
                'classes': classes,
                'students': students
                }

            return render(request, 'src/settings.html', context)

        if request.method == 'POST' and "form2" in request.POST:

            ses_ids = []
            trm_ids = []
            clas_ids = []

            ids = request.POST.getlist('id')
            conduct = request.POST.getlist('conduct')
            punc = request.POST.getlist('punctuality')
            ded = request.POST.getlist('dedication')
            part = request.POST.getlist('participation')
            hosp = request.POST.getlist('hospitality')
            creat= request.POST.getlist('creativity')
            phy = request.POST.getlist('physical')
            neat = request.POST.getlist('neatness')

            for i in student_id:
                ses_ids.append(session_id)
                trm_ids.append(term_id)
                clas_ids.append(class_id)



            queryset = StudentBehaviouralAssessment.objects.filter(session=session_id, term=term_id, student_class=class_id).exists()
            if queryset:
                print("record is already there")
            else:
                c = connection.cursor()
                c.executemany("""INSERT INTO src_studentbehaviouralassessment (conduct, punctuality, dedication, participation, hospitality,
                    neatness, creativity, physical, session_id, student_id, student_class_id, term_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    zip(conduct, punc, ded, part, hosp, neat, creat, phy, ses_ids, student_id, clas_ids, trm_ids))
                connection.commit()
                c.close()


            classes = StudentClass.objects.all()

            context = {
                'classes': classes
                }

            return render(request, 'src/settings.html', context)



        else:
            classes = StudentClass.objects.all()

            context = {
                'classes': classes
                }

            return render(request, 'src/settings.html', context)
    else:
        return render(request, 'src/welcome.html')
'''

def behav_sheet(request):
    if request.user.is_authenticated:

        if request.method == 'POST' and "form1" in request.POST:
            classs = request.POST['class']

            class_id = StudentClass.objects.get(class_name=classs)
            class_id = class_id.id

            ids = []
            names = []
            conduct = []
            punc = []
            ded = []
            part = []
            hosp = []
            creat = []
            phy = []
            neat = []

            dukka = Student.objects.filter(student_class=class_id).all()

            for i in dukka:
                ids.append(i.id)
                names.append(i.student_name)
                conduct.append(0)
                punc.append(0)
                ded.append(0)
                part.append(0)
                hosp.append(0)
                creat.append(0)
                phy.append(0)
                neat.append(0)



            book = Workbook()
            sheet = book.active
            sheet.title = 'result'


            sheet['A1'] = "ID NO"
            sheet['B1'] = "Names"
            sheet['C1'] = "conduct"
            sheet['D1'] = "punc."
            sheet['E1'] = "dedic."
            sheet['F1'] = "part."
            sheet['G1'] = "hosp."
            sheet['H1'] = "creat."
            sheet['I1'] = "phy."
            sheet['J1'] = "neat."
            y=2

            for x in range(len(ids)):
                cell_to_write = sheet.cell(row=y, column=1)
                cell_to_write.value = ids[x]
                cell_to_write = sheet.cell(row=y, column=2)
                cell_to_write.value = names[x]
                cell_to_write = sheet.cell(row=y, column=3)
                cell_to_write.value = conduct[x]
                cell_to_write = sheet.cell(row=y, column=4)
                cell_to_write.value = punc[x]
                cell_to_write = sheet.cell(row=y, column=5)
                cell_to_write.value = ded[x]
                cell_to_write = sheet.cell(row=y, column=6)
                cell_to_write.value = part[x]
                cell_to_write = sheet.cell(row=y, column=7)
                cell_to_write.value = hosp[x]
                cell_to_write = sheet.cell(row=y, column=8)
                cell_to_write.value = creat[x]
                cell_to_write = sheet.cell(row=y, column=9)
                cell_to_write.value = phy[x]
                cell_to_write = sheet.cell(row=y, column=10)
                cell_to_write.value = neat[x]

                y += 1

            response = HttpResponse(content=save_virtual_workbook(book), content_type='application/ms-excel',)
            response['Content-Disposition'] = 'attachment; filename=template.xlsx'
            return response

        else:
            classes = StudentClass.objects.all()
            context = {
                'classes': classes
            }
            return render(request, 'src/behavsheet.html', context)

    else:
        return render(request, 'src/welcome.html')

def std_alts(request):
    if request.user.is_authenticated:
        global f_s_id
        global context
        global student_name
        global student_class
        global student
        global classes
        if request.method == 'POST' and "form1" in request.POST:
            class_name = request.POST['class']

            student = Student.objects.filter(
                student_class=StudentClass.objects.get(id=int(class_name))).all()
            classes = StudentClass.objects.all()

            generalContext['student'] = student
            context = {
                "classes": classes,
                "student": student,
            }
            return render(request, "src/std-alts.html", generalContext)

            # Adding New Students
        if request.method == 'POST' and "add" in request.POST:
            name = request.POST['name']
            classs = request.POST['class']

            Student.objects.create(
                student_name=name, student_class=StudentClass.objects.get(id=int(classs)))
            messages.success(request, 'Record Created Successfully')
            return render(request, "src/std-alts.html", generalContext)



        if request.method == 'POST' and "save" in request.POST:
            session = request.POST['session']
            current_class = request.POST['current_class']
            promotion_class = request.POST['promotion_class']

            #-----getting classes ids---------
            c_clas = StudentClass.objects.get(id=int(current_class))
            # print('SS 3' in str(c_clas))

            p_clas = StudentClass.objects.get(id=int(promotion_class))
            #p_class_id = p_clas.id

            #-----------getting student in a class---------------
            students_in_class = Student.objects.filter(student_class=c_clas).all()
            session = Session.objects.get(id=int(session))


            for student in students_in_class:

                # if 'S 3' in str(c_clas):
                #     query = student
                #     query.student_class = p_clas
                #     query.save()


                # else:
                #     student_results = StudentResult.objects.filter(student=student, term=3, session=session).all()

                #     total = []
                #     for result in student_results:
                #         total.append(result.total)
                #     print(total)

                #     avr = sum(total)/len(total)
                #     if avr >= 40:

                query = student
                query.student_class = p_clas
                query.save()

            messages.success(request, 'Students Promoted Successfully')
            return render(request, "src/std-alts.html", generalContext)

            # Updating ---------------------------------

        if request.method == 'POST':
            # deleting
            try:
                items_to_delete = request.POST.getlist('delete_items')
                temp1 = Student.objects.get(pk__in=items_to_delete)
                temp1.delete()
                classes = request.POST['class']
                student = Student.objects.filter(
                    student_class=StudentClass.objects.get(id=int(classes))).all()
                generalContext['student'] = student
                messages.success(request, 'Record Updated Successfully')
                return render(request, "src/std-alts.html", generalContext)

            except:
                # updating
                names = request.POST.getlist('name')
                classes = request.POST.getlist('class')
                items_to_update = request.POST.getlist('update_items')
                temp = Student.objects.get(pk__in=items_to_update)
                for i, j in zip(names, classes):
                    temp.student_name = i
                    temp.student_class = StudentClass.objects.get(id=int(j))
                temp.save()
                classes = request.POST['class']
                student = Student.objects.filter(
                    student_class=StudentClass.objects.get(id=int(classes))).all()
                generalContext['student'] = student
                messages.success(request, 'Record Updated Successfully')
                return render(request, "src/std-alts.html", generalContext)

        else:

            context = {
                # "classes": classes,
            }
            return render(request, "src/std-alts.html", generalContext)


    else:
        return render(request, 'src/welcome.html')
def class_summary(request):
    if request.user.is_authenticated:
        if request.method == 'POST' and "form1" in request.POST:
            classs = request.POST['class']
            term = request.POST['term']
            session = request.POST['session']
            subject = request.POST['subject']

            result_summary = StudentResult.objects.filter(subject=Subject.objects.get(subject_name=subject), student_class=StudentClass.objects.get(class_name=classs),
                            session=Session.objects.get(session_name=session), term=Term.objects.get(term_name=term)).all()


            total = []
            for i in result_summary:
                total.append(i.total)


            a_count = 0
            b_count = 0
            c_count = 0
            d_count = 0
            e_count = 0
            f_count = 0
            total_students = len(total)

            for i in total:
                if i >= 70:
                    a_count = a_count + 1
                elif i >= 60:
                    b_count = b_count + 1
                elif i >= 50:
                    c_count = c_count + 1
                elif i >=45:
                    d_count = d_count + 1
                elif i >=40:
                    e_count = e_count + 1
                else:
                    f_count = f_count + 1
            print(f_count)

            context = {
                'a_count': a_count,
                'b_count': b_count,
                'c_count': c_count,
                'd_count': d_count,
                'e_count': e_count,
                'f_count': f_count,
                'summary': result_summary,
                'total_students': total_students,
                'subject': subject,
                'classs': classs
            }




            '''total = []
            subject = []
            for result in result_summary:
                subject.append(result.subject)
                total.append(result.total)

            final_subjects = list(dict.fromkeys(subject))
            length_resulut_summary = len(result_summary)
            length_final_subjects = len(final_subjects)
            number_of_students = length_resulut_summary/length_final_subjects
            splits = np.array_split(total, length_final_subjects)

            for array in splits:
                print(array)'''




            return render(request, 'src/summary_page.html', context)
        else:
            classes = StudentClass.objects.all()
            terms = Term.objects.all()
            sessions = Session.objects.all()
            subjects = Subject.objects.all()
            context = {
                'classes': classes,
                'terms': terms,
                'sessions': sessions,
                'subjects': subjects
            }
            return render(request, 'src/class_summary.html', context)
        pass
    else:
        return render(request, 'src/welcome.html')

def delete_result(request):
    if request.user.is_authenticated:
        if request.method == 'POST' and "form1" in request.POST:
            session = request.POST['session']
            term = request.POST['term']
            classs = request.POST['class']

            ses = Session.objects.get(session_name=session)
            session_id = ses.id

            trm = Term.objects.get(term_name=term)
            term_id = trm.id

            clas = StudentClass.objects.get(class_name=classs)
            class_id = clas.id

            # subj = Subject.objects.get(subject_name=subject)
            # subject_id = subj.id

            query = StudentResult.objects.filter(session=session_id, term=term_id, student_class=class_id).all()
            query.delete()

            messages.info(request, 'Result Deleted Successfully')

            subjects = Subject.objects.all()
            classes = StudentClass.objects.all()
            sessions = Session.objects.all()
            terms = Term.objects.all()
            context = {
                'subjects': subjects,
                'classes': classes,
                'sessions': sessions,
                'terms': terms,
            }

            return render(request, 'src/resultdelete.html', context)

        if request.method == 'POST' and "form2" in request.POST:
            session = request.POST['session']
            term = request.POST['term']
            classs = request.POST['class']
            subject = request.POST['subject']

            ses = Session.objects.get(session_name=session)
            session_id = ses.id

            trm = Term.objects.get(term_name=term)
            term_id = trm.id

            clas = StudentClass.objects.get(class_name=classs)
            class_id = clas.id

            subj = Subject.objects.get(subject_name=subject)
            subject_id = subj.id

            query = StudentResult.objects.filter(session=session_id, term=term_id, student_class=class_id, subject=subject_id).all()
            query.delete()

            messages.info(request, 'Result Deleted Successfully')

            subjects = Subject.objects.all()
            classes = StudentClass.objects.all()
            sessions = Session.objects.all()
            terms = Term.objects.all()
            context = {
                'subjects': subjects,
                'classes': classes,
                'sessions': sessions,
                'terms': terms,
            }

            return render(request, 'src/resultdelete.html', context)

        else:
            subjects = Subject.objects.all()
            classes = StudentClass.objects.all()
            sessions = Session.objects.all()
            terms = Term.objects.all()
            context = {
                'subjects': subjects,
                'classes': classes,

            }
            return render(request, "src/resultdelete.html", context)
    else:
        return render(request, 'src/welcome.html')


def delete_bhv(request):
    if request.user.is_authenticated:
        if request.method == 'POST' and "form1" in request.POST:
            session = request.POST['session']
            term = request.POST['term']
            classs = request.POST['class']

            ses = Session.objects.get(session_name=session)
            session_id = ses.id

            trm = Term.objects.get(term_name=term)
            term_id = trm.id

            clas = StudentClass.objects.get(class_name=classs)
            class_id = clas.id

            # subj = Subject.objects.get(subject_name=subject)
            # subject_id = subj.id

            query = StudentBehaviouralAssessment.objects.filter(session=session_id, term=term_id, student_class=class_id).all()
            query.delete()

            messages.info(request, 'Result Deleted Successfully')


            classes = StudentClass.objects.all()
            sessions = Session.objects.all()
            terms = Term.objects.all()
            context = {

                'classes': classes,
                'sessions': sessions,
                'terms': terms,
            }

            return render(request, 'src/bhvdelete.html', context)


        else:

            classes = StudentClass.objects.all()
            sessions = Session.objects.all()
            terms = Term.objects.all()
            context = {

                'classes': classes,

            }
            return render(request, "src/bhvdelete.html", context)
    else:
        return render(request, 'src/welcome.html')

def bhvxl_missed(request):
    global students
    global subject
    global term
    global session
    global classs
    global class_id
    global session_id
    global term_id
    global subject_id
    global student_id
    if request.user.is_authenticated:
        classes = StudentClass.objects.all()
        context = {
            'classes': classes
        }
        if "GET" == request.method:
            return render(request, 'src/behav.html', context)
        else:

            session = request.POST['session']
            term = request.POST['term']
            classs = request.POST['class']


            #---------------Getting IDs of the Subjects, Session, and Class---------------------
            ses = Session.objects.get(session_name=session)
            session_id = ses.id

            trm = Term.objects.get(term_name=term)
            term_id = trm.id

            clas = StudentClass.objects.get(class_name=classs)
            class_id = clas.id

            excel_file = request.FILES["excel_file"]

            # you may put validations here to check extension or file size

            wb = openpyxl.load_workbook(excel_file)

            # getting a particular sheet by name out of many sheets
            worksheet = wb["result"]
            ids = []
            ses_ids = []
            trm_ids = []
            clas_ids = []
            conduct = []
            punc = []
            ded = []
            part = []
            hosp = []
            creat = []
            phy = []
            neat = []


            for i, j, k, l, m, n, o, p, q in zip((worksheet['A']), (worksheet['C']), (worksheet['D']), (worksheet['E']), (worksheet['F']), (worksheet['G']), (worksheet['H']), (worksheet['I']), (worksheet['J'])):
                ids.append(i.value)
                ses_ids.append(session_id)
                trm_ids.append(term_id)
                clas_ids.append(class_id)
                conduct.append(j.value)
                punc.append(k.value)
                ded.append(l.value)
                part.append(m.value)
                hosp.append(n.value)
                creat.append(o.value)
                phy.append(p.value)
                neat.append(q.value)




            #------------removing first row of the excel-----------
            f_ids = ids[1:]
            conduct = conduct[1:]
            punc = punc[1:]
            ded = ded[1:]
            part = part[1:]
            hosp = hosp[1:]
            creat = creat[1:]
            phy = phy[1:]
            neat = neat[1:]

            #-----------coverting to interger list----------------
            a_ids = [int(i) for i in f_ids]


            #--------------sumation of the CA to get Total Marks


            clso = int(class_id)
            sess = int(session_id)
            trm = int(term_id)








            c = connection.cursor()
            c.executemany("""INSERT INTO src_studentbehaviouralassessment (conduct, punctuality, dedication, participation, hospitality,
                neatness, creativity, physical, session_id, student_id, student_class_id, term_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                zip(conduct, punc, ded, part, hosp, neat, creat, phy, ses_ids, f_ids, clas_ids, trm_ids))
            connection.commit()
            c.close()

            s = "ZMS/SS/12"



        return render(request,'src/behav.html', context)
    else:
        return render(request, 'src/welcome.html')



def class_result_summary(request):
    global class_id
    global session_id
    global term_id

    if request.user.is_authenticated:

        if request.method == 'POST' and "form1" in request.POST:
            classes = StudentClass.objects.all()

            context = {
                'classes': classes,
                'sessions': Session.objects.all(),
                'terms': Term.objects.all()
                }

            session = request.POST['session']
            term = request.POST['term']
            classs = request.POST['class']

            directorAcadamic = "Director Acadamic & Examination"
            if "SS" in classs or "JS" in classs:
                pcHeadTeacher = "Principal"

            else:
                pcHeadTeacher = "Head Teacher"

            ses = Session.objects.get(session_name=session)
            session_id = ses.id

            trm = Term.objects.get(term_name=term)
            term_id = trm.id

            clas = StudentClass.objects.get(class_name=classs)
            class_id = clas.id

            results = StudentResult.objects.filter(session=session_id, term=term_id, student_class=class_id)
            bulk = {}


            eachSubject = []
            for result in results:
                ca1_total = 0
                ca2_total = 0
                exams_total = 0
                total = 0
                subjects = []
                for subject in results:
                    if subject.student == result.student:
                        subjects.append(subject)
                        eachSubject.append(subject.subject)
                        ca1_total += subject.ca1
                        ca2_total += subject.ca2
                        exams_total += subject.exams
                        total += subject.total
                        subject_pos = subject.subject_position
                        grade = subject.grade
                        terms = subject.term
                        sesss = subject.session
                        classs = subject.student_class
                        avr = total/len(subjects)



                    bulk[result.student] = {
                    "student": result.student,
                    "subjects": subjects,
                    "ca1_total": ca1_total,
                    "ca2_total": ca1_total,
                    "exams_total": exams_total,
                    "total": total,
                    "grade": grade,
                    "subject_pos": subject_pos,
                    "terms": terms,
                    "sesss": sesss,
                    "classs": classs,
                    "overal_total": total,
                    "average": round(avr, 2),




                    }

            classes = StudentClass.objects.all()
            bhv = StudentBehaviouralAssessment.objects.filter(session=session_id, term=term_id, student_class=class_id)
            signs = signature.objects.filter(classs=classs).first()
            some_images = sets.objects.first()

            f_classs = str(classs)
            date = datetime.datetime.now()
            eachSubject = list(dict.fromkeys(eachSubject))
            context = {
                'date': date,
                'f_classs': f_classs,
                'classes': classes,
                'results': bulk,
                'bhv': bhv,
                'signs': signs,
                'some_images':some_images,
                'p_term': term,
                'eachSubject': eachSubject,
                "session": session,
                "term": term,
                "class": classs,
                "directorAcadamic": directorAcadamic,
                "pcHeadTeacher": pcHeadTeacher,
            }



            return render(request, 'src/class_result_summary.html', context)

        else:
            classes = StudentClass.objects.all()

            context = {
                'classes': classes,
                'sessions': Session.objects.all(),
                'terms': Term.objects.all()
                }

            return render(request, 'src/result_view.html', context)

    else:
        return render(request, 'src/welcome.html')