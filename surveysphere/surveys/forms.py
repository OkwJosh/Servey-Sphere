from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from .models import Survey, Question, Option, Response, Answer


class SurveyResponseForm(forms.Form):
    """
    Dynamic form that generates fields based on survey questions
    """
    def __init__(self, survey, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.survey = survey
        
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
                    max_digits=10,
                    decimal_places=2,
                    widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
                )
            elif question.question_type == 'radio':
                choices = [(opt.id, opt.text) for opt in question.options.all()]
                self.fields[field_name] = forms.ChoiceField(
                    label=question.text,
                    choices=choices,
                    required=question.is_required,
                    help_text=question.help_text,
                    widget=forms.RadioSelect()
                )
            elif question.question_type == 'checkbox':
                choices = [(opt.id, opt.text) for opt in question.options.all()]
                self.fields[field_name] = forms.MultipleChoiceField(
                    label=question.text,
                    choices=choices,
                    required=question.is_required,
                    help_text=question.help_text,
                    widget=forms.CheckboxSelectMultiple()
                )
            elif question.question_type == 'rating':
                rating_choices = [(i, str(i)) for i in range(1, 6)]
                self.fields[field_name] = forms.ChoiceField(
                    label=question.text,
                    choices=rating_choices,
                    required=question.is_required,
                    help_text=question.help_text,
                    widget=forms.RadioSelect()
                )

    def save(self, request):
        response = Response.objects.create(
            survey=self.survey,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            is_complete=True
        )

        for question in self.survey.questions.all():
            field_name = f'question_{question.id}'
            answer_data = self.cleaned_data.get(field_name)
            
            # 🐛 BUG FIX: The original logic was wrong!
            # It was skipping answers when answer_data was falsy (empty string, empty list, etc.)
            # But we should create Answer objects even for empty responses to track that the question was presented
            
            # Create answer object for every question that was in the form
            if field_name in self.cleaned_data:  # Only if the field existed in the form
                answer = Answer.objects.create(response=response, question=question)

                if question.question_type == 'radio':
                    if answer_data:  # Only set option if something was selected
                        try:
                            option = Option.objects.get(id=int(answer_data))
                            answer.selected_options.add(option)
                        except (Option.DoesNotExist, ValueError, TypeError):
                            # Handle invalid option IDs gracefully
                            pass

                elif question.question_type == 'checkbox':
                    if answer_data:  # Only set options if something was selected
                        try:
                            option_ids = [int(opt_id) for opt_id in answer_data]
                            options = Option.objects.filter(id__in=option_ids)
                            answer.selected_options.set(options)
                        except (ValueError, TypeError):
                            # Handle invalid option IDs gracefully
                            pass

                elif question.question_type == 'rating':
                    if answer_data:  # Only save if a rating was selected
                        answer.text_answer = str(answer_data)
                        answer.save()

                elif question.question_type == 'number':
                    if answer_data is not None:  # Save even if 0
                        answer.numeric_answer = answer_data
                        answer.save()

                else:
                    # text, textarea, email, etc.
                    if answer_data:  # Only save if there's actual text
                        answer.text_answer = str(answer_data)
                        answer.save()

        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')


class SurveyCreationForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ['title', 'description', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if len(title) < 5:
            raise ValidationError("Survey title must be at least 5 characters long.")
        return title


class QuestionCreationForm(forms.ModelForm):
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
        text = self.cleaned_data.get('text')
        if len(text) < 10:
            raise ValidationError("Question text must be at least 10 characters long.")
        return text


class OptionCreationForm(forms.ModelForm):
    class Meta:
        model = Option
        fields = ['text', 'order']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_text(self):
        text = self.cleaned_data.get('text')
        if not text.strip():
            raise ValidationError("Option text cannot be empty.")
        return text


# ✅ Inline formset to tie options to a single question
OptionFormSet = inlineformset_factory(
    Question, Option,
    form=OptionCreationForm,
    extra=2,          # Show 2 blank option fields by default
    can_delete=True
)