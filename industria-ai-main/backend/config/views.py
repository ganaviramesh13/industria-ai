from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


def index_view(request):
    if not request.user.is_authenticated:
        return redirect('login_page')
    if request.user.role == 'ADMIN' or request.user.is_superuser:
        return redirect('admin_dashboard_page')
    elif request.user.role == 'SUPERVISOR':
        return redirect('supervisor_dashboard_page')
    return redirect('engineer_dashboard_page')


def login_page(request):
    if request.user.is_authenticated:
        return index_view(request)
    return render(request, 'login.html')


@login_required(login_url='login_page')
def engineer_dashboard_page(request):
    return render(request, 'engineer_dashboard.html')


@login_required(login_url='login_page')
def admin_dashboard_page(request):
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return redirect('engineer_dashboard_page')
    return render(request, 'admin_dashboard.html')


@login_required(login_url='login_page')
def supervisor_dashboard_page(request):
    if request.user.role not in ['SUPERVISOR', 'ADMIN'] and not request.user.is_superuser:
        return redirect('engineer_dashboard_page')
    return render(request, 'supervisor_dashboard.html')

