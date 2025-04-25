from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Avg, Max, Min, Count
import datetime  # import the entire datetime module
from accounts.forms import (
    UserProfileForm, CustomPasswordChangeForm, UsernameChangeForm, 
    IssueReportForm, CustomUserCreationForm, NotificationSettingsForm,
    ThresholdSettingsForm, ApiKeyForm
)
from .models import IssueReport, UserProfile
from sensor_api.models import SensorData
from django.views.decorators.http import require_POST # Import require_POST
import requests # Import requests library
import json # Import json library

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            if email:  # If user provided an email, update profile
                user.email = email
                user.save()
            
            messages.success(request, f"Account successfully created for {username}! You can now log in.")
            return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                # Check if user has a profile, create one if not
                try:
                    user.profile
                except:  # Catch any exception, including RelatedObjectDoesNotExist
                    UserProfile.objects.create(user=user)
                
                login(request, user)
                return redirect('home')
        else:
            messages.error(request, "Invalid username or password")
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def home_view(request):
    return render(request, 'accounts/home.html')

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('login')

@login_required
def profile_view(request):
    profile_form = UserProfileForm(instance=request.user)
    password_form = CustomPasswordChangeForm(request.user)
    username_form = UsernameChangeForm(instance=request.user)
    notification_form = NotificationSettingsForm(instance=request.user.profile)
    threshold_form = ThresholdSettingsForm(instance=request.user.profile)
    api_key_form = ApiKeyForm(instance=request.user.profile)
    
    active_tab = 'profile'
    
    if request.method == 'POST':
        if 'profile_submit' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=request.user)
            active_tab = 'profile'
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Your profile has been updated successfully!')
                return redirect('profile')
        
        elif 'password_submit' in request.POST:
            password_form = CustomPasswordChangeForm(request.user, request.POST)
            active_tab = 'password'
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password has been changed successfully!')
                return redirect('profile')
                
        elif 'username_submit' in request.POST:
            username_form = UsernameChangeForm(request.POST, instance=request.user)
            active_tab = 'username'
            if username_form.is_valid():
                user = username_form.save()
                # Re-login to update session
                login(request, user)
                messages.success(request, 'Your username has been changed successfully!')
                return redirect('profile')
                
        elif 'notification_submit' in request.POST:
            notification_form = NotificationSettingsForm(request.POST, instance=request.user.profile)
            active_tab = 'notifications'
            if notification_form.is_valid():
                notification_form.save()
                messages.success(request, 'Your notification settings have been updated successfully!')
                return redirect('profile')
                
        elif 'threshold_submit' in request.POST:
            threshold_form = ThresholdSettingsForm(request.POST, instance=request.user.profile)
            active_tab = 'thresholds'
            if threshold_form.is_valid():
                threshold_form.save()
                messages.success(request, 'Your threshold settings have been updated successfully!')
                return redirect('profile')
        
        elif 'api_key_submit' in request.POST:
            api_key_form = ApiKeyForm(request.POST, instance=request.user.profile)
            active_tab = 'profile'
            if api_key_form.is_valid():
                api_key_form.save()
                messages.success(request, 'Your API Key has been updated successfully!')
                return redirect('profile')
    
    context = {
        'profile_form': profile_form,
        'password_form': password_form,
        'username_form': username_form,
        'notification_form': notification_form,
        'threshold_form': threshold_form,
        'api_key_form': api_key_form,
        'active_tab': active_tab
    }
    
    return render(request, 'accounts/profile.html', context)

@login_required
def report_issue_view(request):
    """Display the issue report form and process submission"""
    if request.method == 'POST':
        form = IssueReportForm(request.POST)
        if form.is_valid():
            # Create report without saving to database
            report = form.save(commit=False)
            # Set reporter to current user
            report.reporter = request.user
            # Save report
            report.save()
            
            messages.success(request, "Your issue has been reported. Thank you for your feedback!")
            return redirect('home')
    else:
        # No longer pre-fill email, set placeholder in form class
        form = IssueReportForm()
    
    return render(request, 'accounts/report_issue.html', {
        'form': form
    })

