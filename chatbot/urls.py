from django.urls import path
from . import views

app_name = 'chatbot' # Add app_name for namespacing

urlpatterns = [
    path('', views.chatbot_view, name='chatbot'),
    path('api/', views.chatbot_api, name='chatbot_api'),
    path('deepseek/', views.deepseek_chat_view, name='deepseek_chat'), # Page for DeepSeek chat
    path('deepseek_api/', views.deepseek_api_view, name='deepseek_api'), # API endpoint for DeepSeek chat
] 