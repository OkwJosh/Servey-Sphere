from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.core.exceptions import ValidationError  # ✅ Added
from .models import Survey, Question, Response, Answer, Option
from .forms import (
    SurveyResponseForm,
    SurveyCreationForm,
    QuestionCreationForm,
    OptionCreationForm
)


def survey_list(request):
    """Display list of active surveys"""
    surveys = Survey.objects.all()
    return render(request, 'surveys/survey_list.html', {'surveys': surveys})


@login_required
def my_surveys(request):
    surveys = Survey.objects.filter(created_by=request.user)
    return render(request, "surveys/my_surveys.html", {"surveys": surveys})


def survey_detail(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id, is_active=True)
    
    if request.method == 'POST':
        form = SurveyResponseForm(survey, request.POST)
        if form.is_valid():
            form.save(request)
            messages.success(request, 'Thank you! Your survey response has been submitted.')
            return redirect('surveys:survey_success')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SurveyResponseForm(survey)
    
    return render(request, 'surveys/survey_details.html', {
        'survey': survey,
        'form': form
    })


def survey_success(request):
    return render(request, 'surveys/survey_success.html')


def survey_create_success(request):
    return render(request,'surveys/create_success.html')


def survey_results(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)

    questions_with_results = []
    for question in survey.questions.all():
        answers_qs = Answer.objects.filter(question=question)
        total_responses = answers_qs.count()

        result_data = {}

        # Handle based on question type
        if question.question_type in ["radio", "checkbox"]:
            options_data = []
            for option in question.options.all():
                count = answers_qs.filter(selected_options=option).count()
                percentage = (count / total_responses * 100) if total_responses > 0 else 0
                options_data.append({
                    "option": option.text,
                    "count": count,
                    "percentage": round(percentage, 2),
                })
            result_data = {"options": options_data}

        elif question.question_type in ["number", "rating"]:
            numeric_answers = [a.numeric_answer for a in answers_qs if a.numeric_answer is not None]
            avg = sum(numeric_answers) / len(numeric_answers) if numeric_answers else None
            result_data = {"average": avg, "answers": numeric_answers}

        else:  # text, textarea, email
            text_answers = [a.text_answer for a in answers_qs if a.text_answer]
            result_data = {"answers": text_answers}

        questions_with_results.append({
            "question": question.text,
            "type": question.question_type,
            "total": total_responses,
            "results": result_data,
        })

    context = {
        "survey": survey,
        "questions_with_results": questions_with_results,
    }
    return render(request, "surveys/survey_results.html", context)

def survey_create(request):
    if request.method == 'POST':
        form = SurveyCreationForm(request.POST)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.created_by = request.user  
            survey.save()
            messages.success(request, 'Survey created successfully! Now add questions.')
            return redirect('surveys:add_questions', survey_id=survey.id)
    else:
        form = SurveyCreationForm()
    
    return render(request, 'surveys/create_surveys.html', {'form': form})


def add_questions(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)

    if request.method == 'POST':
        question_form = QuestionCreationForm(request.POST)

        if question_form.is_valid():
            try:
                with transaction.atomic():
                    question = question_form.save(commit=False)
                    question.survey = survey
                    question.save()

                    if question.question_type in ['radio', 'checkbox']:
                        options_text = request.POST.getlist('options[]')
                        if not options_text or all(not text.strip() for text in options_text):
                            raise ValidationError("Choice questions must have at least one option.")
                        
                        for order, text in enumerate(options_text, 1):
                            if text.strip():  # avoid empty option fields
                                Option.objects.create(
                                    question=question,
                                    text=text.strip(),
                                    order=order
                                )

                messages.success(request, "Question added successfully!")
                return redirect('surveys:add_questions', survey_id=survey.id)
                
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        question_form = QuestionCreationForm()

    questions = survey.questions.prefetch_related('options').all()

    return render(request, 'surveys/add_questions.html', {
        'survey': survey,
        'form': question_form,
        'questions': questions,
    })
