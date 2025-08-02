from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import json
import openai
from sensor_api.models import SensorData
from django.db.models import Avg, Max, Min
from .models import ChatbotQA
import re
from accounts.models import UserProfile
import requests # Import requests
from functools import lru_cache # For simple caching
from django.utils import timezone
import pytz
from datetime import datetime

# Simple FAQ dictionary
FAQ = {
    "what is this system": "This is an AMI Sensor Monitoring System that helps track and manage sensor data.",
    "how to use": "You can view sensor data on the dashboard, manage sensors through the admin panel, and analyze readings using our visualization tools.",
    "who created": "This system was used for the AMI team, and I'm an AI assistant.",
    "contact support": "For support, please press the 'Report Issue' button on the dashboard.",
    "features": "Our system features real-time monitoring, data visualization, alerts, and detailed reporting.",
    "how to add data": "To add new sensor data, you can use one of these methods:\n1. Use our monitoring system to automatically collect and upload data\n2. Use the API endpoint at '/api/sensor/' with a POST request\n3. Import data from CSV/Excel files via the Admin Panel\n4. Connect compatible sensors directly to the system for real-time data collection",
    "data security": "We store data in a sqlite database..",
    "sensor types": "Our system supports various sensors including CO2, humidity, temperature, and particulate matter (PM1.0, PM2.5, PM10.0) sensors.",
    "export data": "You can export sensor data in CSV or JSON format from the Sensor Monitoring Dashboard by clicking the Export button.",
    "system requirements": "This system works best with modern browsers like Chrome, Firefox, or Edge. No special hardware is required for access.",
    "mobile access": "Yes, the system is fully responsive and can be accessed from mobile devices.",
    "help": "You can ask about system features, sensor data, how to use the system, or contact information. Try asking 'What can I ask?' for more suggestions.",
    "aqi": "AQI (Air Quality Index) is a measure of air quality. It ranges from 0 to 500, with higher values indicating worse air quality. The index is calculated based on concentrations of air pollutants like PM2.5, PM10, ozone, and others."
}

# Questions that can be asked
QUESTION_SUGGESTIONS = [
    "What is this system?",
    "How do I use this system?",
    "What features does the system have?",
    "How can I add a new data?",
    "What types of sensors are supported?",
    "Can I export the data?",
    "Who created this system?",
    "How do I contact support?",
    "What are the system requirements?",
    "Can I access from mobile?",
    "What's the current temperature?",
    "Show me the latest CO2 readings",
    "Is the air quality good?",
    "What is the current AQI?",
    "What are the average humidity levels?"
    "What is the weather?"
]

# Sensor data interpretation thresholds
SENSOR_THRESHOLDS = {
    'co2': {
        'good': 800,
        'moderate': 1500,
        'poor': 2000,
        'unit': 'ppm',
        'explanation': {
            'good': 'CO2 levels are good. The air quality is excellent.',
            'moderate': 'CO2 levels are moderate. Consider increasing ventilation.',
            'poor': 'CO2 levels are high. Ventilation is needed.',
            'very_poor': 'CO2 levels are very high. Immediate ventilation is required.'
        }
    },
    'temperature': {
        'cold': 18,
        'comfortable': 25,
        'hot': 30,
        'unit': '°C',
        'explanation': {
            'cold': 'The temperature is low.',
            'comfortable': 'The temperature is in a comfortable range.',
            'hot': 'The temperature is high.',
            'very_hot': 'The temperature is very high.'
        }
    },
    'humidity': {
        'dry': 30,
        'comfortable': 60,
        'humid': 70,
        'unit': '%',
        'explanation': {
            'dry': 'The humidity is low, which might cause discomfort.',
            'comfortable': 'The humidity level is comfortable.',
            'humid': 'The humidity is high.',
            'very_humid': 'The humidity is very high, which might cause discomfort.'
        }
    },
    'pm1_0': {
        'good': 10,
        'moderate': 25,
        'unhealthy': 45,
        'unit': 'μg/m³',
        'explanation': {
            'good': 'PM1.0 levels are good. The air quality is excellent.',
            'moderate': 'PM1.0 levels are moderate. Air quality is acceptable.',
            'unhealthy': 'PM1.0 levels are unhealthy for sensitive groups.',
            'very_unhealthy': 'PM1.0 levels are unhealthy. Consider using an air purifier.'
        }
    },
    'pm2_5': {
        'good': 12,
        'moderate': 35.4,
        'unhealthy': 55.4,
        'unit': 'μg/m³',
        'explanation': {
            'good': 'PM2.5 levels are good. The air quality is excellent.',
            'moderate': 'PM2.5 levels are moderate. Air quality is acceptable.',
            'unhealthy': 'PM2.5 levels are unhealthy for sensitive groups.',
            'very_unhealthy': 'PM2.5 levels are unhealthy. Consider using an air purifier.'
        }
    },
    'pm10_0': {
        'good': 54,
        'moderate': 154,
        'unhealthy': 254,
        'unit': 'μg/m³',
        'explanation': {
            'good': 'PM10 levels are good. The air quality is excellent.',
            'moderate': 'PM10 levels are moderate. Air quality is acceptable.',
            'unhealthy': 'PM10 levels are unhealthy for sensitive groups.',
            'very_unhealthy': 'PM10 levels are unhealthy. Consider using an air purifier.'
        }
    },
    'aqi': {
        'good': 50,
        'moderate': 100,
        'unhealthy_for_sensitive': 150,
        'unhealthy': 200,
        'very_unhealthy': 300,
        'hazardous': 500,
        'unit': '',
        'explanation': {
            'good': 'AQI is good (0-50). Air quality is satisfactory, and air pollution poses little or no risk.',
            'moderate': 'AQI is moderate (51-100). Air quality is acceptable, but there may be a risk for some people, particularly those who are unusually sensitive to air pollution.',
            'unhealthy_for_sensitive': 'AQI is unhealthy for sensitive groups (101-150). Members of sensitive groups may experience health effects, but the general public is less likely to be affected.',
            'unhealthy': 'AQI is unhealthy (151-200). Everyone may begin to experience health effects; members of sensitive groups may experience more serious health effects.',
            'very_unhealthy': 'AQI is very unhealthy (201-300). Health alert: everyone may experience more serious health effects.',
            'hazardous': 'AQI is hazardous (301-500). Health warning of emergency conditions: everyone is more likely to be affected.'
        }
    }
}