@login_required
def send_test_email(request):
    """Send a test email to the user's inbox"""
    if request.method == 'POST':
        user = request.user
        if not user.email:
            return JsonResponse({
                'success': False,
                'message': 'You have not set an email address. Please add an email in your profile first.'
            })
            
        subject = 'Test Notification Email - AMI Sensor Monitoring System'
        message = f"""
Dear {user.username},

This is a test email to verify that your email address {user.email} can receive notifications from the AMI Sensor Monitoring System.

If you received this email, your notification settings are working correctly. When sensor data is abnormal, the system will send you alerts via email.

Sincerely,
AMI Sensor Monitoring System
        """
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            # Log
            print(f"Test email sent to user {user.username} ({user.email})")
            
            return JsonResponse({
                'success': True,
                'message': f'Test email has been sent to {user.email}. Please check your inbox.'
            })
        except Exception as e:
            print(f"Email sending failed: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Failed to send email: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=400)

@login_required
def analyze_view(request):
    """Display analysis of current and historical sensor data with recommendations"""
    
    # Get the latest sensor data
    latest_data = SensorData.objects.order_by('-timestamp').first()
    
    # Get today's data - use the current timezone's date
    today = timezone.localtime(timezone.now()).date()
    print(f"Using today's date in local timezone: {today}")
    
    # Using __date filtering might use UTC, so we explicitly specify the date range for the current timezone
    today_start = timezone.make_aware(datetime.datetime.combine(today, datetime.time.min))
    today_end = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))
    print(f"Today date range: {today_start} to {today_end}")
    
    today_data = SensorData.objects.filter(
        timestamp__gte=today_start,
        timestamp__lte=today_end
    )
    today_stats = today_data.aggregate(
        avg_co2=Avg('co2'),
        avg_humidity=Avg('humidity'),
        avg_temperature=Avg('temperature'),
        avg_pm1_0=Avg('pm1_0'),
        avg_pm2_5=Avg('pm2_5'),
        avg_pm10_0=Avg('pm10_0'),
        max_co2=Max('co2'),
        max_humidity=Max('humidity'),
        max_temperature=Max('temperature'),
        max_pm1_0=Max('pm1_0'),
        max_pm2_5=Max('pm2_5'),
        max_pm10_0=Max('pm10_0'),
        min_co2=Min('co2'),
        min_humidity=Min('humidity'),
        min_temperature=Min('temperature'),
        min_pm1_0=Min('pm1_0'),
        min_pm2_5=Min('pm2_5'),
        min_pm10_0=Min('pm10_0'),
    )
    
    # Daily hourly analysis (4 hours per slot)
    time_slots = {}
    time_slot_names = {
        0: "Early Morning (12am-4am)",
        1: "Morning (4am-8am)",
        2: "Late Morning (8am-12pm)",
        3: "Afternoon (12pm-4pm)",
        4: "Evening (4pm-8pm)",
        5: "Night (8pm-12am)"
    }
    
    # Initialize data containers for each time slot
    for slot in range(6):
        time_slots[slot] = {
            'data': [],
            'name': time_slot_names[slot],
            'avg_co2': 0,
            'avg_pm2_5': 0,
            'avg_temperature': 0,
            'avg_humidity': 0
        }
    
    # Categorize today's data by time slot
    for entry in today_data:
        # Ensure using local timezone's time
        local_timestamp = timezone.localtime(entry.timestamp)
        hour = local_timestamp.hour
        print(f"Entry: {entry.id}, UTC timestamp: {entry.timestamp}, Local hour: {hour}")
        
        slot = hour // 4  # One session every 4 hours
        time_slots[slot]['data'].append(entry)
    
    # Calculate the average value for each time slot
    worst_slot = None
    worst_slot_score = 0
    
    for slot, data in time_slots.items():
        if data['data']:
            co2_values = [entry.co2 for entry in data['data']]
            pm25_values = [entry.pm2_5 for entry in data['data']]
            temp_values = [entry.temperature for entry in data['data']]
            humidity_values = [entry.humidity for entry in data['data']]
            
            avg_co2 = sum(co2_values) / len(co2_values)
            avg_pm25 = sum(pm25_values) / len(pm25_values)
            avg_temp = sum(temp_values) / len(temp_values)
            avg_humidity = sum(humidity_values) / len(humidity_values)
            
            time_slots[slot]['avg_co2'] = avg_co2
            time_slots[slot]['avg_pm2_5'] = avg_pm25
            time_slots[slot]['avg_temperature'] = avg_temp
            time_slots[slot]['avg_humidity'] = avg_humidity
            
            # Calculate the air quality score (simply weighted CO2 and PM2.5)
            slot_score = (avg_co2 / 500) + (avg_pm25 / 10)  # Normalize
            
            if slot_score > worst_slot_score:
                worst_slot_score = slot_score
                worst_slot = slot
    
    # Get data from the past 7 days
    week_ago = today - datetime.timedelta(days=7)
    weekly_data = SensorData.objects.filter(timestamp__date__gte=week_ago)
    weekly_stats = weekly_data.aggregate(
        avg_co2=Avg('co2'),
        avg_humidity=Avg('humidity'),
        avg_temperature=Avg('temperature'),
        avg_pm1_0=Avg('pm1_0'),
        avg_pm2_5=Avg('pm2_5'),
        avg_pm10_0=Avg('pm10_0'),
        max_co2=Max('co2'),
        max_humidity=Max('humidity'),
        max_temperature=Max('temperature'),
        max_pm1_0=Max('pm1_0'),
        max_pm2_5=Max('pm2_5'),
        max_pm10_0=Max('pm10_0'),
        min_co2=Min('co2'),
        min_humidity=Min('humidity'),
        min_temperature=Min('temperature'),
        min_pm1_0=Min('pm1_0'),
        min_pm2_5=Min('pm2_5'),
        min_pm10_0=Min('pm10_0'),
    )
    
    # Analyze data from the past 7 days by day
    daily_stats = {}
    days_of_week = {
        0: "Monday",
        1: "Tuesday",
        2: "Wednesday",
        3: "Thursday", 
        4: "Friday",
        5: "Saturday",
        6: "Sunday"
    }
    
    # Calculate the average value for each day in the past 7 days
    for i in range(7):
        day_date = today - datetime.timedelta(days=i)
        day_name = days_of_week[day_date.weekday()]
        
        day_data = SensorData.objects.filter(timestamp__date=day_date)
        if day_data.exists():
            day_stats = day_data.aggregate(
                avg_co2=Avg('co2'),
                avg_pm2_5=Avg('pm2_5'),
                avg_temperature=Avg('temperature'),
                avg_humidity=Avg('humidity'),
                count=Count('id')
            )
            daily_stats[i] = {
                'date': day_date,
                'name': day_name,
                'avg_co2': day_stats['avg_co2'],
                'avg_pm2_5': day_stats['avg_pm2_5'],
                'avg_temperature': day_stats['avg_temperature'],
                'avg_humidity': day_stats['avg_humidity'],
                'count': day_stats['count']
            }
    
    # Find the day with the worst air quality
    worst_day = None
    worst_day_score = 0
    
    for day_index, stats in daily_stats.items():
        if stats.get('avg_co2') and stats.get('avg_pm2_5'):
            day_score = (stats['avg_co2'] / 500) + (stats['avg_pm2_5'] / 10)
            if day_score > worst_day_score:
                worst_day_score = day_score
                worst_day = day_index
    
    # Get data from the past 30 days
    month_ago = today - datetime.timedelta(days=30)
    monthly_data = SensorData.objects.filter(timestamp__date__gte=month_ago)
    monthly_stats = monthly_data.aggregate(
        avg_co2=Avg('co2'),
        avg_humidity=Avg('humidity'),
        avg_temperature=Avg('temperature'),
        avg_pm1_0=Avg('pm1_0'),
        avg_pm2_5=Avg('pm2_5'),
        avg_pm10_0=Avg('pm10_0'),
    )
    
    # Analyze data from the past 30 days by week
    weekly_breakdown = {}
    
    for i in range(4):  # Past 4 weeks
        week_start = today - datetime.timedelta(days=today.weekday() + 7*i)
        week_end = week_start + datetime.timedelta(days=6)
        
        week_data = SensorData.objects.filter(
            timestamp__date__gte=week_start,
            timestamp__date__lte=week_end
        )
        
        if week_data.exists():
            week_stats = week_data.aggregate(
                avg_co2=Avg('co2'),
                avg_pm2_5=Avg('pm2_5'),
                avg_temperature=Avg('temperature'),
                avg_humidity=Avg('humidity'),
                count=Count('id')
            )
            
            weekly_breakdown[i] = {
                'start_date': week_start,
                'end_date': week_end,
                'avg_co2': week_stats['avg_co2'],
                'avg_pm2_5': week_stats['avg_pm2_5'],
                'avg_temperature': week_stats['avg_temperature'],
                'avg_humidity': week_stats['avg_humidity'],
                'count': week_stats['count']
            }
    
    # Find the week with the worst air quality
    worst_week = None
    worst_week_score = 0
    
    for week_index, stats in weekly_breakdown.items():
        if stats.get('avg_co2') and stats.get('avg_pm2_5'):
            week_score = (stats['avg_co2'] / 500) + (stats['avg_pm2_5'] / 10)
            if week_score > worst_week_score:
                worst_week_score = week_score
                worst_week = week_index
    
    # Add the worst week data to the weekly_breakdown dictionary, so it can be accessed directly by dot syntax
    if worst_week is not None and worst_week in weekly_breakdown:
        weekly_breakdown['worst_week'] = weekly_breakdown[worst_week]
        
    # Add the worst slot data to the time_slots dictionary, so it can be accessed directly by dot syntax
    if worst_slot is not None and worst_slot in time_slots:
        time_slots['worst_slot'] = time_slots[worst_slot]
        
    # Add the worst day data to the daily_stats dictionary, so it can be accessed directly by dot syntax
    if worst_day is not None and worst_day in daily_stats:
        daily_stats['worst_day'] = daily_stats[worst_day]
    
    # Pre-calculate differences to avoid arithmetic operations in the template
    differences = {}
    
    # Today data differences
    if today_stats['max_co2'] is not None and today_stats['min_co2'] is not None:
        differences['today_co2_diff'] = today_stats['max_co2'] - today_stats['min_co2']
    else:
        differences['today_co2_diff'] = 0
        
    if today_stats['max_temperature'] is not None and today_stats['min_temperature'] is not None:
        differences['today_temp_diff'] = today_stats['max_temperature'] - today_stats['min_temperature']
    else:
        differences['today_temp_diff'] = 0
        
    if today_stats['max_humidity'] is not None and today_stats['min_humidity'] is not None:
        differences['today_humidity_diff'] = today_stats['max_humidity'] - today_stats['min_humidity']
    else:
        differences['today_humidity_diff'] = 0
        
    if today_stats['max_pm2_5'] is not None and today_stats['min_pm2_5'] is not None:
        differences['today_pm25_diff'] = today_stats['max_pm2_5'] - today_stats['min_pm2_5']
    else:
        differences['today_pm25_diff'] = 0
    
    # Weekly data differences
    if weekly_stats['max_temperature'] is not None and weekly_stats['min_temperature'] is not None:
        differences['weekly_temp_diff'] = weekly_stats['max_temperature'] - weekly_stats['min_temperature']
    else:
        differences['weekly_temp_diff'] = 0
        
    if weekly_stats['max_humidity'] is not None and weekly_stats['min_humidity'] is not None:
        differences['weekly_humidity_diff'] = weekly_stats['max_humidity'] - weekly_stats['min_humidity']
    else:
        differences['weekly_humidity_diff'] = 0
    
    # Current vs weekly average difference
    if latest_data and weekly_stats['avg_co2'] is not None:
        differences['current_vs_weekly_co2'] = latest_data.co2 - weekly_stats['avg_co2']
        differences['abs_current_vs_weekly_co2'] = abs(differences['current_vs_weekly_co2'])
    else:
        differences['current_vs_weekly_co2'] = 0
        differences['abs_current_vs_weekly_co2'] = 0
    
    # Generate recommendations
    recommendations = []
    
    if latest_data:
        # CO2 recommendations
        if latest_data.co2 > 1000:
            recommendations.append("CO₂ concentration is too high, recommend ventilation or opening windows.")
        elif latest_data.co2 > 800:
            recommendations.append("CO₂ concentration is slightly high, recommend increasing ventilation.")
            
        # Humidity recommendations
        if latest_data.humidity > 70:
            recommendations.append("Humidity is too high, recommend using a dehumidifier.")
        elif latest_data.humidity < 30:
            recommendations.append("Humidity is too low, recommend using a humidifier to maintain appropriate moisture.")
            
        # Temperature recommendations
        if latest_data.temperature > 28:
            recommendations.append("Temperature is too high, recommend turning on air conditioning or fans for cooling.")
        elif latest_data.temperature < 18:
            recommendations.append("Temperature is too low, recommend appropriate heating.")
            
        # PM2.5 recommendations
        if latest_data.pm2_5 > 35:
            recommendations.append("PM2.5 concentration is too high, recommend using an air purifier and reducing outdoor activities.")
        elif latest_data.pm2_5 > 12:
            recommendations.append("PM2.5 concentration is slightly high, recommend maintaining indoor ventilation or using an air purifier.")
            
        # PM10 recommendations
        if latest_data.pm10_0 > 150:
            recommendations.append("PM10 concentration is too high, recommend using an air purifier and reducing outdoor activities.")
        elif latest_data.pm10_0 > 50:
            recommendations.append("PM10 concentration is slightly high, recommend maintaining indoor ventilation or using an air purifier.")
    
    context = {
        'latest_data': latest_data,
        'today_stats': today_stats,
        'weekly_stats': weekly_stats,
        'monthly_stats': monthly_stats,
        'recommendations': recommendations,
        'differences': differences,  # Add the difference dictionary to the context
        'time_slots': time_slots,    # Add the time slot analysis
        'worst_slot': worst_slot,    # The worst slot
        'daily_stats': daily_stats,  # Daily statistics
        'worst_day': worst_day,      # The worst day
        'weekly_breakdown': weekly_breakdown,  # Weekly statistics
        'worst_week': worst_week,    # The worst week
    }
    
    return render(request, 'accounts/analyze.html', context)

