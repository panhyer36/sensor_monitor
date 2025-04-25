from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, IssueReport

# Define an inline admin descriptor for UserProfile model
# which acts a bit like a singleton
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    # Add fields from UserProfile you want to display/edit
    fields = ('api_key', 'email_notifications', 'temp_min', 'temp_max', 'humidity_min', 'humidity_max', 'co2_max', 'pm25_max', 'pm10_max', 'aqi_max')

# Define a new User admin
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline, )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_api_key') # Add API key display
    list_select_related = ('profile', )

    def get_api_key(self, instance):
        return instance.profile.api_key
    get_api_key.short_description = 'API Key' # Column header

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(IssueReport)
class IssueReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'issue_type', 'reporter', 'email', 'status', 'created_at')
    list_filter = ('issue_type', 'status', 'created_at')
    search_fields = ('title', 'description', 'reporter__username', 'email')
    readonly_fields = ('reporter', 'created_at', 'updated_at')
    fieldsets = (
        ('Issue Information', {
            'fields': ('title', 'description', 'issue_type', 'reporter', 'email')
        }),
        ('Status', {
            'fields': ('status', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