# --- mcpo OpenAPI Schema Handling ---
MCPO_OPENAPI_URL = "http://localhost:8002/openapi.json"
MCPO_BASE_URL = "http://localhost:8002"

@lru_cache(maxsize=1) # Simple cache for the OpenAPI schema
def get_mcpo_openapi_schema():
    """Fetches and caches the OpenAPI schema from the mcpo proxy."""
    try:
        response = requests.get(MCPO_OPENAPI_URL, timeout=5)
        response.raise_for_status()
        print("Successfully fetched mcpo OpenAPI schema.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Could not fetch mcpo OpenAPI schema from {MCPO_OPENAPI_URL}: {e}")
        return None

def parse_openapi_schema_for_tools(schema):
    """Parses the mcpo OpenAPI schema and converts it to OpenAI tool format."""
    if not schema or 'paths' not in schema:
        return []

    openai_tools = []
    schemas_component = schema.get('components', {}).get('schemas', {})

    for path, path_item in schema['paths'].items():
        if path.startswith('/') and 'post' in path_item: # Assuming tools are POST requests at root path
            tool_name = path[1:] # Remove leading slash
            operation = path_item['post']
            
            parameters = {"type": "object", "properties": {}, "required": []}
            
            # Extract parameters from requestBody schema reference
            request_body = operation.get('requestBody')
            if request_body:
                content = request_body.get('content', {}).get('application/json', {})
                schema_ref = content.get('schema', {}).get('$ref')
                if schema_ref and schema_ref.startswith('#/components/schemas/'):
                    schema_name = schema_ref.split('/')[-1]
                    param_schema = schemas_component.get(schema_name)
                    if param_schema and 'properties' in param_schema:
                        parameters['properties'] = param_schema['properties']
                        # Handle defaults and descriptions if available within properties
                        for param_name, prop_details in parameters['properties'].items():
                            # OpenAI schema doesn't have a top-level default, remove it?
                            # Or maybe keep it in description?
                            if 'default' in prop_details:
                                prop_details['description'] = prop_details.get('description', '') + f" (default: {prop_details['default']})"
                                # del prop_details['default'] # OpenAI spec doesn't define default here
                            # Remove title if description exists, or use title as description
                            if 'description' not in prop_details and 'title' in prop_details:
                                 prop_details['description'] = prop_details['title']
                            if 'title' in prop_details:
                                 del prop_details['title']
                                 
                        parameters['required'] = param_schema.get('required', [])

            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": operation.get('description') or operation.get('summary', ''),
                    "parameters": parameters
                }
            })
            
    # print(f"[DEBUG] Parsed OpenAI tools: {json.dumps(openai_tools, indent=2)}") 
    return openai_tools

