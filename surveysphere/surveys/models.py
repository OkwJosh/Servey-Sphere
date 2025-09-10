from django.db import models
from users.models import CustomUser
from django.core.exceptions import ValidationError


class Survey(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="surveys")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Survey"
        verbose_name_plural = "Surveys"

    def __str__(self):
        return self.title
    
    @property
    def response_count(self):
        return self.responses.count()


class Question(models.Model):
    QUESTION_TYPES = (
        ('text', 'Text Input'),
        ('textarea', 'Long Text'),
        ('radio', 'Single Choice'),
        ('checkbox', 'Multiple Choice'),
        ('rating', 'Rating Scale'),
        ('email', 'Email'),
        ('number', 'Number'),
    )

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="questions")
    text = models.CharField(max_length=500)  # Increased for longer questions
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='text')
    is_required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)  # For question ordering
    help_text = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['order', 'id']
        unique_together = ['survey', 'order']

    def __str__(self):
        return f"{self.survey.title} - {self.text[:50]}"
    
    def clean(self):
        # Validate that choice questions have options
        if self.question_type in ['radio', 'checkbox'] and not self.options.exists():
            if self.pk:  # Only check if question already exists
                raise ValidationError("Choice questions must have at least one option.")


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'id']
        unique_together = ['question', 'order']

    def __str__(self):
        return f"{self.question.text[:30]} - {self.text}"


class Response(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="responses")
    submitted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    is_complete = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Response to {self.survey.title} at {self.submitted_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def completion_time(self):
        """Calculate time taken to complete survey (if tracking start time)"""
        # You could add a started_at field to track this
        pass


class Answer(models.Model):
    response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    
    # For choice-based questions
    selected_options = models.ManyToManyField(Option, blank=True)  # Changed to M2M for multiple choice
    
    # For text-based questions
    text_answer = models.TextField(blank=True)
    
    # For numeric questions
    numeric_answer = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    class Meta:
        unique_together = ['response', 'question']  # One answer per question per response

    def __str__(self):
        try:
            question_text = str(self.question.text)[:30] if self.question and self.question.text else "Unknown Question"
            response_id = str(self.response.id) if self.response and self.response.id else "New"
            return f"Answer to '{question_text}' in response {response_id}"
        except:
            return f"Answer {self.id}" if self.id else "New Answer"
    
    def clean(self):
        # Validation based on question type
        if self.question.question_type == 'text' and not self.text_answer:
            if self.question.is_required:
                raise ValidationError("Text answer is required for this question.")
        
        elif self.question.question_type == 'radio':
            if self.selected_options.count() > 1:
                raise ValidationError("Single choice questions can only have one selected option.")
            if self.question.is_required and self.selected_options.count() == 0:
                raise ValidationError("This question requires an answer.")
        
        elif self.question.question_type == 'number':
            if self.question.is_required and self.numeric_answer is None:
                raise ValidationError("Numeric answer is required for this question.")
    
    def get_display_answer(self):
        """Return a human-readable version of the answer"""
        if self.question.question_type in ['radio', 'checkbox']:
            options = self.selected_options.all()
            return ", ".join([opt.text for opt in options])
        elif self.question.question_type == 'number':
            return str(self.numeric_answer) if self.numeric_answer is not None else ""
        else:
            return self.text_answer