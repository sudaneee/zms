from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('create-result', views.resultcreate, name='resultcreate'),
    path('update-result', views.updateresult, name='updateresult'),
    path('single-result-update', views.single_result_update, name='single_result_update'),
    path('bulk-result-view', views.result_view, name='result_view'),
    path('class-result-summary', views.class_result_summary, name='class_result_summary'),
    path('settings', views.settings, name='settings'),
    path('single-result-view', views.single_result_view, name='single_result_view'),
    path('bulk-result-upload', views.ResultUpload, name='std_upload'),
    path('create-student', views.stdcreate, name='std_create'),
    path('set-position', views.setting_position, name='setting_position'),
    path('nav', views.side_nav, name='nav'),
    path('score-sheet', views.score_sheet, name='score_sheet'),
    path('logout', views.logout, name='logout'),
    path('excel_score_sheet', views.excel_score_sheet, name='excel_score_sheet'),
    path('not-uploaded-results', views.not_uploaded_results, name='not_uploaded_results'),
    path('behaivioural-excel', views.bhvxl, name='bhvxl'),
    path('behaivioural-excel-missed', views.bhvxl_missed, name='bhvxl-missed'),
    path('behaivioural-excel2', views.behav_sheet, name='behav_sheet'),
    path('std-alts', views.std_alts, name='Std-Alts'),
    path('class-result-summary', views.class_summary, name='class-result-summary'),
    path('delete_result', views.delete_result, name='delete_result'),
    path('delete_bhv', views.delete_bhv, name='delete_bhv'),

]

