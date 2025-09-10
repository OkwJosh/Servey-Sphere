# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from .models import Survey, Question, Response, Answer, Option
from .forms import SurveyResponseForm


def survey_list(request):
    """Display list of active surveys"""
    surveys = Survey.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'surveys/survey_list.html', {'surveys': surveys})


def survey_detail(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id, is_active=True)
    
    if request.method == 'POST':
        form = SurveyResponseForm(survey, request.POST)
        if form.is_valid():
            response = form.save(request)
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


def handle_survey_submission(request, survey, questions):
    """Process survey form submission"""
    try:
        with transaction.atomic():
            # Create response record
            response = Response.objects.create(
                survey=survey,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                is_complete=True
            )
            
            # Process each question's answer
            for question in questions:
                answer_data = request.POST.get(f'question_{question.id}')
                
                if question.question_type == 'checkbox':
                    # Handle multiple choice
                    selected_options = request.POST.getlist(f'question_{question.id}')
                    if selected_options or not question.is_required:
                        answer = Answer.objects.create(
                            response=response,
                            question=question
                        )
                        if selected_options:
                            option_ids = [int(opt_id) for opt_id in selected_options]
                            options = Option.objects.filter(id__in=option_ids, question=question)
                            answer.selected_options.set(options)
                
                elif question.question_type == 'radio':
                    # Handle single choice
                    if answer_data or not question.is_required:
                        answer = Answer.objects.create(
                            response=response,
                            question=question
                        )
                        if answer_data:
                            option = Option.objects.get(id=int(answer_data), question=question)
                            answer.selected_options.add(option)
                
                elif question.question_type == 'number':
                    # Handle numeric input
                    if answer_data or not question.is_required:
                        Answer.objects.create(
                            response=response,
                            question=question,
                            numeric_answer=float(answer_data) if answer_data else None
                        )
                
                else:
                    # Handle text input
                    if answer_data or not question.is_required:
                        Answer.objects.create(
                            response=response,
                            question=question,
                            text_answer=answer_data or ''
                        )
                        
            messages.success(request, 'Thank you! Your survey response has been submitted successfully.')
            return redirect('survey_success')
            
    except Exception as e:
        messages.error(request, 'There was an error submitting your response. Please try again.')
        return render(request, 'surveys/survey_detail.html', {
            'survey': survey,
            'questions': questions,
            'error': str(e)
        })


def survey_success(request):
    """Thank you page after successful submission"""
    return render(request, 'surveys/survey_success.html')


def survey_results(request, survey_id):
    """Display survey results (admin only)"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view survey results.')
        return redirect('survey_list')
    
    survey = get_object_or_404(Survey, id=survey_id)
    questions = survey.questions.all().prefetch_related('options')
    responses = survey.responses.filter(is_complete=True)
    
    # Calculate statistics for each question
    question_stats = []
    for question in questions:
        answers = Answer.objects.filter(question=question, response__in=responses)
        
        if question.question_type in ['radio', 'checkbox']:
            # Count option selections
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
            # Text/number responses
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


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# forms.py (if you want to use Django forms instead of raw HTML)
from django import forms
from .models import Survey, Question, Option


class SurveyResponseForm(forms.Form):
    def __init__(self, survey, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for question in survey.questions.all():
            field_name = f'question_{question.id}'
            
            if question.question_type == 'text':
                self.fields[field_name] = forms.CharField(
                    label=question.text,
                    required=question.is_required,
                    help_text=question.help_text,
                    widget=forms.TextInput(attrs={'class': 'form-control'})
                )
            
            elif question.question_type == 'textarea':
                self.fields[field_name] = forms.CharField(
                    label=question.text,
                    required=question.is_required,
                    help_text=question.help_text,
                    widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4})
                )
            
            elif question.question_type == 'email':
                self.fields[field_name] = forms.EmailField(
                    label=question.text,
                    required=question.is_required,
                    help_text=question.help_text,
                    widget=forms.EmailInput(attrs={'class': 'form-control'})
                )
            
            elif question.question_type == 'number':
                self.fields[field_name] = forms.DecimalField(
                    label=question.text,
                    required=question.is_required,
                    help_text=question.help_text,
                    widget=forms.NumberInput(attrs={'class': 'form-control'})
                )
            
            elif question.question_type == 'radio':
                choices = [(opt.id, opt.text) for opt in question.options.all()]
                self.fields[field_name] = forms.ChoiceField(
                    label=question.text,
                    choices=choices,
                    required=question.is_required,
                    help_text=question.help_text,
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
                )
            
            elif question.question_type == 'checkbox':
                choices = [(opt.id, opt.text) for opt in question.options.all()]
                self.fields[field_name] = forms.MultipleChoiceField(
                    label=question.text,
                    choices=choices,
                    required=question.is_required,
                    help_text=question.help_text,
                    widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
                )