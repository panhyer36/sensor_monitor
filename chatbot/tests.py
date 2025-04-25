from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from .models import ChatbotQA

class ChatbotQAModelTests(TestCase):
    """Test the functionality of the ChatbotQA model"""
    
    def setUp(self):
        """Create test data for each test method"""
        self.qa1 = ChatbotQA.objects.create(
            question="What is the temperature sensor?",
            answer="The temperature sensor measures ambient temperature in degrees Celsius."
        )
        
        self.qa2 = ChatbotQA.objects.create(
            question="How to analyze data?",
            answer="You can analyze sensor data by using the export feature and choosing CSV or JSON format."
        )
        
        self.qa3 = ChatbotQA.objects.create(
            question="PM2.5 sensor specifications",
            answer="The PM2.5 sensor has a range of 0-500 μg/m³ with an accuracy of ±10%."
        )
    
    def test_qa_creation(self):
        """Test if the QA entries are correctly created"""
        self.assertTrue(isinstance(self.qa1, ChatbotQA))
        self.assertEqual(self.qa1.question, "What is the temperature sensor?")
        self.assertEqual(self.qa1.answer, "The temperature sensor measures ambient temperature in degrees Celsius.")
        
        # Confirm that the timestamps are set
        self.assertIsNotNone(self.qa1.created_at)
        self.assertIsNotNone(self.qa1.updated_at)
    
    def test_string_representation(self):
        """Test the string representation of the model"""
        self.assertEqual(str(self.qa1), "What is the temperature sensor?")
    
    def test_find_best_match_exact(self):
        """Test the exact match situation"""
        # Exact match question
        match = ChatbotQA.find_best_match("What is the temperature sensor?")
        self.assertEqual(match, self.qa1)
    
    def test_find_best_match_case_insensitive(self):
        """Test the case insensitive situation"""
        # Case insensitive match
        match = ChatbotQA.find_best_match("what is the temperature sensor?")
        self.assertEqual(match, self.qa1)
    
    def test_find_best_match_partial(self):
        """Test the partial match situation"""
        # Partial keyword match
        match = ChatbotQA.find_best_match("temperature sensor specs")
        self.assertEqual(match, self.qa1)  # Should match the first question
        
        # Another partial match
        match = ChatbotQA.find_best_match("PM2.5 sensor information")
        self.assertEqual(match, self.qa3)  # Should match the third question
    
    def test_find_best_match_no_match(self):
        """Test the situation where no match is found"""
        # Completely unrelated query
        match = ChatbotQA.find_best_match("How to reset my password?")
        self.assertIsNone(match)  # Should return None


class ChatbotAPIViewTests(TestCase):
    """Test the functionality of the ChatbotAPIView"""
    
    def setUp(self):
        """Create test data for each test method"""
        self.client = Client()
        self.chatbot_url = reverse('chatbot_api')  # Assuming you have a URL pattern named 'chatbot_api'
        
        # Create test QA entries
        self.qa1 = ChatbotQA.objects.create(
            question="What is the temperature sensor?",
            answer="The temperature sensor measures ambient temperature in degrees Celsius."
        )
        
        self.qa2 = ChatbotQA.objects.create(
            question="How to analyze data?",
            answer="You can analyze sensor data by using the export feature and choosing CSV or JSON format."
        )
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        
        # Ensure user is logged in (if API requires authentication)
        self.client.login(username='testuser', password='password123')
    
    def test_chatbot_invalid_request_method(self):
        """Test accessing the chatbot API with an invalid request method"""
        response = self.client.get(self.chatbot_url)
        
        self.assertEqual(response.status_code, 405)  # Assuming only POST requests are allowed, GET returns 405 error


class ChatbotWebInterfaceTests(TestCase):
    """Test the functionality of the Chatbot web interface"""
    
    def setUp(self):
        """Create test data for each test method"""
        self.client = Client()
        self.chatbot_url = reverse('chatbot')  # Assuming you have a URL pattern named 'chatbot'
        
        # Create test QA entries
        self.qa = ChatbotQA.objects.create(
            question="What is the temperature sensor?",
            answer="The temperature sensor measures ambient temperature in degrees Celsius."
        )
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
    
    def test_chatbot_page_loads_authenticated(self):
        """Test if an authenticated user can load the chatbot page"""
        # Login user
        self.client.login(username='testuser', password='password123')
        
        response = self.client.get(self.chatbot_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'chatbot/chatbot.html')  # Assuming you use this template
    
    def test_chatbot_page_loads_unauthenticated(self):
        """Test if an unauthenticated user is redirected to the login page"""
        response = self.client.get(self.chatbot_url)
        
        # Assuming the chatbot page requires authentication
        self.assertRedirects(response, f'{reverse("login")}?next={self.chatbot_url}')
