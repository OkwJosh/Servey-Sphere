# urls.py (app level)
from django.urls import path
from . import views

app_name = 'surveys'

urlpatterns = [
    path('', views.survey_list, name='survey_list'),
    path('survey/<int:survey_id>/', views.survey_detail, name='survey_detail'),
    path('survey/<int:survey_id>/results/', views.survey_results, name='survey_results'),
    path('success/', views.survey_success, name='survey_success'),
    path('survey/create/', views.survey_create, name='survey_create'),
    path('survey/<int:survey_id>/add-questions/', views.add_questions, name='add_questions'),
]


# Don't forget to include in your main urls.py:
# from django.contrib import admin
# from django.urls import path, include
# 
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('surveys/', include('your_app.urls')),
# ]