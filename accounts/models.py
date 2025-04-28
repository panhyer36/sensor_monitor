from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.

class UserProfile(models.Model):
    """User profile model for storing notification preferences and external API keys"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    api_key = models.CharField(max_length=255, blank=True, null=True, help_text="Optional: Your personal API Key for the external LLM service.")
    email_notifications = models.BooleanField(default=False, help_text="Receive email alerts for sensor data alerts")
    
    # Sensor notification threshold settings
    temp_min = models.FloatField(default=10.0, help_text="Minimum temperature (°C)")
    temp_max = models.FloatField(default=30.0, help_text="Maximum temperature (°C)")
    humidity_min = models.FloatField(default=20.0, help_text="Minimum humidity (%)")
    humidity_max = models.FloatField(default=80.0, help_text="Maximum humidity (%)")
    co2_max = models.FloatField(default=1000.0, help_text="Maximum CO2 level (ppm)")
    pm25_max = models.FloatField(default=35.0, help_text="Maximum PM2.5 level (μg/m³)")
    pm10_max = models.FloatField(default=150.0, help_text="Maximum PM10 level (μg/m³)")
    aqi_max = models.FloatField(default=100.0, help_text="Maximum AQI")
    
    def __str__(self):
        return f"{self.user.username}'s profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Signal to create a user profile when a new user is created"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Signal to save a user profile when the user is saved"""
    instance.profile.save()

class IssueReport(models.Model):
    """User reported issue model"""
    ISSUE_TYPES = [
        ('bug', 'Bug/Error'),
        ('feature', 'Feature Request'),
        ('sensor', 'Sensor Problem'),
        ('data', 'Data Issue'),
        ('other', 'Other')
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    ]
    
    title = models.CharField(max_length=100)
    description = models.TextField()
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPES)
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    email = models.EmailField(blank=True, null=True, help_text="Optional email for updates")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    admin_notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.title} ({self.get_issue_type_display()}) - {self.get_status_display()}"
    
    class Meta:
        ordering = ['-created_at']
