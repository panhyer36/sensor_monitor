from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import IssueReport, UserProfile

class CustomUserCreationForm(UserCreationForm):
    """Custom registration form that includes email field"""
    email = forms.EmailField(max_length=254, required=False, 
                           help_text='Optional. Used to receive notifications and important alerts.')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False, label='First Name')
    last_name = forms.CharField(max_length=30, required=False, label='Last Name')
    email = forms.EmailField(max_length=254, required=False, label='Email')
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class ApiKeyForm(forms.ModelForm):
    """Form for managing the user's LLM API Key"""
    class Meta:
        model = UserProfile
        fields = ['api_key']
        labels = {
            'api_key': 'DeepSeek API Key (Optional)',
        }
        widgets = {
            'api_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your DeepSeek API Key'}),
        }
        help_texts = {
            'api_key': 'This key will be used to connect to the DeepSeek service on your behalf.'
        }

class NotificationSettingsForm(forms.ModelForm):
    """Form for user notification settings"""
    class Meta:
        model = UserProfile
        fields = ['email_notifications']
        labels = {
            'email_notifications': 'Receive Email Notifications',
        }
        help_texts = {
            'email_notifications': 'When sensor data exceeds normal range, we will notify you by email'
        }

class ThresholdSettingsForm(forms.ModelForm):
    """Form for user threshold settings"""
    class Meta:
        model = UserProfile
        fields = [
            'temp_min', 'temp_max', 
            'humidity_min', 'humidity_max',
            'co2_max', 'pm25_max', 'pm10_max', 'aqi_max'
        ]
        labels = {
            'temp_min': 'Minimum Temperature',
            'temp_max': 'Maximum Temperature',
            'humidity_min': 'Minimum Humidity',
            'humidity_max': 'Maximum Humidity',
            'co2_max': 'Maximum CO2 Level',
            'pm25_max': 'Maximum PM2.5 Level',
            'pm10_max': 'Maximum PM10 Level',
            'aqi_max': 'Maximum AQI',
        }
        widgets = {
            'temp_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'temp_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'humidity_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'humidity_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'co2_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'pm25_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'pm10_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'aqi_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        }

class UsernameChangeForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, label='New Username')
    
    class Meta:
        model = User
        fields = ['username']
        
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

class CustomPasswordChangeForm(PasswordChangeForm):
    """Custom Password Change Form with Bootstrap styling"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'}) 

class IssueReportForm(forms.ModelForm):
    """User reported issue form"""
    email = forms.EmailField(required=False, help_text="Optional email for updates on your report")
    
    class Meta:
        model = IssueReport
        fields = ['title', 'description', 'issue_type', 'email']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'issue_type': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap styling
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Customize labels and help text
        self.fields['title'].help_text = "Brief summary of the issue"
        self.fields['description'].help_text = "Please provide details about the issue"
        
        # Add placeholder to email field instead of pre-filled value
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Enter your email address (optional)'
        }) 