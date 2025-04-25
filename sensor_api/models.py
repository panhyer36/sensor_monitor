from django.db import models
from django.utils import timezone

class SensorData(models.Model):
    co2 = models.FloatField()
    humidity = models.FloatField()
    temperature = models.FloatField()
    pm1_0 = models.FloatField()
    pm2_5 = models.FloatField()
    pm10_0 = models.FloatField()
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Sensor Data {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
