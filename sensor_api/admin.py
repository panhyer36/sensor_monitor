from django.contrib import admin
from .models import SensorData

@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'temperature', 'humidity', 'co2', 'pm1_0', 'pm2_5', 'pm10_0')
    list_filter = ('timestamp',)
    search_fields = ('timestamp',)
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'

    fieldsets = (
        ('Time Information', {
            'fields': ('timestamp',)
        }),
        ('Environmental Data', {
            'fields': ('temperature', 'humidity', 'co2')
        }),
        ('Air Quality Data', {
            'fields': ('pm1_0', 'pm2_5', 'pm10_0')
        }),
    )
