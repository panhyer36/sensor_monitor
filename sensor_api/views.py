from django.shortcuts import render
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from .models import SensorData
from .serializers import SensorDataSerializer
import csv
import json
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta, datetime

# Create your views here.

class SensorDataCreateAPIView(generics.CreateAPIView):
    queryset = SensorData.objects.all()
    serializer_class = SensorDataSerializer
    permission_classes = [permissions.AllowAny]  # Allow anyone to send data
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class SensorDataListAPIView(generics.ListAPIView):
    serializer_class = SensorDataSerializer
    permission_classes = [permissions.IsAuthenticated]  # Only logged in users can view data
    
    def get_queryset(self):
        # 获取时间范围参数，默认为24小时
        hours = self.request.query_params.get('hours', '24')
        
        try:
            # 将小时数转换为整数
            hours = int(hours)
        except ValueError:
            # 如果转换失败，默认为24小时
            hours = 24
            
        # 计算开始时间
        end_date = timezone.now()
        start_date = end_date - timedelta(hours=hours)
        
        # 根据时间范围过滤数据
        queryset = SensorData.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('timestamp')
        
        return queryset

@login_required
def export_data_view(request):
    """Process sensor data export functionality"""
    if request.method == 'GET':
        # Display export options page
        return render(request, 'sensor_api/export_data.html')
    
    elif request.method == 'POST':
        format_type = request.POST.get('format', 'csv')
        time_range = request.POST.get('time_range', '7days')
        sensor_types = request.POST.getlist('sensor_types', ['all'])
        
        # Filter data based on time range
        end_date = timezone.now()
        if time_range == '24hours':
            start_date = end_date - timedelta(days=1)
        elif time_range == '7days':
            start_date = end_date - timedelta(days=7)
        elif time_range == '30days':
            start_date = end_date - timedelta(days=30)
        elif time_range == 'custom':
            # Parse custom date range
            try:
                start_date_str = request.POST.get('start_date', '')
                end_date_str = request.POST.get('end_date', '')
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            except ValueError:
                return render(request, 'sensor_api/export_data.html', {
                    'error': 'Invalid date format. Please use YYYY-MM-DD format.'
                })
        else:
            start_date = end_date - timedelta(days=7)  # Default to 7 days
        
        # Query data for specified time range
        sensor_data = SensorData.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('timestamp')
        
        if not sensor_data:
            return render(request, 'sensor_api/export_data.html', {
                'error': 'No data found for the selected time range.'
            })
        
        # Export data based on selected format
        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="sensor_data_{start_date.strftime("%Y%m%d")}_to_{end_date.strftime("%Y%m%d")}.csv"'
            
            writer = csv.writer(response)
            
            # Decide which fields to include
            fields = ['timestamp']
            if 'all' in sensor_types or 'temperature' in sensor_types:
                fields.append('temperature')
            if 'all' in sensor_types or 'humidity' in sensor_types:
                fields.append('humidity')
            if 'all' in sensor_types or 'co2' in sensor_types:
                fields.append('co2')
            if 'all' in sensor_types or 'pm1_0' in sensor_types:
                fields.append('pm1_0')
            if 'all' in sensor_types or 'pm2_5' in sensor_types:
                fields.append('pm2_5')
            if 'all' in sensor_types or 'pm10_0' in sensor_types:
                fields.append('pm10_0')
            
            # Write header row
            writer.writerow(fields)
            
            # Write data rows
            for data in sensor_data:
                row = [data.timestamp.strftime('%Y-%m-%d %H:%M:%S')]
                if 'all' in sensor_types or 'temperature' in sensor_types:
                    row.append(data.temperature)
                if 'all' in sensor_types or 'humidity' in sensor_types:
                    row.append(data.humidity)
                if 'all' in sensor_types or 'co2' in sensor_types:
                    row.append(data.co2)
                if 'all' in sensor_types or 'pm1_0' in sensor_types:
                    row.append(data.pm1_0)
                if 'all' in sensor_types or 'pm2_5' in sensor_types:
                    row.append(data.pm2_5)
                if 'all' in sensor_types or 'pm10_0' in sensor_types:
                    row.append(data.pm10_0)
                writer.writerow(row)
                
            return response
            
        elif format_type == 'json':
            data_list = []
            
            for data in sensor_data:
                data_dict = {'timestamp': data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
                
                if 'all' in sensor_types or 'temperature' in sensor_types:
                    data_dict['temperature'] = data.temperature
                if 'all' in sensor_types or 'humidity' in sensor_types:
                    data_dict['humidity'] = data.humidity
                if 'all' in sensor_types or 'co2' in sensor_types:
                    data_dict['co2'] = data.co2
                if 'all' in sensor_types or 'pm1_0' in sensor_types:
                    data_dict['pm1_0'] = data.pm1_0
                if 'all' in sensor_types or 'pm2_5' in sensor_types:
                    data_dict['pm2_5'] = data.pm2_5
                if 'all' in sensor_types or 'pm10_0' in sensor_types:
                    data_dict['pm10_0'] = data.pm10_0
                
                data_list.append(data_dict)
            
            response = HttpResponse(json.dumps(data_list, indent=4), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="sensor_data_{start_date.strftime("%Y%m%d")}_to_{end_date.strftime("%Y%m%d")}.json"'
            return response
        
        else:
            return render(request, 'sensor_api/export_data.html', {
                'error': 'Invalid export format selected.'
            })
