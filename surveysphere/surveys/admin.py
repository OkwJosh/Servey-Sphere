# admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Survey, Question, Option, Response, Answer


class OptionInline(admin.TabularInline):
    model = Option
    extra = 2
    fields = ['text', 'order']


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1
    fields = ['text', 'question_type', 'is_required', 'order', 'help_text']
    inlines = [OptionInline]


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_by', 'is_active', 'question_count', 'response_count', 'created_at']
    list_filter = ['is_active', 'created_at', 'created_by']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at', 'response_count']
    inlines = [QuestionInline]
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new survey
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text_preview', 'survey', 'question_type', 'is_required', 'order']
    list_filter = ['question_type', 'is_required', 'survey']
    search_fields = ['text', 'survey__title']
    inlines = [OptionInline]
    
    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Question Text'


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ['text', 'question_preview', 'order']
    list_filter = ['question__survey', 'question__question_type']
    search_fields = ['text', 'question__text']
    
    def question_preview(self, obj):
        return obj.question.text[:30] + "..." if len(obj.question.text) > 30 else obj.question.text
    question_preview.short_description = 'Question'


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ['question', 'get_answer_display']
    
    def get_answer_display(self, obj):
        return obj.get_display_answer()
    get_answer_display.short_description = 'Answer'


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ['survey', 'submitted_at', 'is_complete', 'answer_count']
    list_filter = ['is_complete', 'submitted_at', 'survey']
    readonly_fields = ['submitted_at', 'ip_address', 'user_agent']
    inlines = [AnswerInline]
    
    def answer_count(self, obj):
        return obj.answers.count()
    answer_count.short_description = 'Answers'


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['question_preview', 'response', 'answer_preview']
    list_filter = ['question__question_type', 'response__survey']
    
    def question_preview(self, obj):
        return obj.question.text[:40] + "..." if len(obj.question.text) > 40 else obj.question.text
    question_preview.short_description = 'Question'
    
    def answer_preview(self, obj):
        answer = obj.get_display_answer()
        return answer[:50] + "..." if len(answer) > 50 else answer
    answer_preview.short_description = 'Answer'