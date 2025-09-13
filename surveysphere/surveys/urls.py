# urls.py (app level)
from django.urls import path
from . import views

app_name = 'surveys'

urlpatterns = [
    path("", views.survey_list, name="survey_list"),
    path("my-surveys/", views.my_surveys, name="my_surveys"),
    path("survey/<int:survey_id>/", views.survey_detail, name="survey_detail"),
    path("survey/<int:survey_id>/results/", views.survey_results, name="survey_results"),
    path("create/", views.survey_create, name="survey_create"),
    path("survey/<int:survey_id>/add-questions/", views.add_questions, name="add_questions"),
    path("success/", views.survey_success, name="survey_success"),
    path("create/sucess/",views.survey_create_success,name="create_success")
]


# Don't forget to include in your main urls.py:
# from django.contrib import admin
# from django.urls import path, include
# 
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('surveys/', include('your_app.urls')),
# ]