@login_required
@require_POST # Ensure this view only accepts POST requests
def check_api_key_view(request):
    """Checks the validity of a provided DeepSeek API key."""
    try:
        data = json.loads(request.body)
        api_key = data.get('api_key')
        if not api_key:
            return JsonResponse({'status': 'error', 'message': 'API Key not provided.'}, status=400)

        # Prepare request to DeepSeek API
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": "deepseek-chat", # Use a standard model
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 1 # Minimize cost
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10) # Add timeout

            if response.status_code == 200:
                # Key is likely valid (or maybe just expired/quota exceeded but reachable)
                return JsonResponse({'status': 'success', 'message': 'Connection successful.'})
            elif response.status_code == 401:
                return JsonResponse({'status': 'invalid', 'message': 'Invalid API Key.'})
            elif response.status_code == 402:
                # Payment Required - Key might be valid but out of funds/quota
                return JsonResponse({'status': 'warning', 'message': 'Insufficient balance or quota. Check your DeepSeek account.'})
            else:
                # Other errors (429 rate limit, 5xx server errors, etc.)
                error_detail = response.text
                try: # Try to parse JSON error from DeepSeek
                    error_json = response.json()
                    error_detail = error_json.get('error', {}).get('message', response.text)
                except json.JSONDecodeError:
                    pass # Keep original text if not JSON
                return JsonResponse({
                    'status': 'error',
                    'message': f'DeepSeek API error ({response.status_code}): {error_detail[:100]}...' # Truncate long messages
                }, status=500)

        except requests.exceptions.RequestException as e:
            # Network error, timeout, etc.
            return JsonResponse({'status': 'error', 'message': f'Network error connecting to DeepSeek: {e}'}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid request format.'}, status=400)
    except Exception as e:
        # Catch unexpected errors
        return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {e}'}, status=500)
