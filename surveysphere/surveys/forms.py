# forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Survey, Question, Option, Response, Answer


class SurveyResponseForm(forms.Form):
    """
    Dynamic form that generates fields based on survey questions
    """
    def __init__(self, survey, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.survey = survey
        
        # Generate form fields for each question
        for question in survey.questions.all():
            field_name = f'question_{question.id}'
            
            # Text input field
            if question.question_type == 'text':
                self.fields[field_name] = forms.CharField(
                    label=question.text,
                    required=question.is_required,
                    help_text=question.help_text,
                    widget=forms.TextInput(attrs={
                        'class': 'form-control',
                        'placeholder': 'Enter your answer...'
                    })
                )
            
            # Long text area
            elif question.question_type == 'textarea':
                self.fields[field_name] = forms.CharField(
                    label=question.text,
                    required=question.is_required,
                    help_text=question.help_text,
                    widget=forms.Textarea(attrs={
                        'class': 'form-control',
                        'rows': 4,
                        'placeholder': 'Enter your detailed answer...'
                    })
                )
            
            # Email input
            elif question.question_type == 'email':
                self.fields[field_name] = forms.EmailField(
                    label=question.text,
                    required=question.is_required,
                    help_text=question.help_text,
                    widget=forms.EmailInput(attrs={
                        'class': 'form-control',
                        'placeholder': 'your.email@example.com'
                    })
                )
            
            # Number input
            elif question.question_type == 'number':
                self.fields[field_name] = forms.DecimalField(
                    label=question.text,
                    required=question.is_required,
                    help_text=question.help_text,
                    max_digits=10,
                    decimal_places=2,
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control',
                        'step': '0.01'
                    })
                )
            
            # Single choice (radio buttons)
            elif question.question_type == 'radio':
                choices = [(opt.id, opt.text) for opt in question.options.all()]
                self.fields[field_name] = forms.ChoiceField(
                    label=question.text,
                    choices=choices,
                    required=question.is_required,
                    help_text=question.help_text,
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
                )
            
            # Multiple choice (checkboxes)
            elif question.question_type == 'checkbox':
                choices = [(opt.id, opt.text) for opt in question.options.all()]
                self.fields[field_name] = forms.MultipleChoiceField(
                    label=question.text,
                    choices=choices,
                    required=question.is_required,
                    help_text=question.help_text,
                    widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
                )
            
            # Rating scale (1-5 or 1-10)
            elif question.question_type == 'rating':
                rating_choices = [(i, str(i)) for i in range(1, 6)]  # 1-5 scale
                self.fields[field_name] = forms.ChoiceField(
                    label=question.text,
                    choices=rating_choices,
                    required=question.is_required,
                    help_text=question.help_text,
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
                )

    def clean(self):
        """Custom validation for the entire form"""
        cleaned_data = super().clean()
        
        # Add any cross-field validation here
        # For example, check if required questions are answered
        
        return cleaned_data

    def save(self, request):
        """Save the form data to the database"""
        # Create response record
        response = Response.objects.create(
            survey=self.survey,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            is_complete=True
        )
        
        # Save answers for each question
        for question in self.survey.questions.all():
            field_name = f'question_{question.id}'
            answer_data = self.cleaned_data.get(field_name)
            
            if answer_data or not question.is_required:
                answer = Answer.objects.create(
                    response=response,
                    question=question
                )
                
                # Handle different question types
                if question.question_type in ['radio', 'rating']:
                    # Single choice
                    option = Option.objects.get(id=int(answer_data))
                    answer.selected_options.add(option)
                
                elif question.question_type == 'checkbox':
                    # Multiple choice
                    if isinstance(answer_data, list):
                        option_ids = [int(opt_id) for opt_id in answer_data]
                        options = Option.objects.filter(id__in=option_ids)
                        answer.selected_options.set(options)
                
                elif question.question_type == 'number':
                    # Numeric answer
                    answer.numeric_answer = answer_data
                    answer.save()
                
                else:
                    # Text-based answers
                    answer.text_answer = str(answer_data) if answer_data else ''
                    answer.save()
        
        return response
    
    def get_client_ip(self, request):
        """Helper method to get client IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SurveyCreationForm(forms.ModelForm):
    """Form for creating/editing surveys in admin or custom views"""
    
    class Meta:
        model = Survey
        fields = ['title', 'description', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_title(self):
        """Custom validation for survey title"""
        title = self.cleaned_data.get('title')
        if len(title) < 5:
            raise ValidationError("Survey title must be at least 5 characters long.")
        return title


class QuestionCreationForm(forms.ModelForm):
    """Form for creating/editing questions"""
    
    class Meta:
        model = Question
        fields = ['text', 'question_type', 'is_required', 'order', 'help_text']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'question_type': forms.Select(attrs={'class': 'form-select'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'help_text': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_text(self):
        """Validate question text"""
        text = self.cleaned_data.get('text')
        if len(text) < 10:
            raise ValidationError("Question text must be at least 10 characters long.")
        return text


class OptionCreationForm(forms.ModelForm):
    """Form for creating/editing options"""
    
    class Meta:
        model = Option
        fields = ['text', 'order']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_text(self):
        """Validate option text"""
        text = self.cleaned_data.get('text')
        if len(text) < 1:
            raise ValidationError("Option text cannot be empty.")
        return text


# Form sets for handling multiple questions/options at once
from django.forms import formset_factory, modelformset_factory

# Create formsets for bulk editing
QuestionFormSet = modelformset_factory(
    Question,
    form=QuestionCreationForm,
    extra=1,
    can_delete=True
)

OptionFormSet = modelformset_factory(
    Option,
    form=OptionCreationForm,
    extra=2,
    can_delete=True
)