from django.urls import path

from . import views

app_name = 'serverlist'

urlpatterns = [
    path('', views.index, name='index'),
    path('client/<int:pk>', views.client, name='client'),
    path('client/<int:client_id>/report/<int:report_id>', views.clientreport, name='clientreport'),
    path('clientreport', views.recvreport),
]
