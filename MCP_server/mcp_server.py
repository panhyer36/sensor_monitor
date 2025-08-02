import os
import sys
import django
import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional
from django.utils.dateparse import parse_datetime
from django.utils import timezone as django_timezone
from asgiref.sync import sync_to_async
from starlette.applications import Starlette
from starlette.routing import Mount

# --- Django Setup ---
# Add the project root directory (sensor_monitor) to the Python path
# Assumes mcp_server.py is in sensor_monitor/MCP_server/
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Set the DJANGO_SETTINGS_MODULE environment variable
# Replace 'config.settings' if your settings file is located elsewhere
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Configure Django
try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    print("Please ensure DJANGO_SETTINGS_MODULE is set correctly and all dependencies are installed.")
    sys.exit(1)

# --- Import Django Models (After django.setup()) ---
try:
    from sensor_api.models import SensorData
    from django.db.models import Avg, Max, Min
    # Import User and IssueReport models
    from django.contrib.auth.models import User
    from accounts.models import IssueReport, UserProfile
except ImportError as e:
    print(f"Error importing Django models: {e}")
    print("Make sure your models are defined correctly and migrations are applied.")
    sys.exit(1)

# --- MCP Setup ---
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("sensor_data_mcp")

print("MCP Server for Sensor Data configured for SSE...")

# --- Tool Implementations ---

# Define sync functions to be wrapped by sync_to_async for clarity
@sync_to_async
def _get_latest_sensor_data_sync():
    return SensorData.objects.order_by('-timestamp').first()

@sync_to_async
def _get_sensor_data_summary_sync(start_time, end_time):
    query = SensorData.objects.filter(timestamp__gte=start_time, timestamp__lte=end_time)
    summary = query.aggregate(
        avg_temp=Avg('temperature'), min_temp=Min('temperature'), max_temp=Max('temperature'),
        avg_humidity=Avg('humidity'), min_humidity=Min('humidity'), max_humidity=Max('humidity'),
        avg_co2=Avg('co2'), min_co2=Min('co2'), max_co2=Max('co2'),
        avg_pm25=Avg('pm2_5'), min_pm25=Min('pm2_5'), max_pm25=Max('pm2_5')
    )
    count = query.count()
    return summary, count

@sync_to_async
def _get_sensor_data_in_range_sync(start_time, end_time):
    query = SensorData.objects.filter(timestamp__gte=start_time, timestamp__lte=end_time).order_by('timestamp')
    return list(query.values(
        'timestamp', 'temperature', 'humidity', 'co2', 'pm1_0', 'pm2_5', 'pm10_0'
    ))

@sync_to_async
def _get_extreme_sensor_value_sync(sensor_type, start_time, end_time):
    query = SensorData.objects.filter(
        timestamp__gte=start_time, 
        timestamp__lte=end_time,
        **{f'{sensor_type}__isnull': False}
    )
    min_record = query.order_by(sensor_type).first()
    max_record = query.order_by(f'-{sensor_type}').first()
    count = query.count()
    return min_record, max_record, count

@sync_to_async
def _count_sensor_data_points_sync(start_time, end_time):
    return SensorData.objects.filter(timestamp__gte=start_time, timestamp__lte=end_time).count()

@sync_to_async
def _get_recent_sensor_data_sync(period_hours):
    end_time = django_timezone.now()
    start_time = end_time - timedelta(hours=period_hours)
    query = SensorData.objects.filter(timestamp__gte=start_time, timestamp__lte=end_time).order_by('timestamp')
    return list(query.values(
        'timestamp', 'temperature', 'humidity', 'co2', 'pm1_0', 'pm2_5', 'pm10_0'
    )), start_time, end_time

