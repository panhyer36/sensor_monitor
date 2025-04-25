from rest_framework import serializers
from .models import SensorData

class SensorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorData
        fields = ['co2', 'humidity', 'temperature', 'pm1_0', 'pm2_5', 'pm10_0', 'timestamp']
        read_only_fields = ['timestamp'] 