def call_mcpo_tool(tool_name: str, arguments: dict):
    """Calls the specified tool via the mcpo proxy."""
    tool_url = f"{MCPO_BASE_URL}/{tool_name}"
    try:
        response = requests.post(tool_url, json=arguments, timeout=10)
        response.raise_for_status()
        # Return the JSON response, assuming it's the tool result
        # mcpo might wrap it, adjust if needed
        return response.json() 
    except requests.exceptions.RequestException as e:
        print(f"ERROR calling mcpo tool '{tool_name}' at {tool_url}: {e}")
        # Return an error structure that can be serialized
        return {"mcp_tool_error": f"Failed to call tool '{tool_name}': {str(e)}"}
    except json.JSONDecodeError:
        print(f"ERROR decoding JSON response from mcpo tool '{tool_name}' at {tool_url}")
        return {"mcp_tool_error": f"Invalid JSON response from tool '{tool_name}'."}

@login_required
def chatbot_view(request):
    """Display the chatbot interface"""
    return render(request, 'chatbot/chatbot.html', {'suggestions': QUESTION_SUGGESTIONS})

def get_sensor_data_interpretation(sensor_type, value):
    """Interpret sensor data"""
    if sensor_type not in SENSOR_THRESHOLDS:
        return f"No interpretation available for {sensor_type}"
        
    thresholds = SENSOR_THRESHOLDS[sensor_type]
    unit = thresholds['unit']
    
    if sensor_type == 'co2':
        if value < thresholds['good']:
            return f"CO2: {value}{unit}. {thresholds['explanation']['good']}"
        elif value < thresholds['moderate']:
            return f"CO2: {value}{unit}. {thresholds['explanation']['moderate']}"
        elif value < thresholds['poor']:
            return f"CO2: {value}{unit}. {thresholds['explanation']['poor']}"
        else:
            return f"CO2: {value}{unit}. {thresholds['explanation']['very_poor']}"
    
    elif sensor_type == 'temperature':
        if value < thresholds['cold']:
            return f"Temperature: {value}{unit}. {thresholds['explanation']['cold']}"
        elif value < thresholds['comfortable']:
            return f"Temperature: {value}{unit}. {thresholds['explanation']['comfortable']}"
        elif value < thresholds['hot']:
            return f"Temperature: {value}{unit}. {thresholds['explanation']['hot']}"
        else:
            return f"Temperature: {value}{unit}. {thresholds['explanation']['very_hot']}"
    
    elif sensor_type == 'humidity':
        if value < thresholds['dry']:
            return f"Humidity: {value}{unit}. {thresholds['explanation']['dry']}"
        elif value < thresholds['comfortable']:
            return f"Humidity: {value}{unit}. {thresholds['explanation']['comfortable']}"
        elif value < thresholds['humid']:
            return f"Humidity: {value}{unit}. {thresholds['explanation']['humid']}"
        else:
            return f"Humidity: {value}{unit}. {thresholds['explanation']['very_humid']}"
    
    elif sensor_type in ['pm1_0', 'pm2_5', 'pm10_0']:
        name = "PM1.0" if sensor_type == 'pm1_0' else ("PM2.5" if sensor_type == 'pm2_5' else "PM10")
        if value < thresholds['good']:
            return f"{name}: {value}{unit}. {thresholds['explanation']['good']}"
        elif value < thresholds['moderate']:
            return f"{name}: {value}{unit}. {thresholds['explanation']['moderate']}"
        elif value < thresholds['unhealthy']:
            return f"{name}: {value}{unit}. {thresholds['explanation']['unhealthy']}"
        else:
            return f"{name}: {value}{unit}. {thresholds['explanation']['very_unhealthy']}"
    
    return f"{sensor_type}: {value}{unit}"

def calculate_aqi_from_pm(pm25_value, pm10_value):
    """Calculate AQI value from PM2.5 and PM10"""
    # PM2.5 AQI calculation
    pm25_aqi = calculate_pm25_aqi(pm25_value)
    
    # PM10 AQI calculation
    pm10_aqi = calculate_pm10_aqi(pm10_value)
    
    # Take the maximum of the two as AQI
    aqi = max(pm25_aqi, pm10_aqi)
    
    return round(aqi)

def calculate_pm25_aqi(pm25):
    """Calculate PM2.5 AQI value"""
    # PM2.5 concentration to AQI mapping
    pm25_breakpoints = [
        (0, 12, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500)
    ]
    
    for low_conc, high_conc, low_aqi, high_aqi in pm25_breakpoints:
        if low_conc <= pm25 <= high_conc:
            # Linear interpolation to calculate AQI
            aqi = ((high_aqi - low_aqi) / (high_conc - low_conc)) * (pm25 - low_conc) + low_aqi
            return aqi
    
    # If out of range
    if pm25 > 500.4:
        return 500
    return 0

