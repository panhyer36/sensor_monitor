from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta, datetime
from django.contrib.auth.models import User

from .models import SensorData
from .serializers import SensorDataSerializer

class SensorDataModelTests(TestCase):
    """Test the functionality of the SensorData model"""
    
    def setUp(self):
        """Create test data for each test method"""
        self.sensor_data = SensorData.objects.create(
            co2=450.0,
            humidity=55.5,
            temperature=25.3,
            pm1_0=10.2,
            pm2_5=15.6,
            pm10_0=30.1
        )
    
    def test_sensor_data_creation(self):
        """Test if the SensorData instance can be created correctly"""
        self.assertTrue(isinstance(self.sensor_data, SensorData))
        self.assertEqual(self.sensor_data.co2, 450.0)
        self.assertEqual(self.sensor_data.humidity, 55.5)
        self.assertEqual(self.sensor_data.temperature, 25.3)
        self.assertEqual(self.sensor_data.pm1_0, 10.2)
        self.assertEqual(self.sensor_data.pm2_5, 15.6)
        self.assertEqual(self.sensor_data.pm10_0, 30.1)
        # Confirm timestamp is recent
        self.assertLess((timezone.now() - self.sensor_data.timestamp).seconds, 10)
    
    def test_string_representation(self):
        """Test the string representation of the model"""
        timestamp_str = self.sensor_data.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        expected_str = f"Sensor Data {timestamp_str}"
        self.assertEqual(str(self.sensor_data), expected_str)


class SensorDataSerializerTests(TestCase):
    """Test the functionality of the SensorDataSerializer"""
    
    def setUp(self):
        """Create test data for each test method"""
        self.sensor_data_attributes = {
            'co2': 450.0,
            'humidity': 55.5,
            'temperature': 25.3,
            'pm1_0': 10.2,
            'pm2_5': 15.6,
            'pm10_0': 30.1
        }
        
        self.sensor_data = SensorData.objects.create(**self.sensor_data_attributes)
        self.serializer = SensorDataSerializer(instance=self.sensor_data)
    
    def test_serializer_contains_expected_fields(self):
        """Test if the serializer contains all expected fields"""
        data = self.serializer.data
        self.assertEqual(set(data.keys()), set(['co2', 'humidity', 'temperature', 'pm1_0', 'pm2_5', 'pm10_0', 'timestamp']))
    
    def test_serializer_field_content(self):
        """Test if the field content in the serializer is correct"""
        data = self.serializer.data
        self.assertEqual(float(data['co2']), self.sensor_data_attributes['co2'])
        self.assertEqual(float(data['humidity']), self.sensor_data_attributes['humidity'])
        self.assertEqual(float(data['temperature']), self.sensor_data_attributes['temperature'])
        self.assertEqual(float(data['pm1_0']), self.sensor_data_attributes['pm1_0'])
        self.assertEqual(float(data['pm2_5']), self.sensor_data_attributes['pm2_5'])
        self.assertEqual(float(data['pm10_0']), self.sensor_data_attributes['pm10_0'])
    
    def test_serializer_validation(self):
        """Test if the serializer validates invalid data"""
        invalid_data = {
            'co2': 'invalid', # Should be a float
            'humidity': 55.5,
            'temperature': 25.3,
            'pm1_0': 10.2,
            'pm2_5': 15.6,
            'pm10_0': 30.1
        }
        serializer = SensorDataSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('co2', serializer.errors)


class SensorDataCreateAPIViewTests(APITestCase):
    """Test the functionality of the SensorDataCreateAPIView"""
    
    def setUp(self):
        """Create test data for each test method"""
        self.url = reverse('sensor-create')  # Assuming you have a URL pattern named 'sensor-create'
        self.valid_payload = {
            'co2': 450.0,
            'humidity': 55.5,
            'temperature': 25.3,
            'pm1_0': 10.2,
            'pm2_5': 15.6,
            'pm10_0': 30.1
        }
        self.invalid_payload = {
            'co2': 450.0,
            'humidity': 55.5,
            # Missing other required fields
        }
    
    def test_create_valid_sensor_data(self):
        """Test creating sensor data with valid data"""
        response = self.client.post(
            self.url,
            self.valid_payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SensorData.objects.count(), 1)
        
        # Confirm the values in the database match the submitted values
        sensor_data = SensorData.objects.first()
        self.assertEqual(sensor_data.co2, self.valid_payload['co2'])
        self.assertEqual(sensor_data.humidity, self.valid_payload['humidity'])
        self.assertEqual(sensor_data.temperature, self.valid_payload['temperature'])
        self.assertEqual(sensor_data.pm1_0, self.valid_payload['pm1_0'])
        self.assertEqual(sensor_data.pm2_5, self.valid_payload['pm2_5'])
        self.assertEqual(sensor_data.pm10_0, self.valid_payload['pm10_0'])
    
    def test_create_invalid_sensor_data(self):
        """Test creating sensor data with invalid data"""
        response = self.client.post(
            self.url,
            self.invalid_payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SensorData.objects.count(), 0)


class SensorDataListAPIViewTests(APITestCase):
    """Test the functionality of the SensorDataListAPIView"""
    
    def setUp(self):
        """Create test data for each test method"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
        
        self.url = reverse('sensor-list')  # Assuming you have a URL pattern named 'sensor-list'
        
        # Create some test data
        now = timezone.now()
        
        # Data 30 hours ago
        SensorData.objects.create(
            co2=400.0,
            humidity=50.0,
            temperature=20.0,
            pm1_0=5.0,
            pm2_5=10.0,
            pm10_0=20.0,
            timestamp=now - timedelta(hours=30)
        )
        
        # Data 12 hours ago
        SensorData.objects.create(
            co2=450.0,
            humidity=55.0,
            temperature=22.0,
            pm1_0=7.0,
            pm2_5=12.0,
            pm10_0=25.0,
            timestamp=now - timedelta(hours=12)
        )
        
        # Current data
        SensorData.objects.create(
            co2=500.0,
            humidity=60.0,
            temperature=24.0,
            pm1_0=9.0,
            pm2_5=15.0,
            pm10_0=30.0,
            timestamp=now
        )
        
        # Set up API client
        self.client = APIClient()
    
    def test_get_sensor_data_authenticated(self):
        """Test if an authenticated user can get sensor data"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Default should return data within the last 24 hours (2条)
        self.assertEqual(len(response.data), 2)
    
    def test_filter_by_time_range(self):
        """Test filtering data by time range parameter"""
        self.client.force_authenticate(user=self.user)
        
        # Get data within the last 48 hours (should return all 3条)
        response = self.client.get(f"{self.url}?hours=48")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        
        # Get data within the last 6 hours (should return the latest 1条)
        response = self.client.get(f"{self.url}?hours=6")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        # Test invalid hours parameter, should use default value 24 hours
        response = self.client.get(f"{self.url}?hours=invalid")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
