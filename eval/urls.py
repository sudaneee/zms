from django.urls import path
from . import views


urlpatterns = [
    path('', views.evaluation, name='evaluation'),
    path('evaluation-view', views.evaluation_view, name='evaluation-view'),
]