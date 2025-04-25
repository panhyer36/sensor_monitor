from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('report/', views.report_issue_view, name='report'),
    path('send-test-email/', views.send_test_email, name='send_test_email'),
    path('check_api_key/', views.check_api_key_view, name='check_api_key'),
    path('analyze/', views.analyze_view, name='analyze'),
] 