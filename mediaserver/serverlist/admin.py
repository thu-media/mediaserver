from django.contrib import admin

from .models import AccessLog, Client, ClientReport, UnknownReport
from django.contrib.auth.models import User

# Register your models here.

class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'ip', 'target', 'param', 'created_at', )
    list_filter = ('ip', 'target', )
    readonly_fields = ('ip', 'target', 'param', 'info', )

class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'client_id', 'display_name', 'created_at', )


class ClientReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'ip', 'version', 'created_at', )
    list_filter = ('client__client_id', 'ip', 'version', )


class UnknownReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'client_id', 'ip', 'version', 'created_at', )
    list_filter = ('client_id', 'ip', 'version', )


admin.site.register(AccessLog, AccessLogAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(ClientReport, ClientReportAdmin)
admin.site.register(UnknownReport, UnknownReportAdmin)
