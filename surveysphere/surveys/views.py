from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
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
    
    return render(request, 'surveys/survey_detail.html', {
        'survey': survey,
        'form': form
    })


def survey_success(request):
    """Thank you page after successful submission"""
    return render(request, 'surveys/survey_success.html')


def survey_results(request, survey_id):
    """Display survey results (admin only)"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view survey results.')
        return redirect('surveys:survey_list')
    
    survey = get_object_or_404(Survey, id=survey_id)
    questions = survey.questions.all().prefetch_related('options')
    responses = survey.responses.filter(is_complete=True)
    
    # Calculate statistics for each question
    question_stats = []
    for question in questions:
        answers = Answer.objects.filter(question=question, response__in=responses)
        
        if question.question_type in ['radio', 'checkbox']:
            option_counts = {}
            for option in question.options.all():
                count = answers.filter(selected_options=option).count()
                option_counts[option.text] = count
            
            question_stats.append({
                'question': question,
                'type': 'choice',
                'option_counts': option_counts,
                'total_answers': answers.count()
            })
        else:
            answer_list = []
            for answer in answers:
                if question.question_type == 'number':
                    answer_list.append(answer.numeric_answer)
                else:
                    answer_list.append(answer.text_answer)
            
            question_stats.append({
                'question': question,
                'type': 'text',
                'answers': answer_list,
                'total_answers': len(answer_list)
            })
    
    return render(request, 'surveys/survey_results.html', {
        'survey': survey,
        'question_stats': question_stats,
        'total_responses': responses.count()
    })


def survey_create(request):
    if request.method == 'POST':
        form = SurveyCreationForm(request.POST)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.created_by = request.user  # link survey to creator
            survey.save()
            messages.success(request, 'Survey created successfully! Now add questions.')
            return redirect('surveys:add_questions', survey_id=survey.id)
    else:
        form = SurveyCreationForm()
    
    return render(request, 'surveys/create_surveys.html', {'form': form})


def add_questions(request, survey_id):
    """Add questions (and options if needed) to a survey"""
    survey = get_object_or_404(Survey, id=survey_id)
    
    if request.method == 'POST':
        question_form = QuestionCreationForm(request.POST)
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.survey = survey
            question.save()
            
            # If the question type needs options (radio/checkbox), redirect to add options
            if question.question_type in ['radio', 'checkbox']:
                messages.info(request, 'Now add options for this question.')
                return redirect('surveys:add_options', survey_id=survey.id, question_id=question.id)
            
            messages.success(request, 'Question added successfully!')
            return redirect('surveys:add_questions', survey_id=survey.id)
    else:
        question_form = QuestionCreationForm()
    
    questions = survey.questions.all()
    return render(request, 'surveys/add_questions.html', {
        'survey': survey,
        'form': question_form,
        'questions': questions
    })


def add_options(request, survey_id, question_id):
    """Add options to a multiple-choice question"""
    survey = get_object_or_404(Survey, id=survey_id)
    question = get_object_or_404(Question, id=question_id, survey=survey)
    
    if request.method == 'POST':
        option_form = OptionCreationForm(request.POST)
        if option_form.is_valid():
            option = option_form.save(commit=False)
            option.question = question
            option.save()
            messages.success(request, 'Option added successfully!')
            return redirect('surveys:add_options', survey_id=survey.id, question_id=question.id)
    else:
        option_form = OptionCreationForm()
    
    options = question.options.all()
    return render(request, 'surveys/add_options.html', {
        'survey': survey,
        'question': question,
        'form': option_form,
        'options': options
    })
