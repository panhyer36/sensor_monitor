from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages

from .models import UserProfile, IssueReport
from .forms import UserProfileForm, IssueReportForm

class UserProfileModelTests(TestCase):
    """Test the functionality of the UserProfile model"""
    
    def setUp(self):
        """Create test data for each test method"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        # UserProfile should be automatically created through the signal
    
    def test_profile_creation(self):
        """Test if a profile is automatically created when a user is created"""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertTrue(isinstance(self.user.profile, UserProfile))
    
    def test_profile_default_values(self):
        """Test if the default values for the profile are correctly set"""
        profile = self.user.profile
        self.assertEqual(profile.email_notifications, False)
        self.assertEqual(profile.temp_min, 10.0)
        self.assertEqual(profile.temp_max, 30.0)
        self.assertEqual(profile.humidity_min, 20.0)
        self.assertEqual(profile.humidity_max, 80.0)
        self.assertEqual(profile.co2_max, 1000.0)
        self.assertEqual(profile.pm25_max, 35.0)
        self.assertEqual(profile.pm10_max, 150.0)
        self.assertEqual(profile.aqi_max, 100.0)
    
    def test_string_representation(self):
        """Test the string representation of the model"""
        expected_str = f"{self.user.username}'s profile"
        self.assertEqual(str(self.user.profile), expected_str)


class IssueReportModelTests(TestCase):
    """Test the functionality of the IssueReport model"""
    
    def setUp(self):
        """Create test data for each test method"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        
        self.issue = IssueReport.objects.create(
            title='Test Issue',
            description='This is a test issue description',
            issue_type='bug',
            reporter=self.user,
            email='reporter@example.com'
        )
    
    def test_issue_creation(self):
        """Test if the issue report is correctly created"""
        self.assertTrue(isinstance(self.issue, IssueReport))
        self.assertEqual(self.issue.title, 'Test Issue')
        self.assertEqual(self.issue.description, 'This is a test issue description')
        self.assertEqual(self.issue.issue_type, 'bug')
        self.assertEqual(self.issue.reporter, self.user)
        self.assertEqual(self.issue.email, 'reporter@example.com')
        self.assertEqual(self.issue.status, 'new')  # Default status should be 'new'
        self.assertIsNone(self.issue.admin_notes)
    
    def test_string_representation(self):
        """Test the string representation of the model"""
        expected_str = "Test Issue (Bug/Error) - New"
        self.assertEqual(str(self.issue), expected_str)
    
    def test_ordering(self):
        """Test the ordering of the issue report (should be sorted by creation time)"""
        # Create another issue report
        newer_issue = IssueReport.objects.create(
            title='Newer Issue',
            description='This is a newer issue',
            issue_type='feature',
            reporter=self.user
        )
        
        # Get all issue reports and check the order
        issues = IssueReport.objects.all()
        self.assertEqual(issues[0], newer_issue)  # The newer issue should be in front
        self.assertEqual(issues[1], self.issue)


class UserProfileFormTests(TestCase):
    """Test the functionality of the UserProfileForm"""
    
    def setUp(self):
        """Create test data for each test method"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        
        self.form_data = {
            'email_notifications': True,
            'temp_min': 15.0,
            'temp_max': 28.0,
            'humidity_min': 30.0,
            'humidity_max': 70.0,
            'co2_max': 800.0,
            'pm25_max': 25.0,
            'pm10_max': 100.0,
            'aqi_max': 80.0
        }
    
    def test_valid_form(self):
        """Test the form validation with valid data"""
        form = UserProfileForm(data=self.form_data, instance=self.user.profile)
        self.assertTrue(form.is_valid())


class IssueReportFormTests(TestCase):
    """Test the functionality of the IssueReportForm"""
    
    def setUp(self):
        """Create test data for each test method"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        
        self.form_data = {
            'title': 'Test Issue',
            'description': 'This is a test issue description',
            'issue_type': 'bug',
            'email': 'reporter@example.com'
        }
    
    def test_valid_form(self):
        """Test the form validation with valid data"""
        form = IssueReportForm(data=self.form_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_form_missing_required_fields(self):
        """Test the form validation with missing required fields"""
        invalid_data = self.form_data.copy()
        invalid_data.pop('description')
        
        form = IssueReportForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('description', form.errors)
    
    def test_invalid_email(self):
        """Test the form validation with invalid email address"""
        invalid_data = self.form_data.copy()
        invalid_data['email'] = 'invalid-email'
        
        form = IssueReportForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class LoginViewTests(TestCase):
    """Test the functionality of the LoginView"""
    
    def setUp(self):
        """Create test data for each test method"""
        self.client = Client()
        self.login_url = reverse('login')  # Assuming you have a URL pattern named 'login'
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
    
    def test_login_page_loads(self):
        """Test if the login page is correctly loaded"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')  # Assuming you use this template
    
    def test_invalid_login(self):
        """Test invalid login attempt"""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        # Should stay on the login page
        self.assertEqual(response.status_code, 200)
        
        # Check if error message is displayed
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Invalid' in str(message) for message in messages))
        
        # User should not be authenticated
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class ProfileUpdateViewTests(TestCase):
    """Test the functionality of the ProfileUpdateView"""
    
    def setUp(self):
        """Create test data for each test method"""
        self.client = Client()
        self.profile_url = reverse('profile')  # Assuming you have a URL pattern named 'profile'
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        
        # Ensure user is logged in
        self.client.login(username='testuser', password='password123')
    
    def test_profile_page_loads(self):
        """Test if the profile page is correctly loaded"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')  # Assuming you use this template
    
    def test_unauthenticated_access(self):
        """Test if unauthenticated users are redirected to the login page"""
        # Log out first
        self.client.logout()
        
        response = self.client.get(self.profile_url)
        
        # Should redirect to the login page
        self.assertRedirects(response, f'{reverse("login")}?next={self.profile_url}')

class PageSecurityTests(TestCase):

    def setup(self):
        self.client = Client()

    # Tests for unauthenticated access attempts to various pages
    # Each attempt should show a redirect to the login page
    # Homepage unauthorized access attempt test
    def test_unauthenticated_access_attempt_homePage(self):
        response = self.client.get(reverse('home')) # page attempting to be accessed
        self.assertEqual(response.status_code, 302) # redirect occured
        self.assertTrue(response.url.startswith('/accounts/login/')) # redirect to login page


    # reportpage unauthorized access attempt test
    def test_unauthenticated_access_attemp_reportPage(self):
        response = self.client.get(reverse('report')) # page attempting to be accessed
        self.assertEqual(response.status_code, 302) # redirect occured
        self.assertTrue(response.url.startswith('/accounts/login/')) # redirect to login page


    # chatbotpage unauthorized access attempt test
    def test_unauthenticated_access_attempt_chatbotPage(self):
        response = self.client.get(reverse('chatbot')) # page attempting to be accessed
        self.assertEqual(response.status_code, 302) # redirect occured
        self.assertTrue(response.url.startswith('/accounts/login/')) # redirect to login page


    # analysispage unauthorized access attempt test
    def test_unauthenticated_access_attempt_analysisPage(self):
        response = self.client.get(reverse('analyze')) # page attempting to be accessed
        self.assertEqual(response.status_code, 302) # redirect occured
        self.assertTrue(response.url.startswith('/accounts/login/')) # redirect to login page


    # profilepage unauthorized access attempt test
    def test_unauthenticated_access_attempt_profilePage(self):
        response = self.client.get(reverse('profile')) # page attempting to be accessed
        self.assertEqual(response.status_code, 302) # redirect occured
        self.assertTrue(response.url.startswith('/accounts/login/')) # redirect to login page
