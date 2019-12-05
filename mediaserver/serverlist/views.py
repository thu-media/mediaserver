import base64
import functools
import json
import math
import os
import pprint
import requests
import time
import uuid

from datetime import datetime, timedelta
from .models import AccessLog, Client, ClientReport, UnknownReport
from django.conf import settings
from django.contrib import auth
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import models, transaction
from django.http import Http404, HttpResponseBadRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from six.moves import urllib

# Create your views here.

def get_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    print(request.META)
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    else:
        print(request.META.get('REMOTE_ADDR'))
        return request.META.get('REMOTE_ADDR')

def index(request):
    client_reports = ClientReport.objects.values('client_id').annotate(id=models.Max('id'))
    clients_no_report = Client.objects.exclude(id__in=[c['client_id'] for c in client_reports]).order_by('client_id')
    client_reports = ClientReport.objects.filter(id__in=[c['id'] for c in client_reports]).select_related('client').order_by('client__client_id')
    now = time.time()
    table = []
    for client_report in client_reports:
        client = client_report.client
        report = json.loads(client_report.report)
        status = 'ok'
        if client_report.version != '0.1.2.1':
            status = '监测脚本不匹配'
            platform = ''
        elif report['uname'][0] == 'Linux':
            platform = '{:s} {:s}'.format(report['dist'][0].capitalize(), report['dist'][1])
        elif report['uname'][0] == 'Windows':
            platform = 'Windows {:s}'.format(report['uname'][2])
        else:
            platform = report['uname'][0]
        tr = []
        tr.append(client.display_name or client.client_id)
        tr.append(platform)
        ips = [client_report.ip]
        tr.append(ips)
        if status == 'ok':
            tr.append([
                    '{:d}核{:d}线程'.format(report['cpu_count_physical'], report['cpu_count_logical']),
                    '(使用 {:.0f}%)'.format(report['cpu_percent']),
                    '最高频率 {:.1f}GHz'.format(report['cpu_freq'][2] / 1000),
                ])
            tr.append('N/A' if report['loadavg'] is None else '{:.1f}'.format(report['loadavg'][2]))
            tr.append('{:.1f}G ({:.0f}%)'.format(report['virtual_memory'][0] / 1024 ** 3, report['virtual_memory'][2]))
            disks = list(zip(report['disk_partitions'], report['disk_usage']))
            disks.sort(key=lambda a: (a[0][0], -a[1][0]))
            disks = [usage for i, (partition, usage) in enumerate(disks) if partition[0] not in set(p[0] for p, _ in disks[:i])]
            tr.append(['{:.0f}G ({:.0f}%)'.format(disk[0] / 1024**3, disk[3]) for disk in disks if disk[0] / 1024**3 > 9])
            if report['nvml_version']:
                tr.append([dev['nvmlDeviceGetName'] for dev in report['nvmlDevices']])
                tr.append(['{:.1f}G ({:.0f}%)'.format(
                        dev['nvmlDeviceGetMemoryInfo']['total'] / 1024**3,
                        dev['nvmlDeviceGetMemoryInfo']['used'] / dev['nvmlDeviceGetMemoryInfo']['total'] * 100,
                    ) for dev in report['nvmlDevices']])
                tr.append(['{:s}% {:.0f}W {:d}℃'.format(
                        '-' if dev['nvmlDeviceGetUtilizationRates']['gpu'] is None else '{:d}'.format(dev['nvmlDeviceGetUtilizationRates']['gpu']),
                        dev['nvmlDeviceGetPowerUsage'] / 1000,
                        dev['nvmlDeviceGetTemperature'],
                    ) for dev in report['nvmlDevices']])
            else:
                tr.extend(['N/A'] * 3)
            users = [user[0] for user in report['users']]
            users = sorted(list(set(users)))
            if len(users) > 4:
                users = users[:3] + ['...']
            tr.append(users)
            tr.append('{:.0f} 天'.format((now - report['boot_time']) / 86400, 0))
            dt = now - client_report.created_at.timestamp()
            if dt >= 86400:
                tr.append([
                    '{:.0f} 分钟前'.format(dt / 60),
                    '({:.1f} 天前)'.format(dt / 86400),
                ])
            else:
                tr.append('{:.0f} 分钟前'.format(dt / 60))
        else:
            tr += [''] * 9
            tr.append(status)
        tr.append(client.manager)
        tr.append(client.info)
        table.append({'client': client, 'tr': tr})
    AccessLog.objects.create(ip=get_ip(request), target='serverlist:index')
    return render(request, 'serverlist/index.html', {'table': table})

def client(request, pk):
    client = get_object_or_404(Client.objects, pk=pk)
    client_reports = ClientReport.objects.filter(client=client).order_by('-id')
    paginator = Paginator(client_reports, 100)
    client_reports = paginator.get_page(request.GET.get('page'))
    AccessLog.objects.create(ip=get_ip(request), target='serverlist:client', param=pk)
    return render(request, 'serverlist/client.html', {'client': client, 'client_reports': client_reports})

def clientchart(request, pk):
    client = get_object_or_404(Client.objects, pk=pk)
    client_reports = ClientReport.objects.filter(client=client).filter(created_at__gt=datetime.now() - timedelta(days=7)).order_by('-created_at')
    data = []
    for report in client_reports:
        day = (report.created_at.timestamp() - timezone.now().timestamp()) / 86400.
        report = json.loads(report.report)
        data.append({
            'day': day,
            'cpu': report['cpu_percent'],
            'virtual_memory': report['virtual_memory'][2],
            'gpu': [{
                'name': dev['nvmlDeviceGetName'],
                'util': dev['nvmlDeviceGetUtilizationRates']['gpu'],
                'memory': dev['nvmlDeviceGetMemoryInfo']['used'] / dev['nvmlDeviceGetMemoryInfo']['total'] * 100,
                'temperature': dev.get('nvmlDeviceGetTemperature', None),
            } for dev in report.get('nvmlDevices', [])],
        })
    AccessLog.objects.create(ip=get_ip(request), target='serverlist:clientchart', param=pk)
    return render(request, 'serverlist/clientchart.html', {'client': client, 'data': json.dumps(data)})

def clientreport(request, client_id, report_id):
    client_report = get_object_or_404(ClientReport.objects.select_related('client'), id=report_id, client_id=client_id)
    report_str = pprint.pformat(json.loads(client_report.report), width=160)
    AccessLog.objects.create(ip=get_ip(request), target='serverlist:clientreport', param=report_id)
    return render(request, 'serverlist/clientreport.html', {'client_report': client_report, 'report_str': report_str})

@csrf_exempt
def recvreport(request):
    client_id = request.POST.get('client_id')
    client_secret = request.POST.get('client_secret')
    report = request.POST.get('report')
    try:
        report = json.loads(report)
        version = report.get('version')
        assert isinstance(version, type(u''))
    except:
        return HttpResponseBadRequest()
    ip = get_ip(request)
    client = Client.objects.filter(client_id=client_id, client_secret=client_secret).first()
    if client is None:
        unknown_report = UnknownReport(client_id=client_id, client_secret=client_secret, ip=ip, version=version)
        unknown_report.save()
        raise Http404
    else:
        client_report = ClientReport(client=client, ip=ip, version=version, report=json.dumps(report, sort_keys=True))
        client_report.save()
    return JsonResponse({'error': 0, 'msg': 'ok'}, json_dumps_params={'sort_keys': True})