def calculate_pm10_aqi(pm10):
    """Calculate PM10 AQI value"""
    # PM10 concentration to AQI mapping
    pm10_breakpoints = [
        (0, 54, 0, 50),
        (55, 154, 51, 100),
        (155, 254, 101, 150),
        (255, 354, 151, 200),
        (355, 424, 201, 300),
        (425, 504, 301, 400),
        (505, 604, 401, 500)
    ]
    
    for low_conc, high_conc, low_aqi, high_aqi in pm10_breakpoints:
        if low_conc <= pm10 <= high_conc:
            # Linear interpolation to calculate AQI
            aqi = ((high_aqi - low_aqi) / (high_conc - low_conc)) * (pm10 - low_conc) + low_aqi
            return aqi
    
    # If out of range
    if pm10 > 604:
        return 500
    return 0

def get_aqi_level(aqi):
    """Get AQI level description"""
    if aqi <= 50:
        return 'good'
    elif aqi <= 100:
        return 'moderate'
    elif aqi <= 150:
        return 'unhealthy_for_sensitive'
    elif aqi <= 200:
        return 'unhealthy'
    elif aqi <= 300:
        return 'very_unhealthy'
    else:
        return 'hazardous'

def get_sensor_info(query):
    """process the sensor data related queries"""
    try:
        # clean the query
        cleaned_query = clean_text(query)
        
        # get the latest sensor data
        latest_data = SensorData.objects.order_by('-timestamp').first()
        
        # calculate the average values
        avg_data = SensorData.objects.aggregate(
            avg_temp=Avg('temperature'),
            avg_humidity=Avg('humidity'),
            avg_co2=Avg('co2'),
            avg_pm1=Avg('pm1_0'),
            avg_pm25=Avg('pm2_5'),
            avg_pm10=Avg('pm10_0')
        )
        
        # query about AQI
        if any(word in cleaned_query for word in ['aqi', 'air quality index', 'air index']):
            if not latest_data:
                return "No air quality data available."
            
            # calculate the AQI
            aqi_value = calculate_aqi_from_pm(latest_data.pm2_5, latest_data.pm10_0)
            aqi_level = get_aqi_level(aqi_value)
            
            result = f"Current AQI: {aqi_value}\n"
            result += SENSOR_THRESHOLDS['aqi']['explanation'][aqi_level]
            
            # add the main contributor
            if calculate_pm25_aqi(latest_data.pm2_5) > calculate_pm10_aqi(latest_data.pm10_0):
                result += f"\n\nPM2.5 ({latest_data.pm2_5:.1f}μg/m³) is the main contributor to current AQI."
            else:
                result += f"\n\nPM10 ({latest_data.pm10_0:.1f}μg/m³) is the main contributor to current AQI."
                
            return result
        
        # query about temperature
        elif any(word in cleaned_query for word in ['temperature', 'hot', 'cold']):
            if not latest_data:
                return "No temperature data available."
            return get_sensor_data_interpretation('temperature', latest_data.temperature)
        
        # query about humidity
        elif any(word in cleaned_query for word in ['humidity', 'humid', 'dry']):
            if not latest_data:
                return "No humidity data available."
            return get_sensor_data_interpretation('humidity', latest_data.humidity)
        
        # query about CO2
        elif any(word in cleaned_query for word in ['co2', 'carbon dioxide']):
            if not latest_data:
                return "No CO2 data available."
            return get_sensor_data_interpretation('co2', latest_data.co2)
        
        # process the query about PM10 - should be processed first to avoid confusion with PM1
        elif ("pm10" in cleaned_query or "pm100" in cleaned_query) and not any(term in cleaned_query for term in ["pm1 ", "pm2"]):
            if not latest_data:
                return "No PM10 data available."
            return get_sensor_data_interpretation('pm10_0', latest_data.pm10_0)
        
        # query about PM1.0
        elif any(word in cleaned_query for word in ['pm1', 'ultrafine']):
            # ensure it's not PM10
            if not "pm10" in cleaned_query and not "pm100" in cleaned_query:
                if not latest_data:
                    return "No PM1.0 data available."
                return get_sensor_data_interpretation('pm1_0', latest_data.pm1_0)
        
        # query about PM2.5
        elif any(word in cleaned_query for word in ['pm25', 'pm2', 'fine particles']):
            if not latest_data:
                return "No PM2.5 data available."
            return get_sensor_data_interpretation('pm2_5', latest_data.pm2_5)
        
        # query about air quality
        elif any(word in cleaned_query for word in ['air quality', 'air', 'quality']):
            if not latest_data:
                return "No air quality data available."
            
            # 计算AQI
            aqi_value = calculate_aqi_from_pm(latest_data.pm2_5, latest_data.pm10_0)
            aqi_level = get_aqi_level(aqi_value)
            
            result = f"Air Quality Status:\n"
            result += f"AQI: {aqi_value} - {SENSOR_THRESHOLDS['aqi']['explanation'][aqi_level]}\n"
            result += get_sensor_data_interpretation('pm2_5', latest_data.pm2_5) + "\n"
            result += get_sensor_data_interpretation('co2', latest_data.co2)
            
            return result
        
        # query about average values
        elif 'average' in cleaned_query:
            if not avg_data['avg_temp']:
                return "No average data available."
            
            result = "Average Sensor Readings:\n"
            if 'temperature' in cleaned_query or 'all' in cleaned_query:
                result += f"Temperature: {avg_data['avg_temp']:.1f}°C\n"
            if 'humidity' in cleaned_query or 'all' in cleaned_query:
                result += f"Humidity: {avg_data['avg_humidity']:.1f}%\n"
            if 'co2' in cleaned_query or 'all' in cleaned_query:
                result += f"CO2: {avg_data['avg_co2']:.1f}ppm\n"
            if 'pm1' in cleaned_query and not 'pm10' in cleaned_query or 'all' in cleaned_query:
                result += f"PM1.0: {avg_data['avg_pm1']:.1f}μg/m³\n"
            if 'pm25' in cleaned_query or 'pm2' in cleaned_query or 'all' in cleaned_query:
                result += f"PM2.5: {avg_data['avg_pm25']:.1f}μg/m³\n"
            if 'pm10' in cleaned_query or 'all' in cleaned_query:
                result += f"PM10: {avg_data['avg_pm10']:.1f}μg/m³"
            
            return result
            
        # query about all the latest data
        elif any(word in cleaned_query for word in ['latest', 'current', 'now']) or (
                'data' in cleaned_query and not any(word in cleaned_query for word in ['analyze', 'analyse', 'average', 'export', 'add', 'import', 'delete'])):
            if not latest_data:
                return "No sensor data available."
            
            # calculate the AQI
            aqi_value = calculate_aqi_from_pm(latest_data.pm2_5, latest_data.pm10_0)
            
            result = "Latest Sensor Readings:\n"
            result += f"Time: {latest_data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            result += f"Temperature: {latest_data.temperature:.1f}°C\n"
            result += f"Humidity: {latest_data.humidity:.1f}%\n"
            result += f"CO2: {latest_data.co2:.1f}ppm\n"
            result += f"PM1.0: {latest_data.pm1_0:.1f}μg/m³\n"
            result += f"PM2.5: {latest_data.pm2_5:.1f}μg/m³\n"
            result += f"PM10: {latest_data.pm10_0:.1f}μg/m³\n"
            result += f"AQI: {aqi_value} ({get_aqi_level(aqi_value).replace('_', ' ').title()})"
            
            return result
        
        return None  # not sensor related queries
        
    except Exception as e:
        return f"Error analyzing sensor data: {str(e)}"

