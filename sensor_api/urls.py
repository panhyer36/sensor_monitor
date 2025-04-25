from django.urls import path
from .views import SensorDataCreateAPIView, SensorDataListAPIView, export_data_view

urlpatterns = [
    path('sensor/', SensorDataCreateAPIView.as_view(), name='sensor-create'),
    path('sensor/list/', SensorDataListAPIView.as_view(), name='sensor-list'),
    path('export/', export_data_view, name='export_data'),
] 