@sync_to_async
def _read_system_info_sync():
    """Synchronously reads the content of AMIsystem.txt."""
    # Construct the path relative to this script file
    script_dir = os.path.dirname(__file__)
    file_path = os.path.join(script_dir, '../chatbot/prompt/AMIsystem.txt')
    
    # Ensure the path is absolute and normalized
    absolute_file_path = os.path.abspath(file_path)
    
    print(f"Attempting to read system info from: {absolute_file_path}")
    
    if not os.path.exists(absolute_file_path):
        print(f"Error: System info file not found at {absolute_file_path}")
        raise FileNotFoundError(f"System information file not found at {absolute_file_path}")
        
    with open(absolute_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content

@sync_to_async
def _create_issue_report_sync(reporter_username: str, title: str, description: str, issue_type: Optional[str] = 'other', reporter_email: Optional[str] = None):
    """Synchronously finds the user and creates an IssueReport record."""
    try:
        reporter_user = User.objects.get(username=reporter_username)
    except User.DoesNotExist:
        raise ValueError(f"User with username '{reporter_username}' not found.")

    # Validate issue_type against choices
    valid_issue_types = [choice[0] for choice in IssueReport.ISSUE_TYPES]
    if issue_type not in valid_issue_types:
        print(f"Warning: Invalid issue_type '{issue_type}' provided. Defaulting to 'other'. Valid types: {valid_issue_types}")
        issue_type = 'other'

    # Use provided email or user's registered email
    email_to_use = reporter_email if reporter_email else reporter_user.email

    issue = IssueReport.objects.create(
        reporter=reporter_user,
        title=title,
        description=description,
        issue_type=issue_type,
        email=email_to_use
    )
    print(f"Successfully created issue report with ID: {issue.id}")
    return issue.id # Return the ID of the created issue

@sync_to_async
def _get_user_profile_sync(username: str):
    """Synchronously fetches User and UserProfile data. The Temperature units are in Celsius."""
    try:
        user = User.objects.select_related('profile').get(username=username)
        profile = user.profile
        return {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "email_notifications": profile.email_notifications,
            "thresholds": {
                "temp_min": profile.temp_min,
                "temp_max": profile.temp_max,
                "humidity_min": profile.humidity_min,
                "humidity_max": profile.humidity_max,
                "co2_max": profile.co2_max,
                "pm25_max": profile.pm25_max,
                "pm10_max": profile.pm10_max,
                "aqi_max": profile.aqi_max
            }
        }
    except User.DoesNotExist:
        raise ValueError(f"User with username '{username}' not found.")
    except UserProfile.DoesNotExist: # Should not happen with signals, but good practice
        raise ValueError(f"UserProfile for username '{username}' not found.")

@sync_to_async
def _update_user_profile_sync(username: str, updates: dict):
    """Synchronously updates User and UserProfile data. The Temperature units are in Celsius."""
    try:
        user = User.objects.select_related('profile').get(username=username)
        profile = user.profile
    except User.DoesNotExist:
        raise ValueError(f"User with username '{username}' not found.")
    except UserProfile.DoesNotExist:
        raise ValueError(f"UserProfile for username '{username}' not found.")

    updated_fields = []
    user_fields = ['first_name', 'last_name', 'email']
    profile_fields = [
        'email_notifications', 'temp_min', 'temp_max', 'humidity_min',
        'humidity_max', 'co2_max', 'pm25_max', 'pm10_max', 'aqi_max'
    ]
    boolean_fields = ['email_notifications']
    numeric_fields = [f for f in profile_fields if f not in boolean_fields]

    # Update User model fields
    user_updated = False
    for field in user_fields:
        if field in updates and getattr(user, field) != updates[field]:
            setattr(user, field, updates[field])
            updated_fields.append(field)
            user_updated = True
    if user_updated:
        user.save()

    # Update UserProfile model fields
    profile_updated = False
    for field in profile_fields:
        if field in updates:
            new_value = updates[field]
            # Type validation/conversion
            try:
                if field in boolean_fields:
                    # Basic truthiness check for boolean
                    new_value = bool(new_value) 
                elif field in numeric_fields:
                    new_value = float(new_value)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid value type provided for field '{field}'. Expected {'boolean' if field in boolean_fields else 'numeric'}.")

            if getattr(profile, field) != new_value:
                setattr(profile, field, new_value)
                updated_fields.append(f"profile.{field}") # Indicate profile field
                profile_updated = True
                
    if profile_updated:
        profile.save() # Profile is saved via signal on user save, but save explicitly if only profile fields changed

    if not updated_fields:
        return "No changes detected or applied."
        
    return f"Successfully updated fields: {', '.join(updated_fields)}"

@mcp.tool()
async def get_latest_sensor_data() -> dict[str, Any]:
    """Fetches the most recent sensor data entry from the database.
    
    Note: Timestamps are returned with timezone information in ISO 8601 format (typically UTC)."""
    print("Executing get_latest_sensor_data tool...")
    try:
        latest_data = await _get_latest_sensor_data_sync()
        if latest_data:
            return {
                "timestamp": latest_data.timestamp.isoformat(),
                "temperature": latest_data.temperature,
                "humidity": latest_data.humidity,
                "co2": latest_data.co2,
                "pm1_0": latest_data.pm1_0,
                "pm2_5": latest_data.pm2_5,
                "pm10_0": latest_data.pm10_0
            }
        else:
            return {"message": "No sensor data found."}
    except Exception as e:
        print(f"Error in get_latest_sensor_data: {e}")
        return {"error": str(e)}

@mcp.tool()
async def get_sensor_data_summary(start_time_iso: str, end_time_iso: str) -> dict[str, Any]:
    """Calculates summary statistics (avg, min, max) for sensor data within a specified time range.

    Args:
        start_time_iso: The start timestamp in ISO 8601 format with timezone (e.g., '2023-10-27T10:00:00Z' or '2023-10-27T18:00:00+08:00'). REQUIRED with timezone info.
        end_time_iso: The end timestamp in ISO 8601 format with timezone (e.g., '2023-10-27T12:00:00Z' or '2023-10-27T20:00:00+08:00'). REQUIRED with timezone info.
    
    Note: Timestamps without timezone info will be rejected. All returned timestamps include timezone info."""
    try:
        # Parse and validate start_time
        start_time = parse_datetime(start_time_iso)
        if not start_time:
            return {"error": "Invalid ISO 8601 timestamp format provided for start_time_iso."}
        if django_timezone.is_naive(start_time):
            return {"error": "start_time_iso must include timezone information (e.g., '2023-10-27T10:00:00Z' or '2023-10-27T18:00:00+08:00')."}
        
        # Parse and validate end_time
        end_time = parse_datetime(end_time_iso)
        if not end_time:
            return {"error": "Invalid ISO 8601 timestamp format provided for end_time_iso."}
        if django_timezone.is_naive(end_time):
            return {"error": "end_time_iso must include timezone information (e.g., '2023-10-27T12:00:00Z' or '2023-10-27T20:00:00+08:00')."}
        
        # Validate time range
        if start_time >= end_time:
            return {"error": "start_time must be earlier than end_time."}
        
        print(f"Executing get_sensor_data_summary from {start_time.isoformat()} to {end_time.isoformat()}...")

        summary, count = await _get_sensor_data_summary_sync(start_time, end_time)
        
        serializable_summary = {k: v if v is not None else None for k, v in summary.items()}
        
        # Calculate period in hours
        period_hours = (end_time - start_time).total_seconds() / 3600

        if count > 0:
            return {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "period_hours": round(period_hours, 2),
                "data_points": count,
                "summary": serializable_summary
            }
        else:
            return {"message": f"No sensor data found between {start_time.isoformat()} and {end_time.isoformat()}."}
    except Exception as e:
        print(f"Error in get_sensor_data_summary: {e}")
        return {"error": str(e)}

@mcp.tool()
async def get_sensor_data_in_range(start_time_iso: str, end_time_iso: str) -> dict[str, Any]:
    """Fetches all sensor data points within a specified ISO 8601 time range.

    Args:
        start_time_iso: The start timestamp in ISO 8601 format with timezone (e.g., '2023-10-27T10:00:00Z' or '2023-10-27T18:00:00+08:00'). REQUIRED with timezone info.
        end_time_iso: The end timestamp in ISO 8601 format with timezone (e.g., '2023-10-27T12:00:00Z' or '2023-10-27T20:00:00+08:00'). REQUIRED with timezone info.
    
    Note: Timestamps without timezone info will be rejected. All returned timestamps include timezone info."""
    print(f"Executing get_sensor_data_in_range from {start_time_iso} to {end_time_iso}...")
    try:
        start_time = parse_datetime(start_time_iso)
        end_time = parse_datetime(end_time_iso)

        if not start_time or not end_time:
            return {"error": "Invalid ISO 8601 timestamp format provided."}

        # Reject timezone-naive timestamps
        if django_timezone.is_naive(start_time):
            return {"error": "start_time_iso must include timezone information (e.g., '2023-10-27T10:00:00Z' or '2023-10-27T18:00:00+08:00')."}
        if django_timezone.is_naive(end_time):
            return {"error": "end_time_iso must include timezone information (e.g., '2023-10-27T12:00:00Z' or '2023-10-27T20:00:00+08:00')."}

        data_points = await _get_sensor_data_in_range_sync(start_time, end_time)
        count = len(data_points)

        # Convert datetime objects to ISO strings for JSON serialization
        for point in data_points:
            point['timestamp'] = point['timestamp'].isoformat()
            
        return {
            "start_time": start_time_iso,
            "end_time": end_time_iso,
            "data_points_count": count,
            "data": data_points
        }
    except Exception as e:
        print(f"Error in get_sensor_data_in_range: {e}")
        return {"error": str(e)}

@mcp.tool()
async def get_extreme_sensor_value(sensor_type: str, period_hours: int = 24) -> dict[str, Any]:
    """Finds the minimum and maximum value for a specific sensor type within a given period.

    Args:
        sensor_type: The sensor field name (e.g., 'temperature', 'humidity', 'co2', 'pm2_5').
        period_hours: The duration in hours to look back from current server time (default: 24).
    
    Note: The period is calculated from server's current time. All returned timestamps include timezone information."""
    print(f"Executing get_extreme_sensor_value for '{sensor_type}' in the last {period_hours} hours...")
    valid_sensor_types = [
        'temperature', 'humidity', 'co2', 'pm1_0', 'pm2_5', 'pm10_0'
    ]
    if sensor_type not in valid_sensor_types:
        return {"error": f"Invalid sensor_type '{sensor_type}'. Valid types are: {valid_sensor_types}"}

    try:
        end_time = django_timezone.now()
        start_time = end_time - timedelta(hours=period_hours)

        min_record, max_record, count = await _get_extreme_sensor_value_sync(sensor_type, start_time, end_time)

        result = {
            "sensor_type": sensor_type,
            "period_hours": period_hours,
            "data_points_considered": count,
            "minimum": None,
            "maximum": None
        }

        if min_record:
            result["minimum"] = {
                "value": getattr(min_record, sensor_type),
                "timestamp": min_record.timestamp.isoformat()
            }
        if max_record:
            result["maximum"] = {
                "value": getattr(max_record, sensor_type),
                "timestamp": max_record.timestamp.isoformat()
            }
            
        if not min_record and not max_record:
             result["message"] = f"No valid data for '{sensor_type}' found in the last {period_hours} hours."

        return result

    except Exception as e:
        print(f"Error in get_extreme_sensor_value: {e}")
        return {"error": str(e)}
        
@mcp.tool()
async def get_recent_sensor_data(period_hours: int = 1) -> dict[str, Any]:
    """Fetches all sensor data points within the specified recent number of hours.

    Args:
        period_hours: The number of hours to look back from the current server time (default: 1).
    
    Note: The period is calculated from server's current time. All returned timestamps include timezone information."""
    print(f"Executing get_recent_sensor_data for the last {period_hours} hours...")
    try:
        if period_hours <= 0:
            return {"error": "period_hours must be a positive integer."}
            
        data_points, start_time, end_time = await _get_recent_sensor_data_sync(period_hours)
        count = len(data_points)

        # Convert datetime objects to ISO strings for JSON serialization
        for point in data_points:
            point['timestamp'] = point['timestamp'].isoformat()
            
        return {
            "period_hours": period_hours,
            "calculated_start_time": start_time.isoformat(),
            "calculated_end_time": end_time.isoformat(),
            "data_points_count": count,
            "data": data_points
        }
    except Exception as e:
        print(f"Error in get_recent_sensor_data: {e}")
        return {"error": str(e)}

@mcp.tool()
async def count_sensor_data_points(period_hours: int = 24) -> dict[str, Any]:
    """Counts the number of sensor data points recorded within a specified period.
    
    Args:
        period_hours: The duration in hours to look back from current server time (default: 24).
    
    Note: The period is calculated from server's current time. All returned timestamps include timezone information."""
    print(f"Executing count_sensor_data_points for the last {period_hours} hours...")
    try:
        end_time = django_timezone.now()
        start_time = end_time - timedelta(hours=period_hours)
        
        count = await _count_sensor_data_points_sync(start_time, end_time)
        
        return {
            "period_hours": period_hours,
            "data_points_count": count,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    except Exception as e:
        print(f"Error in count_sensor_data_points: {e}")
        return {"error": str(e)}

@mcp.tool()
async def convert_temperature(value: float, from_unit: str) -> dict[str, Any]:
    """Converts a temperature value between Celsius and Fahrenheit.

    Args:
        value: The temperature value to convert.
        from_unit: The unit of the input value ('C' for Celsius, 'F' for Fahrenheit).

    Returns:
        A dictionary containing the original value and unit, and the converted value and unit, or an error message.
    """
    print(f"Executing convert_temperature for {value} degrees {from_unit}...")
    from_unit = from_unit.upper()
    
    if from_unit == 'C':
        converted_value = (value * 9/5) + 32
        to_unit = 'F'
    elif from_unit == 'F':
        converted_value = (value - 32) * 5/9
        to_unit = 'C'
    else:
        return {"error": "Invalid 'from_unit'. Please specify 'C' for Celsius or 'F' for Fahrenheit."}
        
    return {
        "original_value": value,
        "original_unit": from_unit,
        "converted_value": round(converted_value, 2), # Round to 2 decimal places
        "converted_unit": to_unit
    }

@mcp.tool()
async def get_system_info() -> dict[str, Any]:
    """Use this tool if the user asks the questions about the system's purpose, features, or how it works."""
    print("Executing read_system_info tool...")
    try:
        system_info_content = await _read_system_info_sync()
        return {"system_info": system_info_content}
    except FileNotFoundError as e:
        print(f"Error in read_system_info: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Unexpected error in read_system_info: {e}")
        return {"error": f"An unexpected error occurred while reading system info: {str(e)}"}

@mcp.tool()
async def report_issue(reporter_username: str, title: str, description: str, issue_type: Optional[str] = None, reporter_email: Optional[str] = None) -> dict[str, Any]:
    """Reports an issue or provides feedback about the system. Requires the username of the reporter.

    Args:
        reporter_username: The username of the user reporting the issue (REQUIRED).
        title: A brief title for the issue (REQUIRED).
        description: A detailed description of the issue or feedback (REQUIRED).
        issue_type: The type of issue. Valid types are: 'bug', 'feature', 'sensor', 'data', 'other'. Defaults to 'other' if invalid or not provided.
        reporter_email: Optional email address for updates, overrides the user's registered email if provided.

    Returns:
        A dictionary confirming the issue creation with its ID, or an error message.
    """
    print(f"Executing report_issue for user '{reporter_username}'...")
    if not reporter_username or not title or not description:
         return {"error": "Missing required arguments: reporter_username, title, and description are required."}
         
    # Set default issue_type if None is passed explicitly
    if issue_type is None:
        issue_type = 'other'
        
    try:
        issue_id = await _create_issue_report_sync(reporter_username, title, description, issue_type, reporter_email)
        return {
            "success": True,
            "message": f"Issue reported successfully by {reporter_username}.",
            "issue_id": issue_id
        }
    except ValueError as e: # Catch specific user not found error
        print(f"Error in report_issue: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Unexpected error in report_issue: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        return {"error": f"An unexpected error occurred while reporting the issue: {str(e)}"}

@mcp.tool()
async def get_user_profile(username: str) -> dict[str, Any]:
    """Fetches the profile information for a given user, including name, email, and notification thresholds.

    Args:
        username: The username of the user whose profile to fetch (REQUIRED).

    Returns:
        A dictionary containing the user's profile information, or an error message.
    """
    print(f"Executing get_user_profile for user '{username}'...")
    if not username:
        return {"error": "Missing required argument: username."}
        
    try:
        profile_data = await _get_user_profile_sync(username)
        return {"success": True, "profile": profile_data}
    except ValueError as e:
        print(f"Error in get_user_profile: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Unexpected error in get_user_profile: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def update_user_profile(username: str, 
                                first_name: Optional[str] = None, 
                                last_name: Optional[str] = None, 
                                email: Optional[str] = None, 
                                email_notifications: Optional[bool] = None,
                                temp_min: Optional[float] = None,
                                temp_max: Optional[float] = None,
                                humidity_min: Optional[float] = None,
                                humidity_max: Optional[float] = None,
                                co2_max: Optional[float] = None,
                                pm25_max: Optional[float] = None,
                                pm10_max: Optional[float] = None,
                                aqi_max: Optional[float] = None
                               ) -> dict[str, Any]:
    """Updates the profile information or notification thresholds for a given user. Only provided fields will be updated.

    Args:
        username: The username of the user whose profile to update (REQUIRED).
        first_name: The user's first name.
        last_name: The user's last name.
        email: The user's email address.
        email_notifications: Set to true to enable email notifications, false to disable.
        temp_min: Minimum temperature threshold (°C).
        temp_max: Maximum temperature threshold (°C).
        humidity_min: Minimum humidity threshold (%).
        humidity_max: Maximum humidity threshold (%).
        co2_max: Maximum CO2 threshold (ppm).
        pm25_max: Maximum PM2.5 threshold (μg/m³).
        pm10_max: Maximum PM10 threshold (μg/m³).
        aqi_max: Maximum AQI threshold.

    Returns:
        A dictionary confirming the update or an error message.
    """
    print(f"Executing update_user_profile for user '{username}'...")
    if not username:
        return {"error": "Missing required argument: username."}

    # Collect updates into a dictionary, excluding None values
    updates = {
        k: v for k, v in {
            'first_name': first_name, 'last_name': last_name, 'email': email,
            'email_notifications': email_notifications, 'temp_min': temp_min, 'temp_max': temp_max,
            'humidity_min': humidity_min, 'humidity_max': humidity_max, 'co2_max': co2_max,
            'pm25_max': pm25_max, 'pm10_max': pm10_max, 'aqi_max': aqi_max
        }.items() if v is not None
    }

    if not updates:
        return {"success": True, "message": "No update parameters provided."}

    try:
        update_message = await _update_user_profile_sync(username, updates)
        return {"success": True, "message": update_message}
    except ValueError as e:
        print(f"Error in update_user_profile: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Unexpected error in update_user_profile: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"An unexpected error occurred: {str(e)}"}

# --- Removed ASGI App Mount ---
# app = Starlette(
#     routes=[
#         Mount('/', app=mcp.sse_app()),
#     ]
# )

# --- Restore stdio run block ---
if __name__ == "__main__":
    print("Attempting to run MCP server (stdio mode)...")
    try:
        # Running sync ORM calls via sync_to_async within tools handles async context.
        mcp.run(transport='stdio')
        print("MCP Server finished.")
    except Exception as e:
        print(f"Error running MCP server: {e}")
        sys.exit(1) 