def clean_text(text):
    """clean the text, remove the punctuation and special characters, keep the letters, numbers, spaces and decimal points"""
    # remove the punctuation and special characters, except decimal points
    # keep the letters, numbers, spaces and decimal points
    cleaned_text = re.sub(r'[^\w\s\.]', '', text)
    # convert to lower case
    cleaned_text = cleaned_text.lower().strip()
    return cleaned_text

@login_required
@require_POST
def chatbot_api(request):
    """Process the chatbot API request"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query', '').lower().strip()
            cleaned_query = clean_text(query)  # use the cleaned query

            # directly match the questions in the question suggestion list
            for suggestion in QUESTION_SUGGESTIONS:
                cleaned_suggestion = clean_text(suggestion)
                if cleaned_query == cleaned_suggestion:
                    # find the corresponding FAQ keyword
                    if "contact support" in suggestion.lower():
                        return JsonResponse({'response': FAQ["contact support"], 'status': 'success'})
                    elif "what is this system" in suggestion.lower():
                        return JsonResponse({'response': FAQ["what is this system"], 'status': 'success'})
                    elif "how do i use" in suggestion.lower():
                        return JsonResponse({'response': FAQ["how to use"], 'status': 'success'})
                    elif "features" in suggestion.lower():
                        return JsonResponse({'response': FAQ["features"], 'status': 'success'})
                    elif "add a new data" in suggestion.lower():
                        return JsonResponse({'response': FAQ["how to add data"], 'status': 'success'})
                    elif "add a new sensor" in suggestion.lower():
                        return JsonResponse({'response': FAQ["how to add sensor"], 'status': 'success'})
                    elif "who created" in suggestion.lower():
                        return JsonResponse({'response': FAQ["who created"], 'status': 'success'})
                    elif "sensors are supported" in suggestion.lower():
                        return JsonResponse({'response': FAQ["sensor types"], 'status': 'success'})
                    elif "export" in suggestion.lower():
                        return JsonResponse({'response': FAQ["export data"], 'status': 'success'})
                    elif "system requirements" in suggestion.lower():
                        return JsonResponse({'response': FAQ["system requirements"], 'status': 'success'})
                    elif "mobile" in suggestion.lower():
                        return JsonResponse({'response': FAQ["mobile access"], 'status': 'success'})
            
            # specific keyword matching
            if "contact" in cleaned_query and any(word in cleaned_query for word in ["support", "help", "service"]):
                return JsonResponse({'response': FAQ["contact support"], 'status': 'success'})
            elif "email" in cleaned_query or "phone" in cleaned_query or "call" in cleaned_query:
                return JsonResponse({'response': FAQ["contact support"], 'status': 'success'})
            elif "add" in cleaned_query and any(word in cleaned_query for word in ["data", "information", "reading", "measurement"]):
                return JsonResponse({'response': FAQ["how to add data"], 'status': 'success'})
            elif "export" in cleaned_query or "export data" in cleaned_query or "download data" in cleaned_query:
                return JsonResponse({'response': FAQ["export data"], 'status': 'success'})
            elif "what is aqi" in cleaned_query or "aqi meaning" in cleaned_query or "air quality index" in cleaned_query:
                return JsonResponse({'response': FAQ["aqi"], 'status': 'success'})
            elif "pm10" in cleaned_query or "pm100" in cleaned_query:
                if not any(term in cleaned_query for term in ["pm1", "pm2"]):
                    sensor_response = get_sensor_info(query)
                    if sensor_response:
                        return JsonResponse({'response': sensor_response, 'status': 'success'})
            elif "pm1" in cleaned_query:
                sensor_response = get_sensor_info(query)
                if sensor_response:
                    return JsonResponse({'response': sensor_response, 'status': 'success'})
            elif "pm25" in cleaned_query or "pm2" in cleaned_query:
                sensor_response = get_sensor_info(query)
                if sensor_response:
                    return JsonResponse({'response': sensor_response, 'status': 'success'})
            
            # Process help requests
            if cleaned_query in ['help', 'what can i ask', 'what can you do']:
                response = "You can ask me about:\n"
                response += "- System information and features\n"
                response += "- How to use the system\n"
                response += "- Sensor data (current readings, averages, interpretations)\n"
                response += "- Contact and support information\n\n"
                response += "Try questions like:\n"
                response += "\n".join(QUESTION_SUGGESTIONS[:5]) + "\n\n"
                response += "For more suggestions, ask 'Show more questions'"
                return JsonResponse({'response': response, 'status': 'success'})
            
            # Display more question suggestions
            if any(phrase in cleaned_query for phrase in ['more questions', 'more suggestions', 'what else', 'show more']):
                response = "Here are more questions you can ask:\n\n"
                response += "\n".join(QUESTION_SUGGESTIONS)
                return JsonResponse({'response': response, 'status': 'success'})
            
            # Process queries related to sensor data
            sensor_response = get_sensor_info(query)
            if sensor_response:
                return JsonResponse({'response': sensor_response, 'status': 'success'})
            
            # 使用改进的匹配逻辑查找数据库中的问答对
            db_match = ChatbotQA.find_best_match(query)
            if db_match:
                return JsonResponse({'response': db_match.answer, 'status': 'success'})
                
            # 如果没有找到匹配的数据库问答对，尝试使用内置FAQ
            best_match = None
            best_match_score = 0
            
            for question in FAQ:
                cleaned_faq_question = clean_text(question)
                # improved keyword matching
                query_words = set(cleaned_query.split())
                question_words = set(cleaned_faq_question.split())
                # calculate the size of the intersection of the two sets
                common_words = query_words.intersection(question_words)
                score = len(common_words) / len(question_words) if question_words else 0
                
                if score > best_match_score:
                    best_match = question
                    best_match_score = score
            
            # If a match is found, return the answer
            if best_match and best_match_score > 0.3:  # Decrease threshold to increase matching probability
                response = FAQ[best_match]
            else:
                response = "I'm sorry, I don't have an answer to that question. Please try asking something about the system features, usage, sensor data, or contact information. Type 'help' to see what you can ask."
            
            return JsonResponse({
                'response': response,
                'status': 'success'
            })
        except json.JSONDecodeError:
            return JsonResponse({
                'response': 'Invalid request format',
                'status': 'error'
            }, status=400)
    
    return JsonResponse({
        'response': 'Method not allowed',
        'status': 'error'
    }, status=405)

# --- DeepSeek Chat Views ---

@login_required
def deepseek_chat_view(request):
    """Render the chat page for DeepSeek integration."""
    # We can pass initial context if needed
    return render(request, 'chatbot/deepseek_chat.html')

@login_required
@require_POST
def deepseek_api_view(request):
    """Handle AJAX requests for DeepSeek chat, allows model to call MCP tools via mcpo."""
    MAX_HISTORY_MESSAGES = 10 # Define the constant here
    try:
        # 1. Get User Input & History
        data = json.loads(request.body)
        user_message = data.get('message')
        history = data.get('history', []) # Get history from request
        current_username = request.user.username # Get the current logged-in username

        if not user_message:
            return JsonResponse({'status': 'error', 'message': 'No message provided.'}, status=400)
        
        # Validate and sanitize history (basic validation)
        validated_history = []
        if isinstance(history, list):
            for msg in history:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg and msg['role'] in ['user', 'assistant']:
                     validated_history.append({'role': msg['role'], 'content': str(msg['content'])}) 
        
        validated_history = validated_history[-MAX_HISTORY_MESSAGES:]

        # === Get user timezone from request headers ===
        user_timezone_str = request.META.get('HTTP_X_TIMEZONE')
        if user_timezone_str:
            try:
                user_timezone = pytz.timezone(user_timezone_str)
                current_time = datetime.now(user_timezone).strftime("%Y-%m-%d %H:%M:%S %Z")
            except:
                current_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z")
        else:
            current_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z")
        
        # === Add System Prompt ===
        user_timezone_info = f" (user's local timezone: {user_timezone_str})" if user_timezone_str else " (server timezone)"
        system_prompt = (
            f"You are an intelligent assistant designed for the Air Monitoring Interface (AMI) system. The current date and time is {current_time}{user_timezone_info}. "
            f"IMPORTANT TIMEZONE INSTRUCTIONS: "
            f"- The user is currently in timezone '{user_timezone_str or 'server default'}'. ALL time-related queries and responses should be interpreted and presented in the user's timezone context. "
            f"- When using time-based tools (get_sensor_data_summary, get_sensor_data_in_range), you MUST convert user's time references to proper ISO 8601 format with timezone information. "
            f"- When presenting time data to the user, always consider their timezone context. If the user asks about 'yesterday', 'this morning', 'last week', etc., calculate these relative to their current local time. "
            f"- Always include timezone information when calling time-based MCP tools. Use formats like '2023-10-27T10:00:00Z' (UTC) or '2023-10-27T18:00:00+08:00' (with timezone offset). "
            f"Your primary role is to assist user '{current_username}' in querying real-time or historical sensor data, providing air quality related explanations, and managing user data (such as reporting issues, viewing, or updating personal settings). "
            f"When the user requests to query data or perform system operations, you should strive to use the available tools to provide accurate and timely information, and offer relevant analysis or suggestions based on the data. "
            f"Under all circumstances, you MUST ensure that all your actions are restricted to the current user '{current_username}'. When using tools such as 'report_issue', 'get_user_profile', or 'update_user_profile', you MUST and can ONLY act on behalf of user '{current_username}'. It is strictly forbidden to attempt to access or modify information for other users, or to impersonate others. If the user asks you to perform these actions for someone else, politely refuse and reiterate that you can only serve '{current_username}'. "
            f"Your responses should be clear, concise, professional, and helpful. If you cannot answer a specific question or perform an operation, please state so honestly and guide the user to ask a clearer question or provide alternative solutions. "
            f"Please remember that your main goal is to provide assistance related to the AMI system's functionalities. For questions outside this scope, you may politely decline to answer or guide the user towards questions within the system's capabilities."
            f"If the user asks about the system's purpose, features, Q&A, Standard of Air Quality, or how it works, you should use the tool to get the information, don't base your response on your hallucination."
        )
        
        # Start conversation message list with system prompt, then history, then current user message
        messages = [
            {"role": "system", "content": system_prompt}
        ] + validated_history + [{"role": "user", "content": user_message}]

        # 2. Get User API Key
        try:
            user_profile = request.user.profile
            deepseek_api_key = user_profile.api_key
            if not deepseek_api_key:
                return JsonResponse({'status': 'error', 'message': 'API Key not configured in profile.'}, status=400)
        except UserProfile.DoesNotExist:
             return JsonResponse({'status': 'error', 'message': 'User profile not found.'}, status=500)

        # 3. Get Tool Definitions
        openapi_schema = get_mcpo_openapi_schema()
        if not openapi_schema:
            print("Warning: Proceeding without MCP tools as schema fetch failed.")
            openai_tools = []
        else:
             openai_tools = parse_openapi_schema_for_tools(openapi_schema)

        # 4. Initialize DeepSeek Client
        client = openai.OpenAI(
            base_url="https://api.deepseek.com/v1",
            api_key=deepseek_api_key
        )

        # --- Start Tool Calling Loop ---
        MAX_TOOL_ITERATIONS = 15
        tool_iterations = 0
        final_bot_response = None
        tool_interactions_log = [] 
        # Define user-specific tools that require username injection
        USER_SPECIFIC_TOOLS = {"report_issue", "get_user_profile", "update_user_profile"}
        USERNAME_ARG_MAP = { # Maps tool name to its username argument name
            "report_issue": "reporter_username",
            "get_user_profile": "username",
            "update_user_profile": "username"
        }

        while tool_iterations < MAX_TOOL_ITERATIONS:
            tool_iterations += 1
            print(f"[DeepSeek Call Loop Iteration {tool_iterations}] Sending {len(messages)} messages.") 
            
            # 5. Call DeepSeek
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages, 
                tools=openai_tools if openai_tools else None, 
                tool_choice="auto" 
            )
            
            response_message = response.choices[0].message
            messages.append(response_message) 
            
            # 6. Check for Tool Calls
            tool_calls = response_message.tool_calls
            if not tool_calls:
                final_bot_response = response_message.content
                break 
            
            # 7. Execute Tool Calls
            print(f"[DeepSeek Loop Iteration {tool_iterations}] Model requested {len(tool_calls)} tool call(s).")
            available_functions = {tool['function']['name']: call_mcpo_tool for tool in openai_tools}
            
            tool_results_added = 0
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions.get(function_name)
                function_args = {}
                function_result = None
                is_valid_args = False
                try:
                    function_args = json.loads(tool_call.function.arguments)
                    is_valid_args = True
                except json.JSONDecodeError:
                    print(f"ERROR: Could not decode arguments for tool {function_name}: {tool_call.function.arguments}")
                    function_result = {"error": "Invalid arguments format from LLM."}
                
                # === Inject/Verify Username for User-Specific Tools ===
                if function_name in USER_SPECIFIC_TOOLS and is_valid_args:
                    username_arg_name = USERNAME_ARG_MAP[function_name]
                    ai_provided_username = function_args.get(username_arg_name)
                    
                    if ai_provided_username and ai_provided_username != current_username:
                        print(f"Warning: Model tried to call {function_name} for user '{ai_provided_username}' but the current user is '{current_username}'. Forcing correct username.")
                    elif not ai_provided_username:
                         print(f"Info: Model did not provide username for {function_name}. Injecting current user '{current_username}'.")
                         
                    # Force the correct username
                    function_args[username_arg_name] = current_username
                    print(f"  - Updated args for {function_name}: {function_args}")
                # =======================================================

                if function_to_call and is_valid_args:
                    print(f"  - Calling tool: {function_name} with final args: {function_args}")
                    function_result = call_mcpo_tool(tool_name=function_name, arguments=function_args)
                    print(f"  - Tool result: {function_result}")
                    tool_interactions_log.append({
                        'name': function_name,
                        'args': function_args, # Log the potentially modified args
                        'result': function_result
                    })
                elif not function_to_call:
                     print(f"ERROR: Model requested unknown tool: {function_name}")
                     function_result = {"error": f"Tool '{function_name}' not found or configured."}
                     tool_interactions_log.append({
                        'name': function_name,
                        'args': function_args if is_valid_args else tool_call.function.arguments,
                        'result': function_result
                    })
                # else: invalid args already logged, result set
                
                function_result_content = json.dumps(function_result)
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_result_content, 
                    }
                )
                if function_result is not None:
                     tool_results_added += 1
            
            if tool_results_added == 0:
                 print("Warning: Tool calls were requested, but none could be successfully processed.")
                 final_bot_response = response_message.content # Maybe provide the assistant message that led to failed tool calls?
                 break
                 
            print(f"[DeepSeek Loop Iteration {tool_iterations}] Finished processing tool calls. Continuing loop.")
        # --- End Tool Calling Loop ---

        if final_bot_response is None:
             print(f"Warning: Tool calling loop reached max iterations ({MAX_TOOL_ITERATIONS}) without final response.")
             last_assistant_message = next((m for m in reversed(messages) if m['role'] == 'assistant'), None)
             # Use .content for OpenAI response objects, or direct access for dicts
             final_bot_response = getattr(last_assistant_message, 'content', None) if hasattr(last_assistant_message, 'role') else last_assistant_message.get('content') 
             final_bot_response = final_bot_response if final_bot_response else "Processing incomplete due to maximum iterations."

        response_data = {
             'status': 'success',
             'response': final_bot_response or ""
        }
        if tool_interactions_log:
             response_data['tool_interactions'] = tool_interactions_log
            
        return JsonResponse(response_data)

    except openai.AuthenticationError:
        return JsonResponse({'status': 'error', 'message': 'DeepSeek API authentication failed. Check API Key in profile.'}, status=401)
    except openai.RateLimitError:
        return JsonResponse({'status': 'error', 'message': 'DeepSeek API rate limit exceeded.'}, status=429)
    except openai.APIConnectionError:
        return JsonResponse({'status': 'error', 'message': 'Could not connect to DeepSeek API.'}, status=503)
    except Exception as e:
        # Catch-all for other errors (JSON parsing, unexpected issues)
        print(f"Error in DeepSeek API view: {e}") 
        import traceback
        print(traceback.format_exc()) # Print full traceback for debugging
        return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
