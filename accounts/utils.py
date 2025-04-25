from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from .models import UserProfile

def check_threshold_exceeded(sensor_type, value, user_profile):
    """
    Check if the sensor value exceeds the user's threshold settings
    
    Parameters:
    - sensor_type: Sensor type
    - value: Sensor reading
    - user_profile: User profile object
    
    Returns:
    - (exceeded, threshold, direction): Tuple, first value is boolean indicating if threshold is exceeded,
      second is the threshold value, third is the direction ('above' or 'below')
    """
    if sensor_type == 'temperature':
        if value < user_profile.temp_min:
            return True, user_profile.temp_min, 'below'
        elif value > user_profile.temp_max:
            return True, user_profile.temp_max, 'above'
    elif sensor_type == 'humidity':
        if value < user_profile.humidity_min:
            return True, user_profile.humidity_min, 'below'
        elif value > user_profile.humidity_max:
            return True, user_profile.humidity_max, 'above'
    elif sensor_type == 'co2':
        if value > user_profile.co2_max:
            return True, user_profile.co2_max, 'above'
    elif sensor_type == 'pm2_5':
        if value > user_profile.pm25_max:
            return True, user_profile.pm25_max, 'above'
    elif sensor_type == 'pm10_0':
        if value > user_profile.pm10_max:
            return True, user_profile.pm10_max, 'above'
    elif sensor_type == 'aqi':
        if value > user_profile.aqi_max:
            return True, user_profile.aqi_max, 'above'
    
    return False, None, None

def send_sensor_alert_email(sensor_type, value, timestamp):
    """
    Send sensor data alert email based on each user's threshold settings
    
    Parameters:
    - sensor_type: Sensor type (like 'temperature', 'humidity', 'co2', etc.)
    - value: Sensor reading
    - timestamp: Timestamp
    """
    # Get all users with email notifications enabled
    users_with_notification = User.objects.filter(
        profile__email_notifications=True,
        email__isnull=False,
        email__gt=''  # Ensure email is not empty
    ).prefetch_related('profile')
    
    # If no users have notifications enabled, return
    if not users_with_notification.exists():
        return
    
    sensor_name_map = {
        'temperature': 'Temperature',
        'humidity': 'Humidity',
        'co2': 'CO2',
        'pm1_0': 'PM1.0',
        'pm2_5': 'PM2.5',
        'pm10_0': 'PM10.0',
        'aqi': 'AQI (Air Quality Index)'
    }
    
    sensor_unit_map = {
        'temperature': '°C',
        'humidity': '%',
        'co2': 'ppm',
        'pm1_0': 'μg/m³',
        'pm2_5': 'μg/m³',
        'pm10_0': 'μg/m³',
        'aqi': ''
    }
    
    sensor_name = sensor_name_map.get(sensor_type, sensor_type)
    unit = sensor_unit_map.get(sensor_type, '')
    
    notification_sent = 0
    
    # Check threshold and send personalized notifications for each user
    for user in users_with_notification:
        # Check if the value exceeds this user's threshold
        exceeded, threshold, direction = check_threshold_exceeded(sensor_type, value, user.profile)
        
        if exceeded:
            subject = f'Sensor Alert: {sensor_name} Abnormal'
            
            message = f"""
Dear {user.username},

The sensor monitoring system has detected abnormal data:

Sensor type: {sensor_name}
Current value: {value} {unit}
Threshold setting: {direction} {threshold} {unit}
Time: {timestamp}

We recommend checking the sensor monitoring dashboard for more details.

---
This email was sent automatically by the system. Please do not reply.
To modify threshold settings or disable email notifications, please visit the "Threshold Settings" page in your profile.
            """
            
            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,  # Don't raise exceptions on failure
            )
            
            notification_sent += 1
    
    return notification_sent  # Return number of notifications sent 