from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth import login
from django.contrib import messages
from django.shortcuts import redirect
from .forms import CustomUserCreationForm
from surveys.models import Survey
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

class SignUpView(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("login")  # You can change this to "dashboard" if you want
    template_name = "signup.html"
    
    def dispatch(self, request, *args, **kwargs):
        # Redirect authenticated users away from signup page
        if request.user.is_authenticated:
            return redirect('dashboard')  # or wherever you want to redirect logged-in users
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Save the user
        response = super().form_valid(form)
        
        # Get the created user
        user = self.object
        
        # Add success message
        messages.success(
            self.request, 
            f'Account created successfully for {user.username}! Please log in.'
        )
        
        # Optional: Auto-login the user after signup
        # Uncomment the lines below if you want to auto-login
        login(self.request, user)
        messages.success(self.request, f'Welcome, {user.username}!')
        return redirect('survey:dashboard')
        
        return response
    
    def form_invalid(self, form):
        # Add error message for failed signup
        messages.error(
            self.request, 
            'Please correct the errors below.'
        )
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Sign Up'
        return context
    


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "surveys/dashboard.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Dashboard"
        context["surveys"] = Survey.objects.all()  # pass all surveys to dashboard
        return context
