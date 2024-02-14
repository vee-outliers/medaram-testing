import re

import pytz
from django.http import JsonResponse
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
# from django.utils.datetime_safe import datetime

from .models import User, UserType, Depot, OperationType, Vehicle, VehicleDetails, SpecialBusDataEntry, \
    TripStatistics, OutDepotVehicleReceive, OwnDepotBusDetailsEntry, OwnDepotBusWithdraw, OutDepotVehicleSentBack, \
    HsdOilSubmission, BusesOnHand, PointData
from django.db.models import Q, Count
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.contrib.auth.hashers import check_password
import pandas as pd
from functools import wraps
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import ast
from itertools import chain
from django.utils import timezone

# RESTAPI IMPORT STARTS HERE
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app import serializers as app_serializers
import datetime
from django.db.models.functions import TruncHour
from django.db.models import Max, Subquery, OuterRef
ENCRYPTION_KEY = getattr(settings, 'ENCRYPTION_KEY', None)
if ENCRYPTION_KEY is None:
    raise ImproperlyConfigured("ENCRYPTION_KEY setting is missing")

cipher_suite = Fernet(ENCRYPTION_KEY)
indian_timezone = pytz.timezone(settings.TIME_ZONE)
from django.db.models import Sum
from django.db.models.functions import Coalesce
from dateutil.rrule import rrule, DAILY
from rest_framework.decorators import api_view


def custom_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if the specific session data exists
        user_id = request.session.get('user_id')

        if user_id is None:
            # Session data does not exist, redirect to login
            return redirect('app:index')

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def index(request):
    if request.user.is_authenticated:
        return redirect("app:dashboard")
    else:
        return render(request, 'login.html')


def do_login(request):
    user_email_phone = request.POST.get('user_email_phone')
    user_password = request.POST.get('password')
    if request.method == "POST":
        if not (user_email_phone and user_password):
            messages.error(request, "Please provide all the details!!")
            return redirect("app:index")
        user_login_data = User.objects.filter(Q(email=user_email_phone) | Q(phone_number=user_email_phone)).first()
        if user_login_data:
            encrypted_password = ast.literal_eval(user_login_data.password)
            decrypted_password = cipher_suite.decrypt(encrypted_password).decode()
            if decrypted_password == user_password:
                request.session['user_id'] = user_login_data.id
                request.session['user_type'] = user_login_data.user_type.name
                if user_login_data.point_name:
                    request.session['point_name'] = user_login_data.point_name.point_name
                else:
                    request.session['point_name'] = ''
                request.session['depot_id'] = user_login_data.depot.id
                if user_login_data.user_type.employee_designation == 4:
                    return redirect("app:hsd_oil_submission_add")
                elif user_login_data.user_type.employee_designation == 5:
                    return redirect("app:buses_on_hand_add")
                else:
                    return redirect("app:dashboard")
            else:
                messages.error(request, 'Invalid Login Credentials!!')
                return redirect("app:index")
        # if user_login_data and check_password(user_password, user_login_data.password):
        #     print(request.user.id)
        #     request.session['user_id'] = user_login_data.id
        #     request.session['user_type'] = user_login_data.user_type.name
        #     request.session['point_name'] = user_login_data.point_name.point_name
        #     return redirect("app:dashboard")
        # else:
        #     messages.error(request, 'Invalid Login Credentials!!')
        #     return redirect("app:index")
    else:
        messages.error(request, 'Login failed. Try again!!')
        return redirect("app:index")


@custom_login_required
def dashboard(request):
    return render(request, 'dashboard.html')


@custom_login_required
def logout_user(request):
    logout(request)
    try:
        del request.session['user_id']
    except:
        pass
    return HttpResponseRedirect('/')


@custom_login_required
def users_list(request):
    users_data_list = []
    users_data = User.objects.filter(~Q(status=2))
    for user in users_data:
        if user.point_name:
            point_data = PointData.objects.get(id=user.point_name.id)
            point_name = point_data.point_name
        else:
            point_name = None
        user_data = {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'employee_designation': user.user_type.employee_designation,
            'phone': user.phone_number,
            'user_type': user.user_type.name,
            'depot': user.depot.name,
            'point_name': point_name,
            'created_at': user.created_at,
        }
        if request.session['user_type'] == 'Super_admin':
            try:
                encrypted_password = ast.literal_eval(user.password)
                decrypted_password = cipher_suite.decrypt(encrypted_password).decode()
                user_data['password'] = decrypted_password
            except Exception as e:
                print(e)
                messages.error(request, ' Failed!!')
        users_data_list.append(user_data)
    return render(request, 'users/list.html', {"users": users_data_list,
                                               'employee_designations': settings.EMPLOYEE_DESIGNATION})


@custom_login_required
def user_add(request):
    if request.method == "POST":
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password = request.POST.get('password')
        point_name = request.POST.get('user_point_name')
        user_status = 0
        user_type = request.POST.get('user_type')
        depot = request.POST.get('user_depot_id')
        try:
            # phone_count = Users.objects.filter(Q(phone__iexact=phone) & ~Q(status=2))
            # if phone_count.exists():
            #     messages.error(request, 'Phone number already exist. Please try again')
            #     return redirect('app:user_add')
            # email_count = Users.objects.all().filter(Q(email__iexact=email) & ~Q(status=2))
            # if email_count.exists():
            #     messages.error(request, 'Email already exist. Please try again')
            #     return redirect('app:user_add')
            user_type_data = UserType.objects.get(id=user_type)

            if point_name:
                point_name_data = PointData.objects.get(point_name=point_name)
            else:
                point_name_data = None

            depot_data = Depot.objects.get(id=depot)
            encrypted_password = cipher_suite.encrypt(password.encode())
            user = User.objects.create(name=name, email=email, password=encrypted_password, phone_number=phone,
                                       status=user_status, user_type=user_type_data, depot=depot_data,
                                       point_name=point_name_data)
            user.save()
            messages.success(request, 'User Created Successfully')
        except Exception as e:
            print(e)
            messages.error(request, 'User Creation Failed!!')
        return redirect("app:users_list")
    try:
        user_type_data = UserType.objects.filter(Q(status=0) | Q(status=1))
        depot_data = Depot.objects.filter(Q(status=0) | Q(status=1))
        # point_name_data = PointData.objects.filter(Q(status=0) | Q(status=1))
        return render(request, 'users/add.html', {'user_type_data': user_type_data, "depot_data": depot_data})
    except Exception as e:
        print(e)
        return render(request, 'users/add.html', {})


@custom_login_required
def get_depot_point_names(request):
    depot_id = request.GET.get('depot_id')
    point_data = PointData.objects.filter(depot_name=depot_id).values('id', 'point_name')
    if point_data.exists():
        point_details = list(point_data)
        return JsonResponse({'point_details': point_details})
    else:
        return JsonResponse({'error': "Selected Depot has no point names"}, status=400)


@custom_login_required
def user_edit(request):
    user_id = request.GET.get('id')
    if user_id:
        user_data = User.objects.get(id=user_id)
        encrypted_password = ast.literal_eval(user_data.password)
        decrypted_password = cipher_suite.decrypt(encrypted_password).decode()
        original_password = decrypted_password
        user_type_id_list = []
        point_name_id_list = []
        depot_id_list = []
        if user_data.user_type:
            user_type_id_list.append(user_data.user_type.id)
        if user_data.depot:
            depot_id_list.append(user_data.depot.id)
        if user_data.point_name:
            point_name_id_list.append(user_data.point_name.point_name)
        else:
            point_name_id_list = ''

    try:
        user_type_data = UserType.objects.filter(Q(status=0) | Q(status=1))
        depot_data = Depot.objects.filter(Q(status=0) | Q(status=1))
        point_name_data = PointData.objects.filter(Q(status=0) | Q(status=1))
        return render(request, 'users/edit.html', {"user_type_data": user_type_data, 'depot_data': depot_data,
                                                   'user': user_data, "point_name_data": point_name_data,
                                                   'user_type_id_list': user_type_id_list,
                                                   'depot_id_list': depot_id_list,
                                                   'point_name_id_list': point_name_id_list,
                                                   'original_password': original_password})
    except Exception as e:
        print(e)
        return render(request, 'users/edit.html', {})


@custom_login_required
def user_update(request):
    user_id = request.POST.get('id')
    name = request.POST.get('name')
    phone = request.POST.get('phone')
    email = request.POST.get('email')
    password = request.POST.get('password')
    user_status = 0
    user_type = request.POST.get('user_type_id')
    depot = request.POST.get('user_depot_id')
    point_name = request.POST.get('user_point_name')
    if user_id:
        try:
            user_data = User.objects.get(id=user_id)
            user_data.name = name
            user_data.email = email
            if user_data.password != password:  # edited the password
                encrypted_password = cipher_suite.encrypt(password.encode())
                user_data.password = encrypted_password
            user_data.phone = phone
            user_data.status = user_status
            user_type_data = UserType.objects.get(id=user_type)
            user_data.user_type = user_type_data
            depot_data = Depot.objects.get(id=depot)
            user_data.depot = depot_data
            if point_name:
                point_name_data = PointData.objects.get(point_name=point_name)
                user_data.point_name = point_name_data
            else:
                user_data.point_name = None

            user_data.save()
            messages.success(request, 'User updated  successfully!!')
            return redirect("app:users_list")
        except Exception as e:
            print(e)
            messages.error(request, 'User update  failed!!')
            return redirect("app:users_list")
    else:
        return redirect("app:users_list")


@transaction.atomic
@custom_login_required
def user_type_list(request):
    user_type_data = UserType.objects.filter(~Q(status=2))
    return render(request, 'user_type/list.html', {"user_type_data": user_type_data})


@custom_login_required
def user_type_add(request):
    if request.method == "POST":
        name = request.POST.get('name')
        designation = request.POST.get('employee_designation')
        user_status = 0
        try:
            user_data = User.objects.get(id=request.session['user_id'])
            user_type = UserType.objects.create(name=name, status=user_status, created_by=user_data,
                                                employee_designation=designation)
            user_type.save()
            messages.success(request, 'User Type Created Successfully')
        except Exception as e:
            print(e)
            messages.error(request, 'User Type Creation Failed!!')
        return redirect("app:user_type_list")
    return render(request, 'user_type/add.html', {'employee_designations': settings.EMPLOYEE_DESIGNATION})


@custom_login_required
def user_type_edit(request):
    user_type_id = request.GET.get('id')
    if user_type_id:
        user_type_data = UserType.objects.get(id=user_type_id)
    try:
        return render(request, 'user_type/edit.html', {"user_type": user_type_data,
                                                       'employee_designations': settings.EMPLOYEE_DESIGNATION})
    except Exception as e:
        print(e)
        return render(request, 'user_type/edit.html', {})


@custom_login_required
def user_type_update(request):
    user_type_id = request.POST.get('id')
    name = request.POST.get('name')
    designation = request.POST.get('employee_designation')
    user_status = 0
    if user_type_id:
        try:
            user_type_data = UserType.objects.get(id=user_type_id)
            user_type_data.name = name
            user_type_data.status = user_status
            user_type_data.employee_designation = designation
            user_data = User.objects.get(id=request.session['user_id'])
            user_type_data.updated_by = user_data
            user_type_data.save()
            messages.success(request, 'User Type updated  successfully!!')
            return redirect("app:user_type_list")
        except Exception as e:
            print(e)
            messages.error(request, 'User Type update  failed!!')
            return redirect("app:user_type_list")
    else:
        return redirect("app:user_type_list")


@custom_login_required
def depots_list(request):
    depot_data = Depot.objects.filter(~Q(status=2))
    return render(request, 'depot/list.html', {"depots": depot_data})


@custom_login_required
def depot_add(request):
    if request.method == "POST":
        name = request.POST.get('name')
        depot_code = request.POST.get('depot_code')
        buses_allotted = request.POST.get('buses_allotted')
        depot_status = 0
        try:
            user_data = User.objects.get(id=request.session['user_id'])
            depot = Depot.objects.create(name=name, depot_code=depot_code, status=depot_status, created_by=user_data,
                                         buses_allotted=buses_allotted)
            depot.save()
            messages.success(request, 'Depot Created Successfully')
        except Exception as e:
            print(e)
            messages.error(request, 'Depot Creation Failed!!')
        return redirect("app:depots_list")

    return render(request, 'depot/add.html', {})


@custom_login_required
def depot_edit(request):
    depot_id = request.GET.get('id')
    if depot_id:
        depot_data = Depot.objects.get(id=depot_id)
    return render(request, 'depot/edit.html', {"depot": depot_data})


@custom_login_required
def depot_update(request):
    depot_id = request.POST.get('id')
    name = request.POST.get('name')
    depot_code = request.POST.get('depot_code')
    buses_allotted = request.POST.get('buses_allotted')
    depot_status = 0
    if depot_id:
        try:
            depot_data = Depot.objects.get(id=depot_id)
            depot_data.name = name
            depot_data.depot_code = depot_code
            depot_data.status = depot_status
            depot_data.buses_allotted = buses_allotted
            user_data = User.objects.get(id=request.session['user_id'])
            depot_data.updated_by = user_data
            depot_data.save()
            messages.success(request, 'Depot updated  successfully!!')
            return redirect("app:depots_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Depot update  failed!!')
            return redirect("app:depots_list")
    else:
        return redirect("app:depots_list")


@custom_login_required
def operation_type_list(request):
    operation_type_data = OperationType.objects.filter(~Q(status=2))
    return render(request, 'operation_type/list.html', {"operation_type": operation_type_data})


@custom_login_required
def operation_type_add(request):
    if request.method == "POST":
        name = request.POST.get('name')
        description = request.POST.get('description')
        status = 0
        try:
            user = User.objects.get(id=request.session['user_id'])
            operation_type = OperationType.objects.create(name=name, description=description, status=status,
                                                          created_by=user)
            operation_type.save()
            messages.success(request, 'Operation Type Created Successfully')
        except Exception as e:
            print(e)
            messages.error(request, 'Operation Type Creation Failed!!')
        return redirect("app:operation_type_list")
    else:
        return render(request, 'operation_type/add.html', {})


@custom_login_required
def operation_type_edit(request):
    operation_type_id = request.GET.get('id')
    if operation_type_id:
        operation_type_data = OperationType.objects.get(id=operation_type_id)
        return render(request, 'operation_type/edit.html', {"operation_type_data": operation_type_data})
    else:
        return render(request, 'operation_type/edit.html', {})


@custom_login_required
def operation_type_update(request):
    operation_type_id = request.POST.get('id')
    name = request.POST.get('name')
    description = request.POST.get('description')
    status = 0
    if operation_type_id:
        try:
            operation_type_data = OperationType.objects.get(id=operation_type_id)
            operation_type_data.name = name
            operation_type_data.description = description
            operation_type_data.status = status
            user_data = User.objects.get(id=request.session['user_id'])
            operation_type_data.updated_by = user_data
            operation_type_data.save()
            messages.success(request, 'Operation Type updated  successfully!!')
            return redirect("app:operation_type_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Operation Type update  failed!!')
            return redirect("app:operation_type_list")
    else:
        return redirect("app:operation_type_list")


@custom_login_required
def vehicle_list(request):
    vehicle_data = Vehicle.objects.filter(~Q(status=2))
    return render(request, 'vehicle/list.html', {"vehicle_data": vehicle_data})


@custom_login_required
def vehicle_add(request):
    if request.method == "POST":
        name = request.POST.get('name')
        vehicle_owner = request.POST.get('vehicle_owner')
        status = 0
        try:
            user = User.objects.get(id=request.session['user_id'])
            vehicle = Vehicle.objects.create(name=name, status=status, created_by=user, vehicle_owner=vehicle_owner)
            vehicle.save()
            messages.success(request, 'Vehicle  Created Successfully')
        except Exception as e:
            print(e)
            messages.error(request, 'Vehicle Type Creation Failed!!')
        return redirect("app:vehicle_list")
    else:
        return render(request, 'vehicle/add.html', {})


@custom_login_required
def vehicle_edit(request):
    vehicle_id = request.GET.get('id')
    if vehicle_id:
        vehicle_data = Vehicle.objects.get(id=vehicle_id)
        return render(request, 'vehicle/edit.html', {"vehicle_data": vehicle_data})
    else:
        return render(request, 'vehicle/edit.html', {})


@custom_login_required
def vehicle_update(request):
    vehicle_id = request.POST.get('id')
    name = request.POST.get('name')
    # vehicle_owner = request.POST.get('vehicle_owner')
    status = 0
    if vehicle_id:
        try:
            vehicle_data = Vehicle.objects.get(id=vehicle_id)
            vehicle_data.name = name
            vehicle_data.status = status
            # vehicle_data.vehicle_owner = vehicle_owner
            user_data = User.objects.get(id=request.session['user_id'])
            vehicle_data.updated_by = user_data
            vehicle_data.save()
            messages.success(request, 'Vehicle  updated  successfully!!')
            return redirect("app:vehicle_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Vehicle update  failed!!')
            return redirect("app:vehicle_list")
    else:
        return redirect("app:vehicle_list")


@custom_login_required
def vehicle_details_list(request):
    vehicle_details_data = VehicleDetails.objects.filter(~Q(status=2))
    return render(request, 'vehicle_details/list.html', {"vehicle_details": vehicle_details_data})


@custom_login_required
def vehicle_detail_add(request):
    if request.method == "POST":
        vehicle_id = request.POST.get('vehicle_id')
        depot_id = request.POST.get('depot_id')
        bus_number = request.POST.get('bus_number')
        opt_type_id = request.POST.get('opt_type')
        vehicle_owner = request.POST.get('vehicle_owner')
        vehicle_detail_status = 0
        try:
            vehicle_data = Vehicle.objects.get(id=vehicle_id)
            depot_data = Depot.objects.get(id=depot_id)
            operation_type_data = OperationType.objects.get(id=opt_type_id)
            user_data = User.objects.get(id=request.session['user_id'])
            vehicle_detail = VehicleDetails.objects.create(vehicle_name=vehicle_data, depot=depot_data,
                                                           opt_type=operation_type_data, bus_number=bus_number,
                                                           status=vehicle_detail_status, created_by=user_data,
                                                           vehicle_owner=vehicle_owner)
            vehicle_detail.save()
            messages.success(request, 'Vehicle Details saved Successfully')
        except Exception as e:
            print(e)
            messages.error(request, 'Vehicle Details Creation Failed!!')
        return redirect("app:vehicle_details_list")
    try:
        vehicle_data = Vehicle.objects.filter(Q(status=0) | Q(status=1))
        depot_data = Depot.objects.filter(Q(status=0) | Q(status=1))
        operation_type_data = OperationType.objects.filter(Q(status=0) | Q(status=1))
        return render(request, 'vehicle_details/add.html', {'vehicle_data': vehicle_data, "depot_data": depot_data,
                                                            'operation_type_data': operation_type_data})
    except Exception as e:
        print(e)
        return render(request, 'vehicle_details/add.html', {})


@custom_login_required
def vehicle_detail_edit(request):
    vehicle_detail_id = request.GET.get('id')
    if vehicle_detail_id:
        vehicle_detail_data = VehicleDetails.objects.get(id=vehicle_detail_id)
        operation_type_id_list = []
        depot_id_list = []
        vehicle_id_list = []
        if vehicle_detail_data.depot:
            depot_id_list.append(vehicle_detail_data.depot.id)
        if vehicle_detail_data.opt_type:
            operation_type_id_list.append(vehicle_detail_data.opt_type.id)
        if vehicle_detail_data.vehicle_name:
            vehicle_id_list.append(vehicle_detail_data.vehicle_name.id)
    try:
        vehicle_data = Vehicle.objects.filter(Q(status=0) | Q(status=1))
        depot_data = Depot.objects.filter(Q(status=0) | Q(status=1))
        operation_type_data = OperationType.objects.filter(Q(status=0) | Q(status=1))
        return render(request, 'vehicle_details/edit.html', {"vehicle_data": vehicle_data, 'depot_data': depot_data,
                                                             'operation_type_data': operation_type_data,
                                                             'operation_type_id_list': operation_type_id_list,
                                                             'depot_id_list': depot_id_list,
                                                             'vehicle_id_list': vehicle_id_list,
                                                             'vehicle_detail': vehicle_detail_data})
    except Exception as e:
        print(e)
        return render(request, 'vehicle_details/edit.html', {})


@custom_login_required
def vehicle_detail_update(request):
    vehicle_detail_id = request.POST.get('id')
    vehicle_id = request.POST.get('vehicle_id')
    depot_id = request.POST.get('depot_id')
    bus_number = request.POST.get('bus_number')
    opt_type_id = request.POST.get('opt_type')
    vehicle_owner = request.POST.get('vehicle_owner')
    vehicle_detail_status = 0
    if vehicle_detail_id:
        try:
            vehicle_detail_data = VehicleDetails.objects.get(id=vehicle_detail_id)
            vehicle_detail_data.bus_number = bus_number
            vehicle_detail_data.vehicle_owner = vehicle_owner
            vehicle_detail_data.status = vehicle_detail_status
            vehicle_data = Vehicle.objects.get(id=vehicle_id)
            vehicle_detail_data.vehicle_name = vehicle_data
            depot_data = Depot.objects.get(id=depot_id)
            vehicle_detail_data.depot = depot_data
            operation_type_data = OperationType.objects.get(id=opt_type_id)
            vehicle_detail_data.opt_type = operation_type_data
            user_data = User.objects.get(id=request.session['user_id'])
            vehicle_detail_data.updated_by = user_data
            vehicle_detail_data.save()
            messages.success(request, 'Vehicle Details updated  successfully!!')
            return redirect("app:vehicle_details_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Vehicle Details update  failed!!')
            return redirect("app:vehicle_details_list")
    else:
        return redirect("app:vehicle_details_list")


@transaction.atomic
@custom_login_required
def operation_type_import(request):
    print("Called")
    if request.method == "POST":
        file = request.FILES.get('operation_type_list')
        try:
            user_data = User.objects.get(id=request.session['user_id'])
            df = pd.read_excel(file)
            row_iter = df.iterrows()
            for i, row in row_iter:
                print(row)
                try:
                    name = row[1]
                    operation_type_exist = OperationType.objects.filter(name=name).count()
                    if operation_type_exist == 0:
                        operation_type = OperationType.objects.create(name=name, description=row[2], status=0,
                                                                      created_by=user_data)
                        operation_type.save()
                    else:
                        pass
                except Exception as e:
                    print(e)
            return redirect("app:operation_type_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Operation Type import failed!!')
        return redirect("app:operation_type_list")
    return render(request, 'operation_type/import.html', {})


@custom_login_required
def spl_bus_data_entry_list(request):
    if request.session['user_type'] == 'PARENT DEPOT':
        spl_bus_data_entry_data = SpecialBusDataEntry.objects.filter(~Q(status=2) &
                                                                     Q(special_bus_sending_depot=
                                                                       request.session['depot_id']))
        return render(request, 'spl_bus_data_entry/list.html', {"spl_bus_data_entry_data": spl_bus_data_entry_data})
    spl_bus_data_entry_data = SpecialBusDataEntry.objects.filter(~Q(status=2))
    return render(request, 'spl_bus_data_entry/list.html', {"spl_bus_data_entry_data": spl_bus_data_entry_data})


@transaction.atomic
@custom_login_required
def spl_bus_data_entry_add(request):
    if request.method == "POST":
        special_bus_sending_depot = request.POST.get('special_bus_sending_depot')
        special_bus_reporting_depot = request.POST.get('special_bus_reporting_depot')
        # bus_type means operation_type
        # bus_number means vechicle_no
        bus_type = request.POST.get('opt_type')
        bus_number = request.POST.get('vehicle_number')
        log_sheet_no = request.POST.get('log_sheet_no')
        driver1_name = request.POST.get('driver1_name')
        driver1_staff_no = request.POST.get('driver1_staff_no')
        driver1_phone_number = request.POST.get('driver1_phone_number')
        driver2_name = request.POST.get('driver2_name')
        driver2_staff_no = request.POST.get('driver2_staff_no')
        driver2_phone_number = request.POST.get('driver2_phone_number')
        incharge_name = request.POST.get('incharge_name')
        incharge_phone_number = request.POST.get('incharge_phone_number')
        status = 0
        try:
            if special_bus_sending_depot == special_bus_reporting_depot:
                messages.error(request, 'Sending Depot and Reporting Depot should not be same!!')
                return redirect("app:spl_bus_data_entry_add")
            sending_depot_data = Depot.objects.get(id=special_bus_sending_depot)
            reporting_depot_data = Depot.objects.get(id=special_bus_reporting_depot)
            bus_type_data = OperationType.objects.get(id=bus_type)
            bus_number_data = VehicleDetails.objects.get(bus_number=bus_number)

            user_data = User.objects.get(id=request.session['user_id'])
            spl_bus_data_entry = SpecialBusDataEntry.objects.create(special_bus_sending_depot=sending_depot_data,
                                                                    special_bus_reporting_depot=reporting_depot_data,
                                                                    bus_type=bus_type_data, bus_number=bus_number_data,
                                                                    log_sheet_no=log_sheet_no,
                                                                    driver1_name=driver1_name,
                                                                    driver1_staff_no=driver1_staff_no,
                                                                    driver1_phone_number=driver1_phone_number,
                                                                    driver2_name=driver2_name,
                                                                    driver2_staff_no=driver2_staff_no,
                                                                    driver2_phone_number=driver2_phone_number,
                                                                    incharge_name=incharge_name,
                                                                    incharge_phone_number=incharge_phone_number,
                                                                    status=status, created_by=user_data)
            spl_bus_data_entry.save()
            messages.success(request, 'Special bus data entry details saved Successfully')
        except Exception as e:
            print(e)
            messages.error(request, 'Special bus data entry details creation Failed!!')
        return redirect("app:spl_bus_data_entry_list")
    try:
        if request.session['user_type'] == 'PARENT DEPOT':
            sending_depot_data = Depot.objects.filter(id=request.session['depot_id'])
        else:
            sending_depot_data = Depot.objects.filter(Q(status=0) | Q(status=1))
        depot_data = Depot.objects.filter(Q(status=0) | Q(status=1))
        operation_type_data = OperationType.objects.filter(Q(status=0) | Q(status=1))
        return render(request, 'spl_bus_data_entry/add.html', {'operation_type_data': operation_type_data,
                                                               'depot_data': depot_data,
                                                               'sending_depot_data': sending_depot_data})
    except Exception as e:
        print(e)
        return render(request, 'spl_bus_data_entry/add.html', {})


@custom_login_required
def get_depot_vehicle_number(request):
    depot_id = request.GET.get('depot_id')
    vehicle_details_data = VehicleDetails.objects.filter(depot=depot_id).values('id', 'bus_number')
    if vehicle_details_data.exists():
        vehicle_details = []
        for bus_number in vehicle_details_data:
            special_bus_entry = SpecialBusDataEntry.objects.filter(bus_number__bus_number=bus_number['bus_number'])
            if special_bus_entry.count() == 0:
                vehicle_details.append(bus_number)
                # vehicle_details = list(vehicle_details_data)
        return JsonResponse({'vehicle_details': vehicle_details})
    else:
        return JsonResponse({'error': "Selected Depot has no bus numbers available"}, status=400)


@custom_login_required
def spl_bus_data_entry_edit(request):
    spl_bus_data_entry_id = request.GET.get('id')
    if spl_bus_data_entry_id:
        spl_bus_data_entry_data = SpecialBusDataEntry.objects.get(id=spl_bus_data_entry_id)
        depot_sending_list = []
        depot_reporting_list = []
        bus_type_id_list = []

        if spl_bus_data_entry_data.special_bus_sending_depot:
            depot_sending_list.append(spl_bus_data_entry_data.special_bus_sending_depot.id)
        if spl_bus_data_entry_data.special_bus_reporting_depot:
            depot_reporting_list.append(spl_bus_data_entry_data.special_bus_reporting_depot.id)
        if spl_bus_data_entry_data.bus_type:
            bus_type_id_list.append(spl_bus_data_entry_data.bus_type.id)

    try:
        depot_sending_data = Depot.objects.filter(Q(status=0) | Q(status=1))
        depot_reporting_data = Depot.objects.filter(Q(status=0) | Q(status=1))
        operation_type_data = OperationType.objects.filter(Q(status=0) | Q(status=1))

        return render(request, 'spl_bus_data_entry/edit.html',
                      {'depot_sending_data': depot_sending_data,
                       'depot_reporting_data': depot_reporting_data,
                       'depot_sending_list': depot_sending_list,
                       'depot_reporting_list': depot_reporting_list,
                       'operation_type_data': operation_type_data,
                       'bus_type_id_list': bus_type_id_list,
                       'spl_bus_data_entry_data': spl_bus_data_entry_data})
    except Exception as e:
        print(e)
        return render(request, 'spl_bus_data_entry/edit.html', {})


@custom_login_required
def spl_bus_data_entry_update(request):
    spl_bus_data_entry_id = request.POST.get('id')
    special_bus_sending_depot = request.POST.get('special_bus_sending_depot')
    special_bus_reporting_depot = request.POST.get('special_bus_reporting_depot')
    bus_type = request.POST.get('opt_type')
    bus_number = request.POST.get('vehicle_number')
    log_sheet_no = request.POST.get('log_sheet_no')
    driver1_name = request.POST.get('driver1_name')
    driver1_staff_name = request.POST.get('driver1_staff_name')
    driver1_phone_number = request.POST.get('driver1_phone_number')
    driver2_name = request.POST.get('driver2_name')
    driver2_staff_name = request.POST.get('driver2_staff_name')
    driver2_phone_number = request.POST.get('driver2_phone_number')
    incharge_name = request.POST.get('incharge_name')
    incharge_phone_number = request.POST.get('incharge_phone_number')
    status = 0
    if spl_bus_data_entry_id:
        try:
            spl_bus_data_entry_data = SpecialBusDataEntry.objects.get(id=spl_bus_data_entry_id)

            sending_depot_data = Depot.objects.get(id=special_bus_sending_depot)
            spl_bus_data_entry_data.special_bus_sending_depot = sending_depot_data

            reporting_depot_data = Depot.objects.get(id=special_bus_reporting_depot)
            spl_bus_data_entry_data.special_bus_reporting_depot = reporting_depot_data

            operation_type_data = OperationType.objects.get(id=bus_type)
            spl_bus_data_entry_data.opt_type = operation_type_data

            vehicle_number = VehicleDetails.objects.get(bus_number=bus_number)
            spl_bus_data_entry_data.bus_number = vehicle_number

            spl_bus_data_entry_data.log_sheet_no = log_sheet_no
            spl_bus_data_entry_data.driver1_name = driver1_name
            spl_bus_data_entry_data.driver1_staff_name = driver1_staff_name
            spl_bus_data_entry_data.driver1_phone_number = driver1_phone_number
            spl_bus_data_entry_data.driver2_name = driver2_name
            spl_bus_data_entry_data.driver2_staff_name = driver2_staff_name
            spl_bus_data_entry_data.driver2_phone_number = driver2_phone_number
            spl_bus_data_entry_data.incharge_name = incharge_name
            spl_bus_data_entry_data.incharge_phone_number = incharge_phone_number
            spl_bus_data_entry_data.status = status
            user_data = User.objects.get(id=request.session['user_id'])
            spl_bus_data_entry_data.updated_by = user_data
            spl_bus_data_entry_data.save()
            messages.success(request, 'Special bus data entry updated  successfully!!')
            return redirect("app:spl_bus_data_entry_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Special bus data entry update  failed!!')
            return redirect("app:spl_bus_data_entry_list")
    else:
        return redirect("app:spl_bus_data_entry_list")


@transaction.atomic
@custom_login_required
def vehicle_names_import(request):
    print("Called")
    if request.method == "POST":
        file = request.FILES.get('vehicle_names_list')
        try:
            user_data = User.objects.get(id=request.session['user_id'])
            df = pd.read_excel(file)
            row_iter = df.iterrows()
            for i, row in row_iter:
                print(row)
                try:
                    name = row[0]
                    vehicle_exist = Vehicle.objects.filter(name=name).count()
                    if vehicle_exist == 0:
                        vehicle = Vehicle.objects.create(name=name, vehicle_owner=row[1], status=0,
                                                         created_by=user_data)
                        vehicle.save()
                    else:
                        pass
                except Exception as e:
                    print(e)
            return redirect("app:vehicle_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Vehicle import failed!!')
        return redirect("app:vehicle_list")
    return render(request, 'vehicle/import.html', {})


@transaction.atomic
@custom_login_required
def depot_import(request):
    print("Called")
    if request.method == "POST":
        file = request.FILES.get('depot_list')
        try:
            user_data = User.objects.get(id=request.session['user_id'])
            df = pd.read_excel(file)
            row_iter = df.iterrows()
            for i, row in row_iter:
                print(row)
                try:
                    name = row[1]
                    depot_exist = Depot.objects.filter(name=name).count()
                    if depot_exist == 0:
                        depot = Depot.objects.create(name=name, depot_code=row[0], status=0, created_by=user_data)
                        depot.save()
                    else:
                        pass
                except Exception as e:
                    print(e)
            return redirect("app:depots_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Deport import failed!!')
        return redirect("app:depots_list")
    return render(request, 'depot/import.html', {})


@transaction.atomic
@custom_login_required
def vehicle_details_import(request):
    print("Called")
    if request.method == "POST":
        file = request.FILES.get('vehicle_details_list')
        try:
            user_data = User.objects.get(id=request.session['user_id'])
            df = pd.read_excel(file)
            row_iter = df.iterrows()
            for i, row in row_iter:
                print(row)
                try:
                    bus_number = row[2]
                    vehicle_detail_exist = VehicleDetails.objects.filter(bus_number=bus_number).count()
                    if vehicle_detail_exist == 0:
                        vehicle_name_data = Vehicle.objects.get(name=row[4])
                        depot_data = Depot.objects.get(depot_code=row[1])
                        opt_type_data = OperationType.objects.get(name=row[3])
                        vehicle_detail = VehicleDetails.objects.create(vehicle_name=vehicle_name_data, depot=depot_data,
                                                                       opt_type=opt_type_data,
                                                                       status=0, created_by=user_data,
                                                                       bus_number=bus_number, depot_name=row[5],
                                                                       region_name=row[6], zone_name=row[7])
                        vehicle_detail.save()
                    else:
                        pass
                except Exception as e:
                    print(e)
            return redirect("app:vehicle_details_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Vehicle Details import failed!!')
        return redirect("app:vehicle_details_list")
    return render(request, 'vehicle_details/import.html', {})


@custom_login_required
def trip_start_add(request):
    if request.method == "POST":
        unique_code = request.POST.get('trip_start_unique_no')
        bus_number = request.POST.get('trip_start_bus_number')
        total_ticket_amount = request.POST.get('total_ticket_amount')
        total_adult_passengers = request.POST.get('total_adult_passengers')
        total_child_passengers = request.POST.get('total_child_passengers')
        mhl_adult_passengers = request.POST.get('mhl_adult_passengers')
        mhl_child_passengers = request.POST.get('mhl_child_passengers')
        mhl_adult_amount = request.POST.get('mhl_adult_amount')
        mhl_child_amount = request.POST.get('mhl_child_amount')
        start_from_location = request.POST.get('start_from_location')
        start_to_location = request.POST.get('start_to_location')
        entry_type = request.POST.get('entry_type')
        service_operated_date = request.POST.get('service_operated_date')
        status = 0

        try:
            user_data = User.objects.get(id=request.session['user_id'])
            start_from_point_data = PointData.objects.get(point_name=start_from_location)
            start_to_pont_data = PointData.objects.get(point_name=start_to_location)

            statistics_data_entry = TripStatistics.objects.create(unique_code=unique_code, bus_number=bus_number,
                                                                  total_ticket_amount=total_ticket_amount,
                                                                  total_adult_passengers=total_adult_passengers,
                                                                  total_child_passengers=total_child_passengers,
                                                                  mhl_adult_passengers=mhl_adult_passengers,
                                                                  mhl_child_passengers=mhl_child_passengers,
                                                                  mhl_adult_amount=mhl_adult_amount,
                                                                  mhl_child_amount=mhl_child_amount,
                                                                  entry_type=entry_type,
                                                                  status=status, created_by=user_data,
                                                                  start_from_location=start_from_point_data,
                                                                  start_to_location=start_to_pont_data,
                                                                  data_enter_by=user_data,
                                                                  service_operated_date=service_operated_date)
            statistics_data_entry.save()
            messages.success(request, 'Statistics Trip Data Created Successfully')
            return redirect("app:trip_start_add")
        except Exception as e:
            print(e)
            messages.error(request, 'Statistics Trip Data Creation Failed!!')
            return redirect("app:trip_start_add")
    else:
        if request.session['user_type'] == 'PSG ENTRY DOWN':
            out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects.all()
            own_depot_vehicle_receive_data = OwnDepotBusDetailsEntry.objects.all()
            combined_data = list(chain(out_depot_vehicle_receive_data, own_depot_vehicle_receive_data))
        else:
            depot_data = Depot.objects.get(id=request.session['depot_id'])
            out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects.filter(out_depot_bus_reporting_depot=depot_data)
            own_depot_vehicle_receive_data = OwnDepotBusDetailsEntry.objects.filter(depot=depot_data)
            combined_data = list(chain(out_depot_vehicle_receive_data, own_depot_vehicle_receive_data))
        point_data = PointData.objects.filter(Q(status=0) | Q(status=1))
        return render(request, 'trip_statistics/trip_start/add.html',
                      {'out_depot_vehicle_receive_data': out_depot_vehicle_receive_data, 'point_data': point_data,
                       'own_depot_vehicle_receive_data': own_depot_vehicle_receive_data,
                       'combined_data': combined_data})


@custom_login_required
def get_out_and_own_depot_bus_number(request):
    unique_no = request.GET.get('unique_no')
    depot_id = request.session['depot_id']
    if request.session['user_type'] == 'PSG ENTRY DOWN':
        out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects.filter(unique_no=unique_no)
        own_depot_bus_entry_data = OwnDepotBusDetailsEntry.objects.filter(unique_no=unique_no)
    else:
        out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects.filter(Q(unique_no=unique_no) &
                                                                               Q(out_depot_bus_reporting_depot_id=depot_id))
        own_depot_bus_entry_data = OwnDepotBusDetailsEntry.objects.filter(Q(unique_no=unique_no) & Q(depot_id=depot_id))
    if out_depot_vehicle_receive_data.exists():
        special_bus_data = out_depot_vehicle_receive_data[0].special_bus_data_entry
        return JsonResponse({'bus_number': special_bus_data.bus_number.bus_number})
    if own_depot_bus_entry_data.exists():
        return JsonResponse({'bus_number': own_depot_bus_entry_data[0].bus_number.bus_number})
    return JsonResponse({}, status=400)


@custom_login_required
def search_trip_end_form(request):
    trip_unqiue_no = ''
    if request.session['user_type'] == 'PSG UP THADVAI':
        trip_unqiue_no = TripStatistics.objects.filter(Q(status=0) | Q(status=1)).filter(~Q(trip_verified=True)).filter(entry_type='up').values_list('unique_code', flat=True).distinct()
    if request.method == "POST":
        unique_no = request.POST.get('unique_no')
        last_trip_details = TripStatistics.objects.filter(unique_code=unique_no).order_by('-created_at').first()
        if last_trip_details:
            return render(request, 'trip_statistics/trip_end/add.html',
                          {'last_trip_details': last_trip_details,
                           'trip_unqiue_no': trip_unqiue_no})
        else:
            messages.error(request, 'Selected Unique No has no TripStatistic details!!')
            return render(request, 'trip_statistics/trip_end/add.html',
                          {'trip_unqiue_no': trip_unqiue_no})
    try:
        return render(request, 'trip_statistics/trip_end/add.html',
                      {'trip_unqiue_no': trip_unqiue_no})
    except Exception as e:
        print(e)


@custom_login_required
def trip_end_add(request):
    trip_check_id = request.POST.get('id')
    total_ticket_amount = request.POST.get('total_ticket_amount')
    total_adult_passengers = request.POST.get('total_adult_passengers')
    total_child_passengers = request.POST.get('total_child_passengers')
    mhl_adult_passengers = request.POST.get('mhl_adult_passengers')
    mhl_child_passengers = request.POST.get('mhl_child_passengers')
    mhl_adult_amount = request.POST.get('mhl_adult_amount')
    mhl_child_amount = request.POST.get('mhl_child_amount')
    trip_verified = request.POST.get('trip_verified')
    trip_verified_time = timezone.now()
    trip_end = timezone.now()
    service_operated_date = request.POST.get('service_operated_date')
    if trip_check_id:
        try:
            trip_check_data = TripStatistics.objects.get(id=trip_check_id)
            trip_check_data.total_ticket_amount = total_ticket_amount
            trip_check_data.total_adult_passengers = total_adult_passengers
            trip_check_data.total_child_passengers = total_child_passengers
            trip_check_data.mhl_adult_passengers = mhl_adult_passengers
            trip_check_data.mhl_child_passengers = mhl_child_passengers
            trip_check_data.mhl_adult_amount = mhl_adult_amount
            trip_check_data.mhl_child_amount = mhl_child_amount
            trip_check_data.trip_verified = trip_verified
            trip_check_data.trip_verified_time = trip_verified_time
            user_data = User.objects.get(id=request.session['user_id'])
            trip_check_data.trip_verify_by = user_data
            trip_check_data.service_operated_date = service_operated_date
            trip_check_data.updated_by = user_data
            trip_check_data.trip_end = trip_end
            trip_check_data.save()
            messages.success(request, 'Trip check updated successfully!!')
            return redirect("app:trip_end_add")
        except Exception as e:
            print(e)
            messages.error(request, 'Trip check updated failed!!')
            return redirect("app:trip_end_add")
    else:
        trip_unqiue_no = ''
        if request.session['user_type'] == 'PSG UP THADVAI':
            trip_unqiue_no = TripStatistics.objects.filter(Q(status=0) | Q(status=1)).filter(~Q(trip_verified=True)).filter(entry_type='up').values_list('unique_code', flat=True).distinct()
        return render(request, 'trip_statistics/trip_end/add.html',
                      {'trip_unqiue_no': trip_unqiue_no})


@custom_login_required
def out_depot_buses_receive_list(request):
    if request.session['user_type'] == 'BUS RECEIVING':
        out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects.filter(~Q(status=2) &
                                                                               Q(out_depot_bus_reporting_depot=
                                                                                 request.session['depot_id']))
        return render(request, 'out_depot_buses/out_depot_vehicle_receive/list.html',
                      {"out_depot_vehicle_receive_data": out_depot_vehicle_receive_data})
    out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects.filter(~Q(status=2))
    return render(request, 'out_depot_buses/out_depot_vehicle_receive/list.html',
                  {'out_depot_vehicle_receive_data': out_depot_vehicle_receive_data})


# @custom_login_required
# def out_depot_buses_receive_form(request):
#     try:
#         special_bus_data = SpecialBusDataEntry.objects.filter(~Q(status=2))
#         return render(request, 'out_depot_buses/out_depot_vehicle_receive/add.html',
#                       {'special_bus_numbers_data': special_bus_data})
#     except Exception as e:
#         print(e)


@custom_login_required
def search_special_bus_data(request):
    if request.method == "POST":
        bus_number = request.POST.get('bus_number')
        if bus_number:
            vehicle_detail = VehicleDetails.objects.get(bus_number=bus_number)
            bus_number_data = SpecialBusDataEntry.objects.get(bus_number=vehicle_detail)
    if request.session['user_type'] == 'BUS RECEIVING':
        depot_data = Depot.objects.filter(id=request.session['depot_id'])
        special_bus_data = SpecialBusDataEntry.objects.filter(
            Q(special_bus_reporting_depot=depot_data[0]) & ~Q(status=2))
        already_received_bus_numbers = OutDepotVehicleReceive.objects.values_list('bus_number__bus_number', flat=True)
        special_bus_data = special_bus_data.exclude(bus_number__bus_number__in=already_received_bus_numbers)
    else:
        special_bus_data = SpecialBusDataEntry.objects.filter(~Q(status=2))
        already_received_bus_numbers = OutDepotVehicleReceive.objects.values_list('bus_number__bus_number', flat=True)
        special_bus_data = special_bus_data.exclude(bus_number__bus_number__in=already_received_bus_numbers)
    # special_bus_numbers_data = SpecialBusDataEntry.objects.filter(~Q(status=2))
    return render(request, 'out_depot_buses/out_depot_vehicle_receive/add.html',
                  {'special_bus_data': bus_number_data, 'special_bus_numbers_data': special_bus_data})


@custom_login_required
def out_depot_buses_receive_add(request):
    if request.session['user_type'] == 'BUS RECEIVING':
        depot_data = Depot.objects.filter(id=request.session['depot_id'])
        special_bus_data = SpecialBusDataEntry.objects.filter(
            Q(special_bus_reporting_depot=depot_data[0]) & ~Q(status=2))
        already_received_bus_numbers = OutDepotVehicleReceive.objects.values_list('bus_number__bus_number', flat=True)
        special_bus_data = special_bus_data.exclude(bus_number__bus_number__in=already_received_bus_numbers)
    else:
        special_bus_data = SpecialBusDataEntry.objects.filter(~Q(status=2))
        already_received_bus_numbers = OutDepotVehicleReceive.objects.values_list('bus_number__bus_number', flat=True)
        special_bus_data = special_bus_data.exclude(bus_number__bus_number__in=already_received_bus_numbers)
    if request.method == "POST":
        bus_number = request.POST.get('out_depot_vehicle_receive_bus_number')
        unique_no = request.POST.get('unique_no')
        new_log_sheet_no = request.POST.get('new_log_sheet_no')
        hsd_top_oil_liters = request.POST.get('hsd_top_oil_liters')
        mts_no = request.POST.get('mts_no')
        bus_reported_date = request.POST.get('bus_reported_date')
        bus_reported_time = request.POST.get('bus_reported_time')
        out_depot_buses_receive_status = 0
        try:
            out_depot_buses_receive_unique_count = OutDepotVehicleReceive.objects.filter(unique_no=unique_no)
            if out_depot_buses_receive_unique_count.exists():
                messages.error(request, 'Unique number already exists!!')
                return render(request, 'out_depot_buses/out_depot_vehicle_receive/add.html',
                              {'special_bus_numbers_data': special_bus_data})
            vehicle_detail_data = VehicleDetails.objects.get(bus_number=bus_number)
            special_bus_data = SpecialBusDataEntry.objects.get(bus_number=vehicle_detail_data)
            out_depot_bus_sending_depot = Depot.objects.get(id=special_bus_data.special_bus_sending_depot.id)
            out_depot_bus_reporting_depot = Depot.objects.get(id=special_bus_data.special_bus_reporting_depot.id)
            user_data = User.objects.get(id=request.session['user_id'])
            out_depot_buses_receive_detail = OutDepotVehicleReceive.objects.create(bus_number=vehicle_detail_data,
                                                                                   special_bus_data_entry=special_bus_data,
                                                                                   unique_no=unique_no,
                                                                                   new_log_sheet_no=new_log_sheet_no,
                                                                                   hsd_top_oil_liters=hsd_top_oil_liters,
                                                                                   mts_no=mts_no,
                                                                                   bus_reported_date=bus_reported_date,
                                                                                   bus_reported_time=bus_reported_time,
                                                                                   created_by=user_data,
                                                                                   status=out_depot_buses_receive_status,
                                                                                   out_depot_bus_sending_depot=out_depot_bus_sending_depot,
                                                                                   out_depot_bus_reporting_depot=out_depot_bus_reporting_depot
                                                                                   )
            out_depot_buses_receive_detail.save()
            messages.success(request, 'Out Depot Vehicle Receive Details saved Successfully')
        except Exception as e:
            print(e)
            messages.error(request, 'Out Depot Vehicle Receive Details Creation Failed!!')
        return redirect("app:out_depot_buses_receive_list")

    if not special_bus_data.exists():
        messages.error(request, "No special bus numbers left to show and receive.")
        return render(request, 'out_depot_buses/out_depot_vehicle_receive/add.html', {})
    try:
        return render(request, 'out_depot_buses/out_depot_vehicle_receive/add.html',
                      {'special_bus_numbers_data': special_bus_data})
    except Exception as e:
        print(e)
    # return render(request, 'out_depot_buses/out_depot_vehicle_receive/add.html', {})


def own_depot_bus_details_entry_list(request):
    if request.session['user_type'] == 'BUS RECEIVING':
        own_depot_bus_detail_entry_data = OwnDepotBusDetailsEntry.objects.filter(~Q(status=2)
                                                                                 & Q(depot=request.session['depot_id']))
        return render(request, 'own_depot_buses/own_depot_bus_details_entry/list.html',
                      {"own_depot_bus_detail_entry_data": own_depot_bus_detail_entry_data})
    own_depot_bus_detail_entry_data = OwnDepotBusDetailsEntry.objects.filter(~Q(status=2))
    return render(request, 'own_depot_buses/own_depot_bus_details_entry/list.html',
                  {'own_depot_bus_detail_entry_data': own_depot_bus_detail_entry_data})


def own_depot_bus_details_entry_add(request):
    # vehicle_details = VehicleDetails.objects.filter(depot=request.session['depot_id']).values('id', 'bus_number')
    if request.session['user_type'] == 'BUS RECEIVING':
        vehicle_details = VehicleDetails.objects.filter(depot=request.session['depot_id'])
        already_entered_bus_numbers = OwnDepotBusDetailsEntry.objects.values_list('bus_number__bus_number', flat=True)
        vehicle_details = vehicle_details.exclude(bus_number__in=already_entered_bus_numbers)
    else:
        vehicle_details = VehicleDetails.objects.filter(~Q(status=2))
        already_entered_bus_numbers = OwnDepotBusDetailsEntry.objects.values_list('bus_number__bus_number', flat=True)
        vehicle_details = vehicle_details.exclude(bus_number__in=already_entered_bus_numbers)
    if request.method == "POST":
        bus_number = request.POST.get('bus_number')
        unique_no = request.POST.get('unique_no')
        bus_type = request.POST.get('bus_type')
        log_sheet_no = request.POST.get('log_sheet_no')
        driver1_name = request.POST.get('driver1_name')
        driver1_phone_number = request.POST.get('driver1_phone_number')
        driver1_staff_no = request.POST.get('driver1_staff_no')
        driver2_name = request.POST.get('driver2_name')
        driver2_phone_number = request.POST.get('driver2_phone_number')
        driver2_staff_no = request.POST.get('driver2_staff_no')
        incharge_name = request.POST.get('incharge_name')
        incharge_phone_number = request.POST.get('incharge_phone_number')
        status = 0
        try:
            own_depot_buses_entry_unique_count = OwnDepotBusDetailsEntry.objects.filter(unique_no=unique_no)
            if own_depot_buses_entry_unique_count.exists():
                messages.error(request, 'Unique number already exists!!')
                return render(request, 'own_depot_buses/own_depot_bus_details_entry/add.html', )
            vehicle_details = VehicleDetails.objects.get(bus_number=bus_number)
            if vehicle_details:
                depot_data = Depot.objects.get(id=vehicle_details.depot.id)
                user_data = User.objects.get(id=request.session['user_id'])
                own_depot_bus_detail_entry = OwnDepotBusDetailsEntry.objects.create(bus_number=vehicle_details,
                                                                                    bus_type=bus_type,
                                                                                    unique_no=unique_no,
                                                                                    log_sheet_no=log_sheet_no,
                                                                                    driver1_name=driver1_name,
                                                                                    driver1_phone_number=driver1_phone_number,
                                                                                    driver2_name=driver2_name,
                                                                                    driver2_phone_number=driver2_phone_number,
                                                                                    status=status,
                                                                                    created_by=user_data,
                                                                                    depot=depot_data,
                                                                                    driver1_staff_no=driver1_staff_no,
                                                                                    driver2_staff_no=driver2_staff_no,
                                                                                    incharge_name=incharge_name,
                                                                                    incharge_phone_number=incharge_phone_number
                                                                                    )
                own_depot_bus_detail_entry.save()
                messages.success(request, 'Own Depot Bus Detail Entry Saved Successfully')
            else:
                messages.error(request, 'Own Depot Bus Detail Entry Creation Failed, Provide Valid Bus Number!!')
                return redirect("app:own_depot_bus_details_entry_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Own Depot Bus Detail Entry Creation Failed!!')
        return redirect("app:own_depot_bus_details_entry_list")

    if not vehicle_details.exists():
        messages.error(request, "No bus numbers left to entry and withdraw.")
        return render(request, 'own_depot_buses/own_depot_bus_details_entry/add.html', {})
    try:
        return render(request, 'own_depot_buses/own_depot_bus_details_entry/add.html',
                      {'vehicle_details': vehicle_details})
    except Exception as e:
        print(e)



@custom_login_required
def own_depot_bus_details_entry_edit(request):
    own_depot_bus_details_entry_id = request.GET.get('id')
    if own_depot_bus_details_entry_id:
        own_depot_bus_details_entry_data = OwnDepotBusDetailsEntry.objects.get(id=own_depot_bus_details_entry_id)
        bus_number_list = []
        if own_depot_bus_details_entry_data.bus_number:
            bus_number_list.append(own_depot_bus_details_entry_data.bus_number.bus_number)
        vehicle_details = VehicleDetails.objects.filter(depot=request.session['depot_id']).values('id', 'bus_number')
        return render(request, 'own_depot_buses/own_depot_bus_details_entry/edit.html',
                      {"own_depot_bus_details_entry_data": own_depot_bus_details_entry_data,
                       'bus_number_list': bus_number_list, 'vehicle_details': vehicle_details})
    else:
        return render(request, 'own_depot_buses/own_depot_bus_details_entry/edit.html', {})


@custom_login_required
def own_depot_bus_details_entry_update(request):
    own_depot_bus_details_entry_id = request.POST.get('id')
    bus_number = request.POST.get('bus_number')
    unique_no = request.POST.get('unique_no')
    bus_type = request.POST.get('bus_type')
    log_sheet_no = request.POST.get('log_sheet_no')
    driver1_name = request.POST.get('driver1_name')
    driver1_phone_number = request.POST.get('driver1_phone_number')
    driver1_staff_no = request.POST.get('driver1_staff_no')
    driver2_name = request.POST.get('driver2_name')
    driver2_phone_number = request.POST.get('driver2_phone_number')
    driver2_staff_no = request.POST.get('driver2_staff_no')
    incharge_name = request.POST.get('incharge_name')
    incharge_phone_number = request.POST.get('incharge_phone_number')
    status = 0
    if own_depot_bus_details_entry_id:
        try:
            # own_depot_buses_entry_unique_count = OwnDepotBusDetailsEntry.objects.filter(unique_no=unique_no)
            # if own_depot_buses_entry_unique_count.exists():
            #     messages.error(request, 'Unique number already exists!update failed!')
            #     redirect("app:own_depot_bus_details_entry_list")
            own_depot_bus_details_entry_data = OwnDepotBusDetailsEntry.objects.get(id=own_depot_bus_details_entry_id)
            # vehicle_details_id = VehicleDetails.objects.get(bus_number=bus_number)
            # own_depot_bus_details_entry_data.bus_number = vehicle_details_id
            # own_depot_bus_details_entry_data.unique_no = unique_no
            own_depot_bus_details_entry_data.bus_type = bus_type
            own_depot_bus_details_entry_data.log_sheet_no = log_sheet_no
            own_depot_bus_details_entry_data.driver1_name = driver1_name
            own_depot_bus_details_entry_data.driver1_phone_number = driver1_phone_number
            own_depot_bus_details_entry_data.driver1_staff_no = driver1_staff_no
            own_depot_bus_details_entry_data.driver2_name = driver2_name
            own_depot_bus_details_entry_data.driver2_phone_number = driver2_phone_number
            own_depot_bus_details_entry_data.driver2_staff_no = driver2_staff_no
            own_depot_bus_details_entry_data.incharge_name = incharge_name
            own_depot_bus_details_entry_data.incharge_phone_number = incharge_phone_number
            own_depot_bus_details_entry_data.status = status
            vehicle_details = VehicleDetails.objects.get(bus_number=bus_number)
            depot_data = Depot.objects.get(id=vehicle_details.depot.id)
            own_depot_bus_details_entry_data.depot = depot_data
            user_data = User.objects.get(id=request.session['user_id'])
            own_depot_bus_details_entry_data.updated_by = user_data
            own_depot_bus_details_entry_data.save()
            messages.success(request, 'Own Depot Bus Detail Entry updated successfully!!')
            return redirect("app:own_depot_bus_details_entry_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Own Depot Bus Detail Entry update  failed!!')
            return redirect("app:own_depot_bus_details_entry_list")
    else:
        return redirect("app:own_depot_bus_details_entry_list")


def own_depot_bus_withdraw_list(request):
    if request.session['user_type'] == 'BUS RECEIVING':
        own_depot_bus_withdraw_data = OwnDepotBusWithdraw.objects.filter(~Q(status=2) &
                                                                         Q(depot=request.session['depot_id']))
        return render(request, 'own_depot_buses/own_depot_bus_withdraw/list.html',
                      {"own_depot_bus_withdraw_data": own_depot_bus_withdraw_data})
    own_depot_bus_withdraw_data = OwnDepotBusWithdraw.objects.filter(~Q(status=2))
    return render(request, 'own_depot_buses/own_depot_bus_withdraw/list.html',
                  {'own_depot_bus_withdraw_data': own_depot_bus_withdraw_data})


def own_depot_bus_withdraw_add(request):
    if request.method == "POST":
        bus_number = request.POST.get('bus_number')
        own_depot_bus_withdraw_status = 0
        try:
            # vehicle_details = VehicleDetails.objects.filter(bus_number=bus_number).filter(depot=request.session['depot_id'])
            # if vehicle_details.count() == 0:
            #     messages.error(request, 'Bus Number not matched with depot')
            #     return redirect("app:own_depot_bus_withdraw_add")

            own_depo_entry_data = OwnDepotBusDetailsEntry.objects.filter(bus_number__bus_number=bus_number)
            if own_depo_entry_data.count() == 0:
                messages.error(request, 'Bus Number not matched with any detail entry')
                return redirect("app:own_depot_bus_withdraw_list")
            own_depo_withdraw_data = OwnDepotBusWithdraw.objects.filter(bus_number=bus_number)
            if own_depo_withdraw_data.count() != 0:
                messages.error(request, 'Already Bus Withdraw')
                return redirect("app:own_depot_bus_withdraw_list")
            if own_depo_entry_data[0].depot.id != request.session['depot_id']:
                messages.error(request, 'Unable to Withdraw Bus')
                return redirect("app:own_depot_bus_withdraw_list")

            depot_data = Depot.objects.get(id=own_depo_entry_data[0].depot.id)
            user_data = User.objects.get(id=request.session['user_id'])
            own_depot_bus_withdraw = OwnDepotBusWithdraw.objects.create(bus_number=bus_number,
                                                                        status=own_depot_bus_withdraw_status,
                                                                        created_by=user_data, depot=depot_data)
            own_depot_bus_withdraw.save()
            messages.success(request, 'Own Depot Bus Withdraw Saved Successfully')
        except Exception as e:
            print(e)
            messages.error(request, 'Own Depot Bus withdraw Creation Failed!!')
        return redirect("app:own_depot_bus_withdraw_list")

    return render(request, 'own_depot_buses/own_depot_bus_withdraw/add.html', {})


@custom_login_required
def own_depot_bus_withdraw_edit(request):
    own_depot_bus_withdraw_id = request.GET.get('id')
    if own_depot_bus_withdraw_id:
        own_depot_bus_withdraw_data = OwnDepotBusWithdraw.objects.get(id=own_depot_bus_withdraw_id)
        return render(request, 'own_depot_buses/own_depot_bus_withdraw/edit.html',
                      {"own_depot_bus_withdraw_data": own_depot_bus_withdraw_data})
    else:
        return render(request, 'own_depot_buses/own_depot_bus_withdraw/edit.html', {})


@custom_login_required
def own_depot_bus_withdraw_update(request):
    own_depot_bus_withdraw_id = request.POST.get('id')
    bus_number = request.POST.get('bus_number')
    status = 0
    if own_depot_bus_withdraw_id:
        try:
            own_depot_bus_withdraw_data = OwnDepotBusWithdraw.objects.get(id=own_depot_bus_withdraw_id)
            own_depot_bus_withdraw_data.bus_number = bus_number
            own_depot_bus_withdraw_data.status = status
            vehicle_details = VehicleDetails.objects.get(bus_number=bus_number)
            depot_data = Depot.objects.get(id=vehicle_details.depot.id)
            own_depot_bus_withdraw_data.depot = depot_data
            user_data = User.objects.get(id=request.session['user_id'])
            own_depot_bus_withdraw_data.updated_by = user_data
            own_depot_bus_withdraw_data.save()
            messages.success(request, 'Own Depot Bus Withdraw updated successfully!!')
            return redirect("app:own_depot_bus_withdraw_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Own Depot Bus Withdraw update  failed!!')
            return redirect("app:own_depot_bus_withdraw_list")
    else:
        return redirect("app:own_depot_bus_withdraw_list")


@custom_login_required
def out_depot_vehicle_send_back_list(request):
    out_depot_vehicle_send_back_data = OutDepotVehicleSentBack.objects.filter(~Q(status=2))
    return render(request, 'out_depot_buses/out_depot_vehicle_send_back/list.html',
                  {'out_depot_vehicle_send_back_data': out_depot_vehicle_send_back_data})


@custom_login_required
def out_depot_vehicle_send_back_add(request):
    if request.method == "POST":
        unique_no = request.POST.get('out_depot_vehicle_receive_unique_no')
        bus_number = request.POST.get('out_depot_vehicle_receive_bus_number')
        log_sheet_no = request.POST.get('out_depot_send_back_log_sheet_no')
        out_depot_buses_send_back_status = 0
        try:
            special_bus_data = SpecialBusDataEntry.objects.filter(Q(log_sheet_no=log_sheet_no) &
                                                                  Q(bus_number__bus_number=bus_number) &
                                                                  Q(special_bus_reporting_depot_id=
                                                                    request.session['depot_id']))
            if special_bus_data.count() == 0:
                messages.error(request, 'Parent Log Sheet number not matched!!')
                return redirect("app:out_depot_vehicle_send_back_add")
            user_data = User.objects.get(id=request.session['user_id'])
            out_depo_buse_send_back_detail = OutDepotVehicleSentBack.objects.create(unique_no=unique_no,
                                                                                    bus_number=bus_number,
                                                                                    log_sheet_no=log_sheet_no,
                                                                                    special_bus_data_entry=
                                                                                    special_bus_data[0],
                                                                                    created_by=user_data,
                                                                                    status=
                                                                                    out_depot_buses_send_back_status)
            out_depo_buse_send_back_detail.save()
            messages.success(request, 'Out Depot Vehicle Send Back Details saved Successfully')
        except Exception as e:
            print(e)
            messages.error(request, 'Out Depot Vehicle Send Back Details Creation Failed!!')
        return redirect("app:out_depot_vehicle_send_back_list")
    try:
        if request.session['user_type'] == 'BUS RECEIVING':
            depot_data = Depot.objects.filter(id=request.session['depot_id'])
            out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects \
                .filter(Q(out_depot_bus_reporting_depot=depot_data[0]) & ~Q(status=2))
            already_send_back_bus_numbers = OutDepotVehicleSentBack.objects.values_list('unique_no', flat=True)
            out_depot_vehicle_receive_data = out_depot_vehicle_receive_data.exclude(unique_no__in=
                                                                                    already_send_back_bus_numbers)
            return render(request, 'out_depot_buses/out_depot_vehicle_send_back/add.html',
                          {'out_depot_vehicle_receive_data': out_depot_vehicle_receive_data})
        else:
            out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects.filter(~Q(status=2))
            already_send_back_bus_numbers = OutDepotVehicleSentBack.objects.values_list('unique_no', flat=True)
            out_depot_vehicle_receive_data = out_depot_vehicle_receive_data.exclude(unique_no__in=
                                                                                    already_send_back_bus_numbers)
            return render(request, 'out_depot_buses/out_depot_vehicle_send_back/add.html',
                          {'out_depot_vehicle_receive_data': out_depot_vehicle_receive_data})
    except Exception as e:
        print(e)
        return render(request, 'out_depot_buses/out_depot_vehicle_send_back/add.html', {})


def hsd_oil_submission_list(request):
    hsd_oil_submission_data = HsdOilSubmission.objects.filter(~Q(status=2))
    return render(request, 'hsd_oil_submission/list.html',
                  {'hsd_oil_submission_data': hsd_oil_submission_data})


@custom_login_required
def hsd_oil_submission_form(request):
    return render(request, 'hsd_oil_submission/add.html')


@custom_login_required
def search_unique_no_bus_no_special_bus_data(request):
    if request.method == "POST":
        unique_no_bus_no = request.POST.get('unique_no_bus_no')
        if unique_no_bus_no.isdigit():
            try:
                out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects.get(unique_no=unique_no_bus_no)
                special_bus_data = out_depot_vehicle_receive_data.special_bus_data_entry
                return render(request, 'hsd_oil_submission/add.html', {'special_bus_data': special_bus_data,
                                                                       'unique_bus_no': unique_no_bus_no})
            except Exception as e:
                print(e)
                messages.error(request, 'Unique number not matching please try again')
                return redirect("app:hsd_oil_submission_add")
        else:
            try:
                vehicle_details = VehicleDetails.objects.get(bus_number=unique_no_bus_no)
                special_bus_data = SpecialBusDataEntry.objects.get(bus_number=vehicle_details)
                return render(request, 'hsd_oil_submission/add.html', {'special_bus_data': special_bus_data,
                                                                       'unique_bus_no': unique_no_bus_no})
            except Exception as e:
                print(e)
                messages.error(request, 'Bus number not matching please try again')
                return redirect("app:hsd_oil_submission_add")
    else:
        return redirect("app:hsd_oil_submission_add")


@custom_login_required
def hsd_oil_submission_add(request):
    if request.method == "POST":
        bus_number = request.POST.get('hsd_oil_bus_number')
        hsd_liters = request.POST.get('hsd_top_oil_liters')
        mts_no = request.POST.get('mts_no')
        point_name = request.POST.get('point_name')
        unique_no_bus_no = request.POST.get('unique_bus_no')
        shift = request.POST.get('shift')
        hsd_oil_submission_status = 0
        try:
            vehicle_detail_data = VehicleDetails.objects.get(bus_number=bus_number)
            special_bus_data = SpecialBusDataEntry.objects.get(bus_number=vehicle_detail_data)
            user_data = User.objects.get(id=request.session['user_id'])
            hsd_oil_submission_detail = HsdOilSubmission.objects.create(special_bus_data_entry=special_bus_data,
                                                                        hsd_liters=hsd_liters,
                                                                        mts_no=mts_no, point_name=point_name,
                                                                        created_by=user_data,
                                                                        unique_no_bus_no=unique_no_bus_no,
                                                                        status=hsd_oil_submission_status,
                                                                        shift=shift)
            hsd_oil_submission_detail.save()
            messages.success(request, 'HSD Oil Submission Details saved Successfully')
        except Exception as e:
            print(e)
            messages.error(request, 'HSD Oil Submission Details Creation Failed!!')
        return redirect("app:hsd_oil_submission_list")

    return render(request, 'hsd_oil_submission/add.html', {})


@custom_login_required
def buses_on_hand_list(request):
    buses_on_hand_data = BusesOnHand.objects.filter(~Q(status=2))
    return render(request, 'buses_on_hand/list.html',
                  {'buses_on_hand_data': buses_on_hand_data})


@custom_login_required
def buses_on_hand_add(request):
    if request.method == "POST":
        unique_code = request.POST.get('unique_code')
        point_name = request.POST.get('point_name')
        bus_in_out = request.POST.get('bus_in_out')
        buses_on_hand_status = 0
        try:
            out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects.get(unique_no=unique_code)
            special_bus_data = out_depot_vehicle_receive_data.special_bus_data_entry
            point_name_data = PointData.objects.get(id=point_name)
            user_data = User.objects.get(id=request.session['user_id'])
            buses_on_hand_detail = BusesOnHand.objects.create(unique_code=unique_code, status=buses_on_hand_status,
                                                              special_bus_data_entry=special_bus_data,
                                                              created_by=user_data, bus_in_out=bus_in_out,
                                                              point_name=point_name_data)
            buses_on_hand_detail.save()
            messages.success(request, 'Buses on hand Details saved Successfully')
        except Exception as e:
            print(e)
            messages.error(request, 'Buses On Hand Details Creation Failed!!')
        return redirect("app:buses_on_hand_list")
    try:
        point_name_data = PointData.objects.filter(Q(status=0) | Q(status=1))
        return render(request, 'buses_on_hand/add.html', {"point_name_data": point_name_data})
    except Exception as e:
        print(e)
        return render(request, 'buses_on_hand/add.html', {})


@custom_login_required
def summary_sending_buses_list(request):
    summary_depot_result = []
    summary_depot_data = Depot.objects.filter(~Q(status=2))
    for summary_depot in summary_depot_data:
        no_of_buses_allotted = summary_depot.buses_allotted
        no_of_buses_dispatched = SpecialBusDataEntry.objects.filter(special_bus_sending_depot=summary_depot).count()
        if summary_depot.buses_allotted != 0:
            no_of_buses_due = summary_depot.buses_allotted - no_of_buses_dispatched
        else:
            no_of_buses_due = 0

        no_of_buses_reached = OutDepotVehicleReceive.objects.filter(out_depot_bus_sending_depot=summary_depot).count()

        if no_of_buses_dispatched != 0:
            no_of_buses_not_reached = no_of_buses_dispatched - no_of_buses_reached
        else:
            no_of_buses_not_reached = 0

        summary_depot_result.append({
            'depot_id': summary_depot.id,
            'depot_name': summary_depot.name,
            'buses_allotted': no_of_buses_allotted,
            'buses_dispatched': no_of_buses_dispatched,
            'buses_due': no_of_buses_due,
            'buses_reached': no_of_buses_reached,
            'buses_not_reached': no_of_buses_not_reached,
        })
    return render(request, 'reports/summary_sending_buses_list.html',
                  {'summary_depot_result': summary_depot_result})


@custom_login_required
def buses_dispatched_list(request):
    depot_id = request.GET.get('id')
    depot_data = Depot.objects.get(id=depot_id)
    buses_dispatched_data = SpecialBusDataEntry.objects.filter(~Q(status=2)).filter(special_bus_sending_depot=depot_id)
    return render(request, 'reports/buses_dispatched_list.html',
                  {'buses_dispatched_data': buses_dispatched_data, 'depot_data': depot_data})


@custom_login_required
def buses_dispatched_display_details(request):
    bus_number = request.GET.get('id')
    if bus_number:
        buses_dispatched_display_data = SpecialBusDataEntry.objects.get(bus_number=bus_number)
        date_part = buses_dispatched_display_data.created_at.date()
        time_part = buses_dispatched_display_data.created_at.time()
    try:
        return render(request, 'reports/buses_dispatched_display_details.html',
                      {"buses_dispatched_display_data": buses_dispatched_display_data, "date_part": date_part,
                       "time_part": time_part})
    except Exception as e:
        print(e)
        return render(request, 'reports/buses_dispatched_display_details.html', {})


@custom_login_required
def buses_reached_list(request):
    depot_id = request.GET.get('id')
    depot_data = Depot.objects.get(id=depot_id)
    buses_reached_data = OutDepotVehicleReceive.objects.filter(~Q(status=2)).filter(
        out_depot_bus_sending_depot=depot_id)
    return render(request, 'reports/buses_reached_list.html',
                  {'buses_reached_data': buses_reached_data, 'depot_data': depot_data})


@custom_login_required
def buses_reached_display_details(request):
    bus_number = request.GET.get('id')
    if bus_number:
        buses_reached_display_data = OutDepotVehicleReceive.objects.get(bus_number=bus_number)
    try:
        return render(request, 'reports/buses_reached_display_details.html',
                      {"buses_reached_display_data": buses_reached_display_data})
    except Exception as e:
        print(e)
        return render(request, 'reports/buses_reached_display_details.html', {})


@custom_login_required
def buses_not_reached_list(request):
    depot_id = request.GET.get('id')
    buses_reached_data = OutDepotVehicleReceive.objects.values_list('special_bus_data_entry__id', flat=True). \
        filter(~Q(status=2)).filter(out_depot_bus_sending_depot=depot_id)
    buses_not_reached_data = SpecialBusDataEntry.objects.filter(~Q(status=2)).exclude(id__in=buses_reached_data). \
        filter(special_bus_sending_depot=depot_id)
    depot_data = Depot.objects.get(id=depot_id)

    return render(request, 'reports/buses_not_reached_list.html',
                  {'buses_not_reached_data': buses_not_reached_data, 'depot_data': depot_data})


@custom_login_required
def buses_not_reached_display_details(request):
    bus_number = request.GET.get('id')
    if bus_number:
        buses_not_reached_display_data = SpecialBusDataEntry.objects.get(bus_number=bus_number)
        date_part = buses_not_reached_display_data.created_at.date()
        time_part = buses_not_reached_display_data.created_at.time()
    try:
        return render(request, 'reports/buses_not_reached_display_details.html',
                      {"buses_not_reached_display_data": buses_not_reached_display_data, "date_part": date_part,
                       "time_part": time_part})
    except Exception as e:
        print(e)
        return render(request, 'reports/buses_not_reached_display_details.html', {})


@custom_login_required
def buses_reached_display_details(request):
    bus_number = request.GET.get('id')
    if bus_number:
        buses_reached_display_data = SpecialBusDataEntry.objects.get(bus_number=bus_number)
        date_part = buses_reached_display_data.created_at.date()
        time_part = buses_reached_display_data.created_at.time()
        bus_reported = OutDepotVehicleReceive.objects.get(special_bus_data_entry=buses_reached_display_data.id)
        bus_reported_date = bus_reported.bus_reported_date
        bus_reported_time = bus_reported.bus_reported_time
    try:
        return render(request, 'reports/buses_reached_display_details.html',
                      {"buses_reached_display_data": buses_reached_display_data, "date_part": date_part,
                       "time_part": time_part, "bus_reported_date": bus_reported_date,
                       "bus_reported_time": bus_reported_time})
    except Exception as e:
        print(e)
        return render(request, 'reports/buses_reached_display_details.html', {})


@custom_login_required
def display_bus_details(request):
    bus_number = request.GET.get('id')
    if bus_number:
        display_bus_data = OutDepotVehicleReceive.objects.get(bus_number=bus_number)
    try:
        return render(request, 'reports/display_bus_details.html', {"display_bus_data": display_bus_data})
    except Exception as e:
        print(e)
        return render(request, 'reports/display_bus_details.html', {})


@custom_login_required
def search_depot_list(request):
    special_bus_sending_depot = SpecialBusDataEntry.objects.values('special_bus_sending_depot__id',
                                                                   'special_bus_sending_depot__name').distinct()
    if request.method == "POST":
        performance_depot_result = []
        depot_name = request.POST.get('depot_name')
        out_depot_bus_reporting_depot = OutDepotVehicleReceive.objects.values_list("out_depot_bus_reporting_depot",
                                                                                   flat=True).filter(
            out_depot_bus_sending_depot=depot_name).distinct()
        if len(out_depot_bus_reporting_depot) > 0:
            for reporting_Depot in out_depot_bus_reporting_depot:
                depot_info = Depot.objects.get(id=reporting_Depot)
                report_depot_id = depot_info.id
                report_depot_name = depot_info.name
                alloted_buses = OutDepotVehicleReceive.objects.filter(
                    out_depot_bus_reporting_depot=reporting_Depot).count()

                depot_points = PointData.objects.values_list('id', flat=True).filter(depot_name=reporting_Depot)

                no_of_trips_up_count = TripStatistics.objects.filter(entry_type='up').filter(
                    start_from_location__in=depot_points).count()
                no_of_trips_down_count = TripStatistics.objects.filter(entry_type='down').filter(
                    start_to_location__in=depot_points).count()

                no_of_trips_count = no_of_trips_up_count + no_of_trips_down_count

                total_earnings_up = TripStatistics.objects.filter(entry_type='up').filter(
                    start_from_location__in=depot_points).aggregate(
                    total_ticket_amount_sum=Coalesce(Sum('total_ticket_amount'), 0),
                    mhl_adult_amount_sum=Coalesce(Sum('mhl_adult_amount'), 0),
                    mhl_child_amount_sum=Coalesce(Sum('mhl_child_amount'), 0)
                )

                total_earnings_down = TripStatistics.objects.filter(entry_type='down').filter(
                    start_to_location__in=depot_points).aggregate(
                    total_ticket_amount_sum=Coalesce(Sum('total_ticket_amount'), 0),
                    mhl_adult_amount_sum=Coalesce(Sum('mhl_adult_amount'), 0),
                    mhl_child_amount_sum=Coalesce(Sum('mhl_child_amount'), 0)
                )

                total_passenger_up = TripStatistics.objects.filter(entry_type='up').filter(
                    start_from_location__in=depot_points).aggregate(
                    total_adult_passengers=Coalesce(Sum('total_adult_passengers'), 0),
                    total_child_passengers=Coalesce(Sum('total_child_passengers'), 0),
                    mhl_adult_passengers=Coalesce(Sum('mhl_adult_passengers'), 0),
                    mhl_child_passengers=Coalesce(Sum('mhl_child_passengers'), 0)
                )

                total_passengers_down = TripStatistics.objects.filter(entry_type='down').filter(
                    start_to_location__in=depot_points).aggregate(
                    total_adult_passengers=Coalesce(Sum('total_adult_passengers'), 0),
                    total_child_passengers=Coalesce(Sum('total_child_passengers'), 0),
                    mhl_adult_passengers=Coalesce(Sum('mhl_adult_passengers'), 0),
                    mhl_child_passengers=Coalesce(Sum('mhl_child_passengers'), 0)
                )

                total_passengers = {
                    'total_adult_passengers': total_passenger_up['total_adult_passengers'] + total_passengers_down[
                        'total_adult_passengers'],
                    'total_child_passengers': total_passenger_up['total_child_passengers'] + total_passengers_down[
                        'total_child_passengers'],
                    'mhl_adult_passengers': total_passenger_up['mhl_adult_passengers'] + total_passengers_down[
                        'mhl_adult_passengers'],
                    'mhl_child_passengers': total_passenger_up['mhl_child_passengers'] + total_passengers_down[
                        'mhl_child_passengers']
                }

                total_passenger_count = total_passengers['total_adult_passengers'] + total_passengers[
                    'total_child_passengers'] + \
                                        total_passengers['mhl_adult_passengers'] + total_passengers[
                                            'mhl_child_passengers']

                total_earnings_count = total_earnings_up['total_ticket_amount_sum'] + total_earnings_up[
                    'mhl_adult_amount_sum'] + total_earnings_up['mhl_child_amount_sum'] + total_earnings_down[
                                           'total_ticket_amount_sum'] + total_earnings_down['mhl_adult_amount_sum'] + \
                                       total_earnings_down['mhl_child_amount_sum']

                performance_depot_result.append({
                    'depot_id': report_depot_id,
                    'depot_name': report_depot_name,
                    'buses_allotted': alloted_buses,
                    'no_of_trips_count': no_of_trips_count,
                    'no_of_trips_up_count': no_of_trips_up_count,
                    'no_of_trips_down_count': no_of_trips_down_count,
                    'total_passenger_count': total_passenger_count,
                    'total_earnings_count': total_earnings_count,
                })

            # messages.error(request, 'Selected Unique No has no TripStatistic details!!')
            return render(request, 'reports/performance_of_buses_list.html',
                          {'performance_depot_result': performance_depot_result,
                           'special_bus_sending_depot': special_bus_sending_depot})
        else:
            return render(request, 'reports/performance_of_buses_list.html',
                          {'special_bus_sending_depot': special_bus_sending_depot})
    else:
        return render(request, 'reports/performance_of_buses_list.html',
                      {'special_bus_sending_depot': special_bus_sending_depot})


def display_operating_depot_list(request):
    operating_depot_name = request.GET.get('id')
    depot = Depot.objects.get(id=operating_depot_name)
    depot_name = depot.name

    out_depot_bus_reporting_depot = OutDepotVehicleReceive.objects.filter(
        out_depot_bus_reporting_depot=operating_depot_name)
    operating_details = []
    for out_depot_bus_reporting in out_depot_bus_reporting_depot:
        bus_number = VehicleDetails.objects.get(bus_number=out_depot_bus_reporting.bus_number.bus_number)
        unique_no = out_depot_bus_reporting.unique_no

        no_of_trips_up_count = TripStatistics.objects.filter(entry_type='up').filter(
            unique_code=unique_no).count()
        no_of_trips_down_count = TripStatistics.objects.filter(entry_type='down').filter(
            unique_code=unique_no).count()

        no_of_trips = no_of_trips_up_count + no_of_trips_down_count

        total_passengers = TripStatistics.objects.filter(unique_code=unique_no).aggregate(
            total_adult_passengers=Coalesce(Sum('total_adult_passengers'), 0),
            total_child_passengers=Coalesce(Sum('total_child_passengers'), 0),
            mhl_adult_passengers=Coalesce(Sum('mhl_adult_passengers'), 0),
            mhl_child_passengers=Coalesce(Sum('mhl_child_passengers'), 0)
        )
        total_passengers_count = total_passengers['total_adult_passengers'] + total_passengers[
            'total_child_passengers'] + total_passengers['mhl_adult_passengers'] + \
                                 total_passengers['mhl_child_passengers']

        total_earnings = TripStatistics.objects.filter(unique_code=unique_no).aggregate(
            total_ticket_amount=Coalesce(Sum('total_ticket_amount'), 0),
            mhl_adult_amount=Coalesce(Sum('mhl_adult_amount'), 0),
            mhl_child_amount=Coalesce(Sum('mhl_child_amount'), 0)
        )

        total_earnings_count = total_earnings['total_ticket_amount'] + total_earnings[
            'mhl_adult_amount'] + total_earnings['mhl_child_amount']

        operating_details.append({
            'bus_number': bus_number.bus_number,
            'unique_no': unique_no,
            'no_of_trips': no_of_trips,
            'no_of_trips_up_count': no_of_trips_up_count,
            'no_of_trips_down_count': no_of_trips_down_count,
            'total_passengers_count': total_passengers_count,
            'total_earnings_count': total_earnings_count,
        })

    return render(request, 'reports/display_operating_depot_list.html',
                  {'depot_name': depot_name, 'operating_details': operating_details})


def status_return_back_buses_list(request):
    status_return_back_buses = []
    status_return_back_buses_list = OutDepotVehicleReceive.objects.values_list('out_depot_bus_reporting_depot',
                                                                               flat=True).distinct()
    for status_return_back_bus in status_return_back_buses_list:
        operating_depot_name = Depot.objects.get(id=status_return_back_bus)

        no_of_buses_reporting = OutDepotVehicleReceive.objects. \
            filter(out_depot_bus_reporting_depot=status_return_back_bus).count()

        bus_number = OutDepotVehicleReceive.objects.filter(out_depot_bus_reporting_depot=status_return_back_bus) \
            .values_list('bus_number__bus_number', flat=True)

        no_of_buses_send_back = OutDepotVehicleSentBack.objects.filter(bus_number__in=bus_number).count()

        status_return_back_buses.append({
            'operating_depot_name': operating_depot_name.name,
            'no_of_buses_reporting': no_of_buses_reporting,
            'no_of_buses_send_back': no_of_buses_send_back,
        })

    return render(request, 'reports/status_return_back_buses_list.html',
                  {'status_return_back_buses': status_return_back_buses})


@custom_login_required
def buses_sending_back_list(request):
    buses_sending_back_data = OutDepotVehicleSentBack.objects.filter(~Q(status=2))
    return render(request, 'reports/buses_sending_back_list.html',
                  {'buses_sending_back_data': buses_sending_back_data})


@custom_login_required
def search_handling_bus_details_list(request):
    point_names = PointData.objects.filter(~Q(status=2))
    if request.method == "POST":
        point_name = request.POST.get('point_name')
        select_time_range = request.POST.get('select_time_range')
        point_names_result = []
        buses_on_hand_data = BusesOnHand.objects.filter(point_name=point_name).values_list('unique_code',
                                                                                           flat=True).distinct()
        if len(buses_on_hand_data) > 0:
            for buses_on_hand in buses_on_hand_data:

                buses_in_data = BusesOnHand.objects.filter(unique_code=buses_on_hand).filter(bus_in_out='in').latest(
                    'created_at')
                buses_created_in = buses_in_data.created_at
                entry_time_in = buses_created_in.astimezone(indian_timezone)
                check_time = entry_time_in.strftime("%H:%M:%S %p %Z")
                entry_time_present_date = datetime.datetime.now(
                    datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
                time_difference = entry_time_present_date - entry_time_in
                hours_difference = time_difference.total_seconds() / 3600

                buses_out_data = BusesOnHand.objects.filter(unique_code=buses_on_hand).filter(bus_in_out='out').latest(
                    'created_at')
                buses_created_out = buses_out_data.created_at

                if buses_created_in > buses_created_out:
                    if int(hours_difference) >= int(select_time_range):
                        unique_code = buses_on_hand

                        parent_depot = OutDepotVehicleReceive.objects.get(
                            special_bus_data_entry=buses_in_data.special_bus_data_entry)
                        parent_depot_name = parent_depot.out_depot_bus_sending_depot.name
                        bus_number = parent_depot.bus_number.bus_number
                        alloted_depot_name = parent_depot.out_depot_bus_reporting_depot.name

                        point_names_result.append({
                            'unique_code': unique_code,
                            'parent_depot_name': parent_depot_name,
                            'bus_number': bus_number,
                            'alloted_depot_name': alloted_depot_name,
                            'check_time': check_time,
                            'hours_difference': round(hours_difference)
                        })
            return render(request, 'reports/handling_bus_details.html',
                          {'point_names': point_names, 'point_names_result': point_names_result})
        else:
            return render(request, 'reports/handling_bus_details.html',
                          {'point_names': point_names})
    else:
        return render(request, 'reports/handling_bus_details.html',
                      {'point_names': point_names})


@custom_login_required
def display_unique_no_crew_details(request):
    unique_no = request.GET.get('id')
    unique_number_crew_details = OutDepotVehicleReceive.objects.get(unique_no=unique_no)
    return render(request, 'reports/display_unique_no_crew_details.html',
                  {'unique_number_crew_details': unique_number_crew_details})


@custom_login_required
def display_bus_no_crew_details(request):
    bus_no = request.GET.get('id')
    bus_data = VehicleDetails.objects.get(bus_number=bus_no)
    bus_number_crew_details = OutDepotVehicleReceive.objects.get(bus_number=bus_data)
    return render(request, 'reports/display_bus_no_crew_details.html',
                  {'bus_number_crew_details': bus_number_crew_details})


@custom_login_required
def search_bus_details(request):
    if request.method == "POST":
        unique_bus_no = request.POST.get('unique_bus_no')
        pattern = r'^[A-Z]{2}\d{2}[A-Z]\d{4}$'
        pattern_numeric = r'^\d+$'
        if re.match(pattern, unique_bus_no):
            bus_data = VehicleDetails.objects.get(bus_number=unique_bus_no)
            bus_number_crew_details = OutDepotVehicleReceive.objects.filter(bus_number=bus_data).first()
            return render(request, 'reports/search_bus_details.html',
                          {'search_bus_details_info': bus_number_crew_details})
        if re.match(pattern_numeric, unique_bus_no):
            print(unique_bus_no)
            unique_number_crew_details = OutDepotVehicleReceive.objects.filter(unique_no=unique_bus_no).first()
            return render(request, 'reports/search_bus_details.html',
                          {'search_bus_details_info': unique_number_crew_details})
    else:
        return render(request, 'reports/search_bus_details.html', {})


@custom_login_required
def search_route_wise_buses_to_list(request):
    point_names = PointData.objects.filter(~Q(status=2)).filter(~Q(point_name='Thadvai'))
    trip_point_result = []
    if request.method == "POST":

        point_name = request.POST.get('point_name')
        date = request.POST.get('date')
        given_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()

        trip_point_data = TripStatistics.objects.filter(entry_type='up').filter(
            start_to_location__point_name='Thadvai').filter(
            start_from_location=point_name).filter(trip_start__date=given_date).count()
        if trip_point_data > 0:
            # for trip_point in trip_point_data:
            point_name = PointData.objects.get(id=point_name)
            no_of_buses = trip_point_data
            total_passengers = TripStatistics.objects.filter(entry_type='up').filter(
                start_to_location__point_name='Thadvai').filter(
                start_from_location=point_name).filter(trip_start__date=given_date).aggregate(
                total_adult_passengers=Coalesce(Sum('total_adult_passengers'), 0),
                total_child_passengers=Coalesce(Sum('total_child_passengers'), 0),
                mhl_adult_passengers=Coalesce(Sum('mhl_adult_passengers'), 0),
                mhl_child_passengers=Coalesce(Sum('mhl_child_passengers'), 0)
            )
            total_passengers_count = total_passengers['total_adult_passengers'] + total_passengers[
                'total_child_passengers'] + total_passengers['mhl_adult_passengers'] + \
                                     total_passengers['mhl_child_passengers']

            total_earnings = TripStatistics.objects.filter(entry_type='up').filter(
                start_to_location__point_name='Thadvai').filter(
                start_from_location=point_name).filter(trip_start__date=given_date).aggregate(
                total_ticket_amount=Coalesce(Sum('total_ticket_amount'), 0),
                mhl_adult_amount=Coalesce(Sum('mhl_adult_amount'), 0),
                mhl_child_amount=Coalesce(Sum('mhl_child_amount'), 0)
            )

            total_earnings_count = total_earnings['total_ticket_amount'] + total_earnings[
                'mhl_adult_amount'] + total_earnings['mhl_child_amount']

            trip_point_result.append({
                'point_name': point_name.point_name,
                'no_of_buses': no_of_buses,
                'total_passengers_count': total_passengers_count,
                'total_earnings_count': total_earnings_count,
            })

            return render(request, 'reports/search_route_wise_buses_to_list.html',
                          {'trip_point_result': trip_point_result,
                           'point_names': point_names})
        else:
            return render(request, 'reports/search_route_wise_buses_to_list.html',
                          {'point_names': point_names})
    else:
        current_datetime = timezone.now()
        yesterday_datetime = current_datetime - datetime.timedelta(days=3)

        trip_point_data = TripStatistics.objects.filter(entry_type='up').filter(
            start_to_location__point_name='Thadvai').filter(trip_start__gte=yesterday_datetime). \
            values_list('start_from_location', flat=True).distinct()
        if len(trip_point_data) > 0:
            for trip_point in trip_point_data:
                point_name = PointData.objects.get(id=trip_point)
                no_of_buses = TripStatistics.objects.filter(entry_type='up').filter(
                    start_to_location=trip_point).count()
                total_passengers = TripStatistics.objects.filter(entry_type='up').filter(
                    start_to_location__point_name='Thadvai').filter(
                    start_from_location=trip_point).filter(trip_start__gte=yesterday_datetime).aggregate(
                    total_adult_passengers=Coalesce(Sum('total_adult_passengers'), 0),
                    total_child_passengers=Coalesce(Sum('total_child_passengers'), 0),
                    mhl_adult_passengers=Coalesce(Sum('mhl_adult_passengers'), 0),
                    mhl_child_passengers=Coalesce(Sum('mhl_child_passengers'), 0)
                )
                total_passengers_count = total_passengers['total_adult_passengers'] + total_passengers[
                    'total_child_passengers'] + total_passengers['mhl_adult_passengers'] + \
                                         total_passengers['mhl_child_passengers']

                total_earnings = TripStatistics.objects.filter(entry_type='up').filter(
                    start_to_location__point_name='Thadvai').filter(
                    start_from_location=trip_point).filter(trip_start__gte=yesterday_datetime).aggregate(
                    total_ticket_amount=Coalesce(Sum('total_ticket_amount'), 0),
                    mhl_adult_amount=Coalesce(Sum('mhl_adult_amount'), 0),
                    mhl_child_amount=Coalesce(Sum('mhl_child_amount'), 0)
                )

                total_earnings_count = total_earnings['total_ticket_amount'] + total_earnings[
                    'mhl_adult_amount'] + total_earnings['mhl_child_amount']

                trip_point_result.append({
                    'point_name': point_name.point_name,
                    'no_of_buses': no_of_buses,
                    'total_passengers_count': total_passengers_count,
                    'total_earnings_count': total_earnings_count,
                })
        return render(request, 'reports/search_route_wise_buses_to_list.html',
                      {'point_names': point_names})


@custom_login_required
def search_route_wise_buses_from_list(request):
    point_names = PointData.objects.filter(~Q(status=2))
    trip_point_result = []
    if request.method == "POST":
        # point_name = request.POST.get('point_name')
        date = request.POST.get('date')
        given_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        trip_point_data = TripStatistics.objects.filter(entry_type='down').filter(
            start_from_location__point_name='Thadvai').filter(trip_start__date=given_date). \
            values_list('start_to_location', flat=True).distinct()
        if len(trip_point_data) > 0:
            for trip_point in trip_point_data:
                point_name = PointData.objects.get(id=trip_point)
                no_of_buses = TripStatistics.objects.filter(entry_type='down').filter(
                    start_to_location=trip_point).count()
                total_passengers = TripStatistics.objects.filter(entry_type='down').filter(
                    start_to_location=trip_point).filter(trip_start__date=given_date).aggregate(
                    total_adult_passengers=Coalesce(Sum('total_adult_passengers'), 0),
                    total_child_passengers=Coalesce(Sum('total_child_passengers'), 0),
                    mhl_adult_passengers=Coalesce(Sum('mhl_adult_passengers'), 0),
                    mhl_child_passengers=Coalesce(Sum('mhl_child_passengers'), 0)
                )
                total_passengers_count = total_passengers['total_adult_passengers'] + total_passengers[
                    'total_child_passengers'] + total_passengers['mhl_adult_passengers'] + \
                                         total_passengers['mhl_child_passengers']

                total_earnings = TripStatistics.objects.filter(entry_type='down').filter(
                    start_to_location=trip_point).filter(trip_start__date=given_date).aggregate(
                    total_ticket_amount=Coalesce(Sum('total_ticket_amount'), 0),
                    mhl_adult_amount=Coalesce(Sum('mhl_adult_amount'), 0),
                    mhl_child_amount=Coalesce(Sum('mhl_child_amount'), 0)
                )

                total_earnings_count = total_earnings['total_ticket_amount'] + total_earnings[
                    'mhl_adult_amount'] + total_earnings['mhl_child_amount']

                trip_point_result.append({
                    'point_name': point_name.point_name,
                    'no_of_buses': no_of_buses,
                    'total_passengers_count': total_passengers_count,
                    'total_earnings_count': total_earnings_count,
                })

            return render(request, 'reports/search_route_wise_buses_from_list.html',
                          {'trip_point_result': trip_point_result,
                           'point_names': point_names})
        else:
            return render(request, 'reports/search_route_wise_buses_from_list.html',
                          {'point_names': point_names})
    else:
        current_datetime = timezone.now()
        yesterday_datetime = current_datetime - datetime.timedelta(days=1)

        trip_point_data = TripStatistics.objects.filter(entry_type='down').filter(
            start_from_location__point_name='Thadvai').filter(trip_start__gte=yesterday_datetime). \
            values_list('start_to_location', flat=True).distinct()
        if len(trip_point_data) > 0:
            for trip_point in trip_point_data:
                point_name = PointData.objects.get(id=trip_point)
                no_of_buses = TripStatistics.objects.filter(entry_type='down').filter(
                    start_to_location=trip_point).count()
                total_passengers = TripStatistics.objects.filter(entry_type='down').filter(
                    start_to_location=trip_point).filter(trip_start__gte=yesterday_datetime).aggregate(
                    total_adult_passengers=Coalesce(Sum('total_adult_passengers'), 0),
                    total_child_passengers=Coalesce(Sum('total_child_passengers'), 0),
                    mhl_adult_passengers=Coalesce(Sum('mhl_adult_passengers'), 0),
                    mhl_child_passengers=Coalesce(Sum('mhl_child_passengers'), 0)
                )
                total_passengers_count = total_passengers['total_adult_passengers'] + total_passengers[
                    'total_child_passengers'] + total_passengers['mhl_adult_passengers'] + \
                                         total_passengers['mhl_child_passengers']

                total_earnings = TripStatistics.objects.filter(entry_type='down').filter(
                    start_to_location=trip_point).filter(trip_start__gte=yesterday_datetime).aggregate(
                    total_ticket_amount=Coalesce(Sum('total_ticket_amount'), 0),
                    mhl_adult_amount=Coalesce(Sum('mhl_adult_amount'), 0),
                    mhl_child_amount=Coalesce(Sum('mhl_child_amount'), 0)
                )

                total_earnings_count = total_earnings['total_ticket_amount'] + total_earnings[
                    'mhl_adult_amount'] + total_earnings['mhl_child_amount']

                trip_point_result.append({
                    'point_name': point_name.point_name,
                    'no_of_buses': no_of_buses,
                    'total_passengers_count': total_passengers_count,
                    'total_earnings_count': total_earnings_count,
                })

        return render(request, 'reports/search_route_wise_buses_from_list.html',
                      {'point_names': point_names, 'trip_point_result': trip_point_result})


@custom_login_required
def search_hour_wise_dispatched_buses_list(request):
    point_names = PointData.objects.filter(~Q(status=2)).filter(~Q(point_name='Thadvai'))
    if request.method == "POST":
        trip_point_result = []
        point_name = request.POST.get('point_name')
        date = request.POST.get('date')
        entry_type = request.POST.get('entry_type')
        given_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()

        current_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=0, minutes=0)))
        start_of_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        # Generate the hourly ranges
        hourly_ranges = [(start_of_day + timezone.timedelta(hours=i), start_of_day + timezone.timedelta(hours=i + 1))
                         for i in range(24)]

        for start, end in hourly_ranges:
            if entry_type == 'up':
                trip_point_data = TripStatistics.objects.filter(entry_type=entry_type).filter(
                    start_from_location=point_name). \
                    filter(start_to_location__point_name='Thadvai').filter(trip_start__range=(start, end))
                if len(trip_point_data) > 0:
                    no_of_trips = trip_point_data.count()

                    total_passengers = TripStatistics.objects.filter(entry_type=entry_type).filter(
                        start_from_location=point_name). \
                        filter(start_to_location__point_name='Thadvai').filter(
                        trip_start__range=(start, end)).aggregate(
                        total_adult_passengers=Coalesce(Sum('total_adult_passengers'), 0),
                        total_child_passengers=Coalesce(Sum('total_child_passengers'), 0),
                        mhl_adult_passengers=Coalesce(Sum('mhl_adult_passengers'), 0),
                        mhl_child_passengers=Coalesce(Sum('mhl_child_passengers'), 0)
                    )
                    total_passengers_count = total_passengers['total_adult_passengers'] + total_passengers[
                        'total_child_passengers'] + total_passengers['mhl_adult_passengers'] + \
                                             total_passengers['mhl_child_passengers']

                    total_earnings = TripStatistics.objects.filter(entry_type=entry_type).filter(
                        start_from_location=point_name). \
                        filter(start_to_location__point_name='Thadvai').filter(
                        trip_start__range=(start, end)).aggregate(
                        total_ticket_amount=Coalesce(Sum('total_ticket_amount'), 0),
                        mhl_adult_amount=Coalesce(Sum('mhl_adult_amount'), 0),
                        mhl_child_amount=Coalesce(Sum('mhl_child_amount'), 0)
                    )

                    total_earnings_count = total_earnings['total_ticket_amount'] + total_earnings[
                        'mhl_adult_amount'] + total_earnings['mhl_child_amount']

                    trip_point_result.append({
                        'no_of_trips': no_of_trips,
                        'no_of_fair_adult_pssg': total_passengers['total_adult_passengers'],
                        'no_of_fair_child_pssg': total_passengers['total_child_passengers'],
                        'total_fare_pssg_amount': total_earnings['total_ticket_amount'],
                        'no_of_mhl_adult_pssg': total_passengers['mhl_adult_passengers'],
                        'no_of_mhl_child_pssg': total_passengers['mhl_child_passengers'],
                        'total_mhl_amount': total_earnings['mhl_adult_amount'] + total_earnings['mhl_child_amount'],
                        'total_passg': total_passengers_count,
                        'total_earnings': total_earnings_count,
                        "start_time": '{:02d}'.format(start.time().hour) + ':' + '{:02d}'.format(
                            start.time().minute) + ':' + '{:02d}'.format(start.time().second),
                        "end_time": '{:02d}'.format(end.time().hour) + ':' + '{:02d}'.format(
                            end.time().minute) + ':' + ':59'
                    })
            else:
                trip_point_data = TripStatistics.objects.filter(entry_type=entry_type).filter(
                    start_from_location__point_name='Thadvai').filter(start_to_location=point_name).filter(
                    trip_start__range=(start, end))
                if len(trip_point_data) > 0:
                    no_of_trips = trip_point_data.count()

                    total_passengers = TripStatistics.objects.filter(entry_type=entry_type).filter(
                        start_from_location__point_name='Thadvai'). \
                        filter(start_to_location=point_name).filter(
                        trip_start__range=(start, end)).aggregate(
                        total_adult_passengers=Coalesce(Sum('total_adult_passengers'), 0),
                        total_child_passengers=Coalesce(Sum('total_child_passengers'), 0),
                        mhl_adult_passengers=Coalesce(Sum('mhl_adult_passengers'), 0),
                        mhl_child_passengers=Coalesce(Sum('mhl_child_passengers'), 0)
                    )
                    total_passengers_count = total_passengers['total_adult_passengers'] + total_passengers[
                        'total_child_passengers'] + total_passengers['mhl_adult_passengers'] + \
                                             total_passengers['mhl_child_passengers']

                    total_earnings = TripStatistics.objects.filter(entry_type=entry_type).filter(
                        start_from_location__point_name='Thadvai'). \
                        filter(start_to_location=point_name).filter(
                        trip_start__range=(start, end)).aggregate(
                        total_ticket_amount=Coalesce(Sum('total_ticket_amount'), 0),
                        mhl_adult_amount=Coalesce(Sum('mhl_adult_amount'), 0),
                        mhl_child_amount=Coalesce(Sum('mhl_child_amount'), 0)
                    )

                    total_earnings_count = total_earnings['total_ticket_amount'] + total_earnings[
                        'mhl_adult_amount'] + total_earnings['mhl_child_amount']

                    trip_point_result.append({
                        'no_of_trips': no_of_trips,
                        'no_of_fair_adult_pssg': total_passengers['total_adult_passengers'],
                        'no_of_fair_child_pssg': total_passengers['total_child_passengers'],
                        'total_fare_pssg_amount': total_earnings['total_ticket_amount'],
                        'no_of_mhl_adult_pssg': total_passengers['mhl_adult_passengers'],
                        'no_of_mhl_child_pssg': total_passengers['mhl_child_passengers'],
                        'total_mhl_amount': total_earnings['mhl_adult_amount'] + total_earnings['mhl_child_amount'],
                        'total_passg': total_passengers_count,
                        'total_earnings': total_earnings_count,
                        "start_time": '{:02d}'.format(
                            start.time().hour) + ':' + '{:02d}'.format(start.time().minute) + ':' + '{:02d}'.format(
                            start.time().second),

                        "end_time": '{:02d}'.format(end.time().hour) + ':' + '{:02d}'.format(
                            end.time().minute) + ':' + ':59'

                    })

        return render(request, 'reports/hour_wise_dispatched_buses_list.html',
                      {'trip_point_result': trip_point_result,
                       'point_names': point_names})
    else:
        return render(request, 'reports/hour_wise_dispatched_buses_list.html',
                      {'point_names': point_names})


@custom_login_required
def en_route_wise_list(request):
    if request.method == "POST":
        unique_bus_no = request.POST.get('unique_bus_no')
    else:
        # trip_data = TripStatistics.objects.filter(Q(status=0) | Q(status=1)).filter(~Q(trip_verified=True)).\
        #     filter(entry_type='up').latest('created_at').distinct()
        # trip_data = TripStatistics.objects.values('bus_number', 'start_from_location__point_name', 'start_to_location__point_name',
        #                                           'unique_code', 'trip_start').filter(Q(status=0) | Q(status=1)).\
        #     filter(entry_type='up').annotate(latest_date=Max('trip_start')).order_by()

        # Get the latest record for each unique name
        latest_records = TripStatistics.objects.filter(
            bus_number=OuterRef('bus_number')
        ).order_by('-trip_start')

        # Query to fetch the latest record for each unique name
        queryset = TripStatistics.objects.filter(trip_verified=False).filter(
            id=Subquery(latest_records.values('id')[:1])
        ).values('bus_number', 'start_from_location__point_name', 'start_to_location__point_name',
                                                  'unique_code', 'trip_start', 'trip_verify_by')

        return render(request, 'reports/en_route_wise_list.html', {'trip_data': queryset})



@custom_login_required
def en_route_bus_details(request):
    bus_number = request.GET.get('id')
    if bus_number:
        en_route_bus_details = SpecialBusDataEntry.objects.get(bus_number__bus_number=bus_number)
        date_part = en_route_bus_details.created_at.date()
        time_part = en_route_bus_details.created_at.time()
    try:
        return render(request, 'reports/en_route_bus_details.html',
                      {"en_route_bus_details": en_route_bus_details, "date_part": date_part, "time_part": time_part})
    except Exception as e:
        print(e)
        return render(request, 'reports/en_route_bus_details.html', {})


@custom_login_required
def out_depot_vehicle_receive_edit(request):
    out_depot_vehicle_receive_id = request.GET.get('id')
    if out_depot_vehicle_receive_id:
        out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects.get(id=out_depot_vehicle_receive_id)
    try:
        return render(request, 'out_depot_buses/out_depot_vehicle_receive/edit.html',
                      {"out_depot_vehicle_receive_data": out_depot_vehicle_receive_data})
    except Exception as e:
        print(e)
        return render(request, 'out_depot_buses/out_depot_vehicle_receive/edit.html', {})


@custom_login_required
def out_depot_vehicle_receive_update(request):
    out_depot_vehicle_receive_id = request.POST.get('id')
    # bus_number = request.POST.get('bus_number')
    unique_no = request.POST.get('unique_no')
    new_log_sheet_no = request.POST.get('new_log_sheet_no')
    hsd_top_oil_liters = request.POST.get('hsd_top_oil_liters')
    mts_no = request.POST.get('mts_no')
    bus_reported_date = request.POST.get('bus_reported_date')
    bus_reported_time = request.POST.get('bus_reported_time')
    out_depot_buses_receive_status = 0
    if out_depot_vehicle_receive_id:
        try:
            out_depot_buses_receive_unique_count = OutDepotVehicleReceive.objects.filter(unique_no=unique_no)
            if out_depot_buses_receive_unique_count.exists():
                messages.error(request, 'Unique number already exists update  failed!!')
                return redirect("app:out_depot_buses_receive_list")
            out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects.get(id=out_depot_vehicle_receive_id)
            out_depot_vehicle_receive_data.unique_no = unique_no
            out_depot_vehicle_receive_data.new_log_sheet_no = new_log_sheet_no
            out_depot_vehicle_receive_data.hsd_top_oil_liters = hsd_top_oil_liters
            out_depot_vehicle_receive_data.mts_no = mts_no
            out_depot_vehicle_receive_data.bus_reported_date = bus_reported_date
            out_depot_vehicle_receive_data.bus_reported_time = bus_reported_time
            out_depot_vehicle_receive_data.status = out_depot_buses_receive_status
            # vehicle_detail_data = VehicleDetails.objects.get(bus_number=bus_number)
            # out_depot_vehicle_receive_data.bus_number = vehicle_detail_data
            # special_bus_data = SpecialBusDataEntry.objects.get(bus_number=vehicle_detail_data)
            # out_depot_vehicle_receive_data.special_bus_data_entry = special_bus_data
            # out_depot_bus_sending_depot = Depot.objects.get(id=special_bus_data.special_bus_sending_depot.id)
            # out_depot_vehicle_receive_data.out_depot_bus_sending_depot = out_depot_bus_sending_depot
            # out_depot_bus_reporting_depot = Depot.objects.get(id=special_bus_data.special_bus_reporting_depot.id)
            # out_depot_vehicle_receive_data.out_depot_bus_reporting_depot = out_depot_bus_reporting_depot
            user_data = User.objects.get(id=request.session['user_id'])
            out_depot_vehicle_receive_data.updated_by = user_data
            out_depot_vehicle_receive_data.save()
            messages.success(request, 'Out Depot Vehicle Receive Details updated  successfully!!')
            return redirect("app:out_depot_buses_receive_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Out Depot Vehicle Receive Details update  failed!!')
            return redirect("app:out_depot_buses_receive_list")
    else:
        return redirect("app:out_depot_buses_receive_list")


@custom_login_required
def out_depot_vehicle_send_back_edit(request):
    out_depot_vehicle_send_back_id = request.GET.get('id')
    if out_depot_vehicle_send_back_id:
        out_depot_vehicle_send_back_data = OutDepotVehicleSentBack.objects.get(id=out_depot_vehicle_send_back_id)
        unique_no_list = []
        if out_depot_vehicle_send_back_data.unique_no:
            unique_no_list.append(out_depot_vehicle_send_back_data.unique_no)
    try:
        out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects.filter(Q(status=0) | Q(status=1))
        return render(request, 'out_depot_buses/out_depot_vehicle_send_back/edit.html',
                      {"out_depot_vehicle_send_back_data": out_depot_vehicle_send_back_data,
                       'unique_no_list': unique_no_list,
                       'out_depot_vehicle_receive_data': out_depot_vehicle_receive_data})
    except Exception as e:
        print(e)
        return render(request, 'out_depot_buses/out_depot_vehicle_send_back/edit.html', {})


@custom_login_required
def out_depot_vehicle_send_back_update(request):
    out_depot_vehicle_send_back_id = request.POST.get('id')
    unique_no = request.POST.get('out_depot_vehicle_receive_unique_no')
    bus_number = request.POST.get('out_depot_vehicle_receive_bus_number')
    log_sheet_no = request.POST.get('log_sheet_no')
    out_depot_buses_send_back_status = 0
    if out_depot_vehicle_send_back_id:
        try:
            out_depot_vehicle_send_back_data = OutDepotVehicleSentBack.objects.get(id=out_depot_vehicle_send_back_id)
            out_depot_vehicle_send_back_data.unique_no = unique_no
            out_depot_vehicle_send_back_data.bus_number = bus_number
            out_depot_vehicle_send_back_data.status = out_depot_buses_send_back_status
            special_bus_data = SpecialBusDataEntry.objects.get(log_sheet_no=log_sheet_no)
            out_depot_vehicle_send_back_data.special_bus_data_entry = special_bus_data
            user_data = User.objects.get(id=request.session['user_id'])
            out_depot_vehicle_send_back_data.updated_by = user_data
            out_depot_vehicle_send_back_data.save()
            messages.success(request, 'Out Depot Vehicle Send Back Details updated  successfully!!')
            return redirect("app:out_depot_vehicle_send_back_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Out Depot Vehicle Send Back Details update  failed!!')
            return redirect("app:out_depot_vehicle_send_back_list")
    else:
        return redirect("app:out_depot_vehicle_send_back_list")


@custom_login_required
def buses_on_hand_edit(request):
    buses_on_hand_id = request.GET.get('id')
    if buses_on_hand_id:
        buses_on_hand_data = BusesOnHand.objects.get(id=buses_on_hand_id)
        point_name_id_list = []
        if buses_on_hand_data.point_name:
            point_name_id_list.append(buses_on_hand_data.point_name.id)
    try:
        point_name_data = PointData.objects.filter(Q(status=0) | Q(status=1))
        return render(request, 'buses_on_hand/edit.html', {"buses_on_hand_data": buses_on_hand_data,
                                                           'point_name_data': point_name_data,
                                                           'point_name_id_list': point_name_id_list})
    except Exception as e:
        print(e)
        return render(request, 'buses_on_hand/edit.html', {})


@custom_login_required
def buses_on_hand_update(request):
    buses_on_hand_id = request.POST.get('id')
    unique_code = request.POST.get('unique_code')
    bus_in_out = request.POST.get('bus_in_out')
    point_name = request.POST.get('point_name_id')
    buses_on_hand_status = 0
    if buses_on_hand_id:
        try:
            buses_on_hand_data = BusesOnHand.objects.get(id=buses_on_hand_id)
            buses_on_hand_data.unique_code = unique_code
            point_name_data = PointData.objects.get(id=point_name)
            buses_on_hand_data.point_name = point_name_data
            buses_on_hand_data.bus_in_out = bus_in_out
            buses_on_hand_data.status = buses_on_hand_status
            out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects.get(unique_no=unique_code)
            special_bus_data = out_depot_vehicle_receive_data.special_bus_data_entry
            buses_on_hand_data.special_bus_data_entry = special_bus_data
            user_data = User.objects.get(id=request.session['user_id'])
            buses_on_hand_data.updated_by = user_data
            buses_on_hand_data.save()
            messages.success(request, 'Buses on hand Details Details updated  successfully!!')
            return redirect("app:buses_on_hand_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Buses on hand Details Details update  failed!!')
            return redirect("app:buses_on_hand_list")
    else:
        return redirect("app:buses_on_hand_list")


@custom_login_required
def hsd_oil_submission_edit(request):
    hsd_oil_submission_id = request.GET.get('id')
    if hsd_oil_submission_id:
        hsd_oil_submission_data = HsdOilSubmission.objects.get(id=hsd_oil_submission_id)
    try:
        return render(request, 'hsd_oil_submission/edit.html', {"hsd_oil_submission_data": hsd_oil_submission_data})
    except Exception as e:
        print(e)
        return render(request, 'hsd_oil_submission/edit.html', {})


@custom_login_required
def hsd_oil_submission_update(request):
    hsd_oil_submission_id = request.POST.get('id')
    bus_number = request.POST.get('hsd_oil_bus_number')
    hsd_liters = request.POST.get('hsd_top_oil_liters')
    mts_no = request.POST.get('mts_no')
    point_name = request.POST.get('point_name')
    unique_no_bus_no = request.POST.get('unique_bus_no')
    shift = request.POST.get('shift')
    hsd_oil_submission_status = 0
    if hsd_oil_submission_id:
        try:
            hsd_oil_submission_data = HsdOilSubmission.objects.get(id=hsd_oil_submission_id)
            hsd_oil_submission_data.unique_no_bus_no = unique_no_bus_no
            hsd_oil_submission_data.point_name = point_name
            hsd_oil_submission_data.hsd_liters = hsd_liters
            hsd_oil_submission_data.mts_no = mts_no
            hsd_oil_submission_data.status = hsd_oil_submission_status
            vehicle_detail_data = VehicleDetails.objects.get(bus_number=bus_number)
            special_bus_data = SpecialBusDataEntry.objects.get(bus_number=vehicle_detail_data)
            hsd_oil_submission_data.special_bus_data_entry = special_bus_data
            hsd_oil_submission_data.shift = shift
            user_data = User.objects.get(id=request.session['user_id'])
            hsd_oil_submission_data.updated_by = user_data
            hsd_oil_submission_data.save()
            messages.success(request, 'HSD Oil Submission Details updated  successfully!!')
            return redirect("app:hsd_oil_submission_list")
        except Exception as e:
            print(e)
            messages.error(request, 'HSD Oil Submission Details update  failed!!')
            return redirect("app:hsd_oil_submission_list")
    else:
        return redirect("app:hsd_oil_submission_list")


@transaction.atomic
@custom_login_required
def point_data_import(request):
    print("Called")
    if request.method == "POST":
        file = request.FILES.get('point_data_list')
        try:
            df = pd.read_excel(file)
            row_iter = df.iterrows()
            for i, row in row_iter:
                print(row)
                try:
                    name = row[1]
                    point_name_exist = PointData.objects.filter(point_name=name).count()
                    if point_name_exist == 0:
                        depot_data = Depot.objects.get(name=row[2])
                        point_name = PointData.objects.create(point_name=name, depot_name=depot_data, region=row[3],
                                                              zone=row[4], status=0)
                        point_name.save()
                    else:
                        pass
                except Exception as e:
                    print(e)
            return redirect("app:point_data_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Point Data import failed!!')
        return redirect("app:point_data_list")
    return render(request, 'point_data/import.html', {})


@custom_login_required
def point_data_list(request):
    point_data = PointData.objects.filter(~Q(status=2))
    return render(request, 'point_data/list.html', {"point_name_data": point_data})


def validate_log_sheet(request):
    log_sheet_no = request.GET.get('log_sheet_no')
    try:
        special_bus_data = SpecialBusDataEntry.objects.get(log_sheet_no=log_sheet_no)
        exists = True
    except SpecialBusDataEntry.DoesNotExist:
        exists = False
    return JsonResponse({'exists': exists})


@custom_login_required
def get_out_depot_vehicle_receive_bus_number(request):
    unique_no = request.GET.get('unique_no')
    out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects.get(unique_no=unique_no)
    special_bus_data = out_depot_vehicle_receive_data.special_bus_data_entry
    return JsonResponse({'bus_number': special_bus_data.bus_number.bus_number})


@custom_login_required
def point_name_add(request):
    if request.method == "POST":
        point_name = request.POST.get('point_name')
        depot_id = request.POST.get('depot_id')
        region = request.POST.get('region')
        zone = request.POST.get('zone')
        point_status = 0
        try:
            depot_data = Depot.objects.get(id=depot_id)
            point_data = PointData.objects.create(point_name=point_name, status=point_status, region=region, zone=zone,
                                                  depot_name=depot_data)
            point_data.save()
            messages.success(request, 'Point Created Successfully')
        except Exception as e:
            print(e)
            messages.error(request, 'Point Creation Failed!!')
        return redirect("app:point_data_list")
    try:
        depot_data = Depot.objects.filter(Q(status=0) | Q(status=1))
        return render(request, 'point_data/add.html', {"depot_data": depot_data})
    except Exception as e:
        print(e)
        return render(request, 'point_data/add.html', {})


@custom_login_required
def point_name_edit(request):
    point_name_id = request.GET.get('id')
    if point_name_id:
        point_name_data = PointData.objects.get(id=point_name_id)
        depot_id_list = []
        if point_name_data.depot_name:
            depot_id_list.append(point_name_data.depot_name.id)
    try:
        depot_data = Depot.objects.filter(Q(status=0) | Q(status=1))
        return render(request, 'point_data/edit.html', {'depot_data': depot_data, "point": point_name_data,
                                                        'depot_id_list': depot_id_list})
    except Exception as e:
        print(e)
        return render(request, 'point_data/edit.html', {})


@custom_login_required
def point_name_update(request):
    point_name_id = request.POST.get('id')
    point_name = request.POST.get('point_name')
    depot_id = request.POST.get('depot_id')
    region = request.POST.get('region')
    zone = request.POST.get('zone')
    point_status = 0
    if point_name_id:
        try:
            point_name_data = PointData.objects.get(id=point_name_id)
            point_name_data.point_name = point_name
            point_name_data.region = region
            point_name_data.zone = zone
            point_name_data.status = point_status
            depot_data = Depot.objects.get(id=depot_id)
            point_name_data.depot_name = depot_data
            point_name_data.save()
            messages.success(request, 'Point Data updated  successfully!!')
            return redirect("app:point_data_list")
        except Exception as e:
            print(e)
            messages.error(request, 'Point Data update  failed!!')
            return redirect("app:point_data_list")
    else:
        return redirect("app:point_data_list")


def dashboard_details_list(request):
    point_names = PointData.objects.filter(~Q(status=2)).filter(~Q(point_name='Thadvai'))
    result_data = []
    if request.method == "POST":
        point_name = request.POST.get('point_name_id')
        start_date_str = '2024-02-01'
        end_date_str = '2024-03-16'
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        dates_list = list(rrule(DAILY, dtstart=start_date, until=end_date))
        total_passengers = 0
        total_buses = 0
        for date in dates_list:
            total_passengers_up = TripStatistics.objects.filter(entry_type='up').filter(
                start_to_location__point_name='Thadvai').filter(
                start_from_location__point_name=point_name).filter(trip_start__date=date).aggregate(
                total_adult_passengers=Coalesce(Sum('total_adult_passengers'), 0),
                total_child_passengers=Coalesce(Sum('total_child_passengers'), 0),
                mhl_adult_passengers=Coalesce(Sum('mhl_adult_passengers'), 0),
                mhl_child_passengers=Coalesce(Sum('mhl_child_passengers'), 0)
            )

            total_passengers_down = TripStatistics.objects.filter(entry_type='down').filter(
                trip_start__date=date).filter(
                start_from_location__point_name='Thadvai').filter(start_to_location__point_name=point_name).aggregate(
                total_adult_passengers=Coalesce(Sum('total_adult_passengers'), 0),
                total_child_passengers=Coalesce(Sum('total_child_passengers'), 0),
                mhl_adult_passengers=Coalesce(Sum('mhl_adult_passengers'), 0),
                mhl_child_passengers=Coalesce(Sum('mhl_child_passengers'), 0)
            )

            if any(total_passengers_up.values()) or any(total_passengers_down.values()):
                total_passengers_left = total_passengers_up['total_adult_passengers'] + total_passengers_up[
                    'total_child_passengers'] + total_passengers_up['mhl_adult_passengers'] + \
                                        total_passengers_up['mhl_child_passengers']

                no_of_buses_left = TripStatistics.objects.filter(entry_type='up').filter(trip_start__date=date).filter(
                    start_to_location__point_name='Thadvai').filter(start_from_location__point_name=point_name).count()

                total_passengers_dispatched = total_passengers_down['total_adult_passengers'] + total_passengers_down[
                    'total_child_passengers'] + total_passengers_down['mhl_adult_passengers'] + \
                                              total_passengers_down['mhl_child_passengers']

                no_of_buses_dispatched = TripStatistics.objects.filter(entry_type='down').filter(trip_start__date=date) \
                    .filter(start_from_location__point_name='Thadvai').filter(start_to_location__point_name=point_name). \
                    count()

                total_passengers_left_over = total_passengers_left - total_passengers_dispatched

                available_buses = no_of_buses_left - no_of_buses_dispatched

                total_passengers = total_passengers + total_passengers_left_over
                total_buses = total_buses + available_buses

                result_data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'total_passengers_left_over': total_passengers_left_over,
                    'available_buses': available_buses,
                    'passengers_left': total_passengers_left,
                    'buses_left': no_of_buses_left,
                    'passengers_dispatched': total_passengers_dispatched,
                    'buses_dispatched': no_of_buses_dispatched,
                })

        return render(request, 'reports/dashboard_details_list.html', {'point_names': point_names,
                                                                       'dashboard_data': result_data,
                                                                       'total_passengers': total_passengers,
                                                                       'total_buses': total_buses})
    else:
        return render(request, 'reports/dashboard_details_list.html', {'point_names': point_names})


def dashboard_details_entry_type(request):
    point_names = PointData.objects.filter(~Q(status=2)).filter(~Q(point_name='Thadvai'))
    result_data = []
    if request.method == "POST":
        point_name = request.POST.get('point_name')
        entry_type = request.POST.get('entry_type')
        start_date_str = '2024-02-01'
        end_date_str = '2024-03-16'
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        dates_list = list(rrule(DAILY, dtstart=start_date, until=end_date))
        for date in dates_list:
            if entry_type == 'up':
                total_passengers = TripStatistics.objects.filter(entry_type=entry_type).filter(
                    start_to_location__point_name='Thadvai').filter(
                    start_from_location__point_name=point_name).filter(trip_start__date=date).aggregate(
                    total_adult_passengers=Coalesce(Sum('total_adult_passengers'), 0),
                    total_child_passengers=Coalesce(Sum('total_child_passengers'), 0),
                    mhl_adult_passengers=Coalesce(Sum('mhl_adult_passengers'), 0),
                    mhl_child_passengers=Coalesce(Sum('mhl_child_passengers'), 0)
                )
                if any(total_passengers.values()):
                    total_adult_passengers = total_passengers['total_adult_passengers']
                    total_child_passengers = total_passengers['total_child_passengers']
                    mhl_adult_passengers = total_passengers['mhl_adult_passengers']
                    mhl_child_passengers = total_passengers['mhl_child_passengers']
                    total_passengers_count = total_adult_passengers+total_child_passengers+mhl_adult_passengers+mhl_child_passengers

                    total_amounts = TripStatistics.objects.filter(entry_type=entry_type).filter(
                        start_to_location__point_name='Thadvai'). \
                        filter(start_from_location__point_name=point_name).filter(
                        trip_start__date=date).aggregate(
                        total_ticket_amount=Coalesce(Sum('total_ticket_amount'), 0),
                        mhl_adult_amount=Coalesce(Sum('mhl_adult_amount'), 0),
                        mhl_child_amount=Coalesce(Sum('mhl_child_amount'), 0)
                    )

                    total_fare_passenger_amount = total_amounts['total_ticket_amount']
                    total_mhl_amount = total_amounts['mhl_adult_amount'] + total_amounts['mhl_child_amount']
                    total_earnings = total_fare_passenger_amount + total_mhl_amount

                    result_data.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'total_passengers': total_passengers_count,
                        'total_earnings': total_earnings,
                        'total_adult_passengers': total_adult_passengers,
                        'total_child_passengers': total_child_passengers,
                        'total_fare_passenger_amount': total_fare_passenger_amount,
                        'mhl_adult_passengers': mhl_adult_passengers,
                        'mhl_child_passengers': mhl_child_passengers,
                        'total_mhl_amount': total_mhl_amount
                    })
            else:
                total_passengers = TripStatistics.objects.filter(entry_type=entry_type).filter(
                    start_from_location__point_name='Thadvai').filter(
                    start_to_location__point_name=point_name).filter(trip_start__date=date).aggregate(
                    total_adult_passengers=Coalesce(Sum('total_adult_passengers'), 0),
                    total_child_passengers=Coalesce(Sum('total_child_passengers'), 0),
                    mhl_adult_passengers=Coalesce(Sum('mhl_adult_passengers'), 0),
                    mhl_child_passengers=Coalesce(Sum('mhl_child_passengers'), 0)
                )
                if any(total_passengers.values()):
                    total_adult_passengers = total_passengers['total_adult_passengers']
                    total_child_passengers = total_passengers['total_child_passengers']
                    mhl_adult_passengers = total_passengers['mhl_adult_passengers']
                    mhl_child_passengers = total_passengers['mhl_child_passengers']

                    total_amounts = TripStatistics.objects.filter(entry_type=entry_type).filter(
                        start_from_location__point_name='Thadvai'). \
                        filter(start_to_location__point_name=point_name).filter(
                        trip_start__date=date).aggregate(
                        total_ticket_amount=Coalesce(Sum('total_ticket_amount'), 0),
                        mhl_adult_amount=Coalesce(Sum('mhl_adult_amount'), 0),
                        mhl_child_amount=Coalesce(Sum('mhl_child_amount'), 0)
                    )

                    total_fare_passenger_amount = total_amounts['total_ticket_amount']
                    total_mhl_amount = total_amounts['mhl_adult_amount'] + total_amounts['mhl_child_amount']
                    total_earnings = total_fare_passenger_amount + total_mhl_amount
                    result_data.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'total_passengers': total_passengers,
                        'total_earnings': total_earnings,
                        'total_adult_passengers': total_adult_passengers,
                        'total_child_passengers': total_child_passengers,
                        'total_fare_passenger_amount': total_fare_passenger_amount,
                        'mhl_adult_passengers': mhl_adult_passengers,
                        'mhl_child_passengers': mhl_child_passengers,
                        'total_mhl_amount': total_mhl_amount
                    })
        return render(request, 'reports/dashboard_details_entry_type.html', {'point_names': point_names,
                                                                             'dashboard_data': result_data})
    else:
        return render(request, 'reports/dashboard_details_entry_type.html', {'point_names': point_names})


@api_view(['POST'])
def create_user(request):
    if request.method == "POST":
        name = 'admin_user'
        phone = '9876543210'
        email = 'admin@email.com'
        password = 'medaram'
        point_name = 'Thadvai'
        user_status = 0
        user_type = 'Super_admin'
        depot = 'KUKATPALLI'
        depot_code = 'KPL'
        try:
            user_exist = User.objects.filter(user_type__name=user_type)
            if user_exist:
                context = {'code': "Fail", 'message': "Creation Failed, Super admin user already existed",
                           'response_code': status.HTTP_400_BAD_REQUEST, "result": {}}
                return Response(context, status=status.HTTP_400_BAD_REQUEST)
            user_type_data = UserType.objects.create(name=user_type, status=user_status)
            user_type_data.save()
            depot_data = Depot.objects.create(name=depot, depot_code=depot_code, status=user_status)
            depot_data.save()
            point_name_data = PointData.objects.create(point_name=point_name, depot_name=depot_data, status=user_status)
            point_name_data.save()

            encrypted_password = cipher_suite.encrypt(password.encode())
            user = User.objects.create(name=name, email=email, password=encrypted_password, phone_number=phone,
                                       status=user_status, user_type=user_type_data, depot=depot_data,
                                       point_name=point_name_data)
            user.save()
            # encrypted_password = ast.literal_eval(user.password)
            decrypted_password = cipher_suite.decrypt(user.password).decode()
            user_data = {
                'email': user.email,
                'password': decrypted_password,
                'phone': user.phone_number
            }
            context = {'code': "Success", 'message': "User created successfully", 'response_code': status.HTTP_200_OK,
                       "result": user_data}
            return Response(context, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
    else:
        context = {'code': "Fail", 'message': "User create unsuccessfully",
                   'response_code': status.HTTP_400_BAD_REQUEST, "result": {}}
        return Response(context, status=status.HTTP_400_BAD_REQUEST)


def show_profile(request):
    user_data = User.objects.filter(Q(id=request.session['user_id']))
    if user_data:
        profile_data = {
            'name': user_data[0].name,
            'email': user_data[0].email,
            'role': user_data[0].user_type.name,
            'depot': user_data[0].depot.name,
        }
        return render(request, 'profile.html', {'profile_data': profile_data})
    else:
        return render(request, 'profile.html')


# REST API STARTS FROM HERE

class LoginAPIView(APIView):
    def post(self, request):
        serializer_instance = app_serializers.LoginSerializer(data=request.data)

        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        user_login_data = User.objects.filter(
            Q(email=serialized_data.get("user_email_phone")) | Q(phone_number=serialized_data.get("user_email_phone"))
        ).first()

        if user_login_data:
            encrypted_password = ast.literal_eval(user_login_data.password)
            decrypted_password = cipher_suite.decrypt(encrypted_password).decode()
            if decrypted_password == serialized_data.get(
                    "user_password"):  # and check_password(serialized_data.get("user_password"), user_login_data.password) this needs to be implementd.
                return Response(status=status.HTTP_200_OK, data={
                    "code": "Success",
                    "message": "User Login Successful.",
                    "result": user_login_data.get_details()
                })
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={
                    "code": "Fail",
                    "message": "Something Went Wrong. Login unsuccessful.",
                    "result": []
                })
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong. Login unsuccessful.",
                "result": []
            })


class DepotAPIView(APIView):
    def get(self, request):
        depot_instances = Depot.objects.all()
        depot_details = [depot.get_details() for depot in depot_instances]
        return Response(status=status.HTTP_200_OK, data={
            "code": "Success",
            "message": "All Depot Fetched Successfully.",
            "result": depot_details
        })


class OperationTypeAPIView(APIView):
    def get(self, request):
        operation_type_instances = OperationType.objects.all()
        operation_details = [opt_type.get_details() for opt_type in operation_type_instances]
        return Response(status=status.HTTP_200_OK, data={
            "code": "Success",
            "message": "All Opeartion Type Fetched Successfully.",
            "result": operation_details
        })


class DepotVehicleAPIView(APIView):
    def get(self, request):
        special_bus_sending_depot = request.GET.get("special_bus_sending_depot")
        serializer_instance = app_serializers.DepotVehicleSerializer(
            data={"special_bus_sending_depot": special_bus_sending_depot}
        )

        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data
        try:
            depot_instance = Depot.objects.get(
                id=serialized_data.get("special_bus_sending_depot")
            )
            vehicle_instances = VehicleDetails.objects.filter(depot=depot_instance)
            vehicle_details = [vehicle.get_details() for vehicle in vehicle_instances]
            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "All Opeartion Type Fetched Successfully.",
                "result": vehicle_details
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })


class AllSplBusEntryAPIView(APIView):
    def get(self, request):
        spl_bus_entry_instances = SpecialBusDataEntry.objects.filter(status=0)
        spl_buses_details = [bus.get_basic_details() for bus in spl_bus_entry_instances]
        return Response(status=status.HTTP_200_OK, data={
            "code": "Success",
            "message": "All Special Bus Entry Data Fetched Successfully.",
            "result": spl_buses_details
        })


class SplBusEntryAPIView(APIView):
    def get(self, request):
        special_bus_data_id = request.GET.get("special_bus_data_id")
        serializer_instance = app_serializers.GetSplBusDataEntrySerializer(
            data={"special_bus_data_id": special_bus_data_id}
        )
        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            spl_bus_entry_instance = SpecialBusDataEntry.objects.get(
                id=serialized_data.get("special_bus_data_id")
            )
            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "Special Bus Entry Data Fetched Successfully.",
                "result": spl_bus_entry_instance.get_complete_detail()
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })

    def post(self, request):
        serializer_instance = app_serializers.SplBusEntrySerializer(data=request.data)

        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            special_bus_sending_depot_instance = Depot.objects.get(
                id=serialized_data.get("bus_sending_depot")
            )
            special_bus_reporting_depot_instance = Depot.objects.get(
                id=serialized_data.get("bus_reporting_depot")
            )
            operation_type_instance = OperationType.objects.get(
                id=serialized_data.get("bus_type")
            )
            vehicle_instance = VehicleDetails.objects.get(
                id=serialized_data.get("bus_number")
            )

            spl_bus_entry_instance = SpecialBusDataEntry.objects.create(
                special_bus_sending_depot=special_bus_sending_depot_instance,
                special_bus_reporting_depot=special_bus_reporting_depot_instance,
                bus_type=operation_type_instance,
                bus_number=vehicle_instance,
                log_sheet_no=serialized_data.get("log_sheet_no"),
                driver1_name=serialized_data.get("driver1_name"),
                driver1_staff_no=serialized_data.get("driver1_staff_no"),
                driver1_phone_number=serialized_data.get("driver1_phone_number"),
                driver2_name=serialized_data.get("driver2_name"),
                driver2_staff_no=serialized_data.get("driver2_staff_no"),
                driver2_phone_number=serialized_data.get("driver2_phone_number"),
                incharge_name=serialized_data.get("incharge_name"),
                incharge_phone_number=serialized_data.get("incharge_phone_no"),
                status=0,
                # created_by = request.user,
                # updated_by = request.user
            )

            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "Special Bus Entry Data Added Successfully.",
                "result": []
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })


class SearchBusNumberAPI(APIView):
    def get(self, request):
        bus_number = request.GET.get("bus_number")
        serializer_instance = app_serializers.SearchBusNumberSerializer(
            data={"bus_number": bus_number}
        )
        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            bus_instance = VehicleDetails.objects.get(bus_number=serialized_data.get("bus_number"))
            spl_bus_details = SpecialBusDataEntry.objects.get(
                bus_number=bus_instance
            )
            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "Special Bus Details Fetched Successfully.",
                "result": spl_bus_details.get_complete_detail()
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })


class GetAllOutDepotVehicleReceiveAPIView(APIView):
    def get(self, request):
        out_depot_vehicle_instances = OutDepotVehicleReceive.objects.filter(~Q(status=2))
        out_depot_vehicle_receive_details = [bus.get_complete_details() for bus in out_depot_vehicle_instances]
        return Response(status=status.HTTP_200_OK, data={
            "code": "Success",
            "message": "All Out Depot Vehicle Receive Data Fetched Successfully.",
            "result": out_depot_vehicle_receive_details
        })


class OutDepotVehicleReceiveAPIView(APIView):
    def get(self, request):
        out_depot_vehicle_receive_id = request.GET.get("out_depot_vehicle_receive_id")
        serializer_instance = app_serializers.GetOutDepotVehicleReceiveSerializer(
            data={"out_depot_vehicle_receive_id": out_depot_vehicle_receive_id}
        )
        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            out_depot_vehicle_receive_instance = OutDepotVehicleReceive.objects.get(
                id=serialized_data.get("out_depot_vehicle_receive_id")
            )
            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "Special Bus Entry Data Fetched Successfully.",
                "result": out_depot_vehicle_receive_instance.get_complete_detail()
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })

    def post(self, request):
        serializer_instance = app_serializers.OutDepotVehicleReceiveSerializer(data=request.data)

        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            vehicle_detail_data = VehicleDetails.objects.get(bus_number=serialized_data.get("bus_number"))
            special_bus_data = SpecialBusDataEntry.objects.get(bus_number=vehicle_detail_data)
            user_data = User.objects.get(id=serialized_data.get("user_id"))
            is_exists = OutDepotVehicleReceive.objects.filter(unique_no=serialized_data.get("unique_no")).exists()
            if not is_exists:
                out_depo_buse_receive_detail = OutDepotVehicleReceive.objects.create(
                    bus_number=vehicle_detail_data,
                    special_bus_data_entry=special_bus_data,
                    unique_no=serialized_data.get("unique_no"),
                    new_log_sheet_no=serialized_data.get("new_log_sheet_no"),
                    hsd_top_oil_liters=serialized_data.get("hsd_top_oil_lts"),
                    mts_no=serialized_data.get("mts_no"),
                    bus_reported_date=datetime.datetime.strptime(serialized_data.get("bus_reported_date"), "%Y-%m-%d"),
                    bus_reported_time=datetime.datetime.strptime(serialized_data.get("bus_reported_time"), '%H:%M:%S'),
                    created_by=user_data,
                    status=0
                )
                return Response(status=status.HTTP_200_OK, data={
                    "code": "Success",
                    "message": "Out Depot Vehicle Receive Data Added Successfully.",
                    "result": []
                })
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={
                    "code": "Fail",
                    "message": "Something Went Wrong.",
                    "result": []
                })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })


class GetAllOutDepotVehicleSendBackAPIView(APIView):
    def get(self, request):
        out_depot_vehicle_instances = OutDepotVehicleSentBack.objects.filter(~Q(status=2))
        out_depot_vehicle_receive_details = [bus.get_complete_details() for bus in out_depot_vehicle_instances]
        return Response(status=status.HTTP_200_OK, data={
            "code": "Success",
            "message": "All Out Depot Vehicle Send Back Data Fetched Successfully.",
            "result": out_depot_vehicle_receive_details
        })


class OutDepotVehicleSendBackAPIView(APIView):
    def get(self, request):
        out_depot_vehicle_send_back_id = request.GET.get("out_depot_vehicle_send_back_id")
        serializer_instance = app_serializers.GetOutDepotVehicleSendBackSerializer(
            data={"out_depot_vehicle_send_back_id": out_depot_vehicle_send_back_id}
        )
        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            out_depot_vehicle_receive_instance = OutDepotVehicleSentBack.objects.get(
                id=serialized_data.get("out_depot_vehicle_send_back_id")
            )
            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "Out Depot Vehicle Sent Back Data Fetched Successfully.",
                "result": out_depot_vehicle_receive_instance.get_complete_detail()
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })

    def post(self, request):
        serializer_instance = app_serializers.OutDepotVehicleSendBackSerializer(data=request.data)

        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            special_bus_data = SpecialBusDataEntry.objects.get(log_sheet_no=serialized_data.get("log_sheet_no"))
            user_data = User.objects.get(id=serialized_data.get("user_id"))

            if special_bus_data:
                out_depo_buse_send_back_detail = OutDepotVehicleSentBack.objects.create(
                    unique_no=serialized_data.get("unique_no"),
                    bus_number=serialized_data.get("bus_number"),
                    log_sheet_no=serialized_data.get("log_sheet_no"),
                    special_bus_data_entry=special_bus_data,
                    created_by=user_data,
                    status=0
                )
                return Response(status=status.HTTP_200_OK, data={
                    "code": "Success",
                    "message": "Out Depot Vehicle Send Back Data Added Successfully.",
                    "result": []
                })
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={
                    "code": "Fail",
                    "message": "Something Went Wrong.",
                    "result": []
                })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })


class GetAllOwnDepotBusDetailAPIView(APIView):
    def get(self, request):
        own_depot_bus_entry_instances = OwnDepotBusDetailsEntry.objects.filter(~Q(status=2))
        own_depot_bus_entry_details = [bus.get_complete_details() for bus in own_depot_bus_entry_instances]
        return Response(status=status.HTTP_200_OK, data={
            "code": "Success",
            "message": "All Own Depot Bus Entry Data Fetched Successfully.",
            "result": own_depot_bus_entry_details
        })


class OwnDepotBusDetailAPIView(APIView):
    def get(self, request):
        own_depot_bus_detail_id = request.GET.get("own_depot_bus_detail_id")
        serializer_instance = app_serializers.GetOwnDepotBusDetailSerializer(
            data={"own_depot_bus_detail_id": own_depot_bus_detail_id}
        )
        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            own_depot_bus_entry_instance = OwnDepotBusDetailsEntry.objects.get(
                id=serialized_data.get("own_depot_bus_detail_id")
            )
            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "Own Depot Bus Entry Data Fetched Successfully.",
                "result": own_depot_bus_entry_instance.get_complete_details()
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })

    def post(self, request):
        serializer_instance = app_serializers.OwnDepotBusDetailSerializer(data=request.data)

        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            own_depot_buses_entry_unique_count = OwnDepotBusDetailsEntry.objects.filter(
                unique_no=serialized_data.get("unique_number")
            ).exists()
            if not own_depot_buses_entry_unique_count:
                vehicle_details = VehicleDetails.objects.get(bus_number=serialized_data.get("bus_number"))
                depot_data = Depot.objects.get(id=vehicle_details.depot.id)
                user_data = User.objects.get(id=serialized_data.get("user_id"))
                own_depot_bus_detail_entry = OwnDepotBusDetailsEntry.objects.create(
                    bus_number=serialized_data.get("bus_number"),
                    bus_type=serialized_data.get("bus_type"),
                    unique_no=serialized_data.get("unique_number"),
                    log_sheet_no=serialized_data.get("log_sheet_no"),
                    driver1_name=serialized_data.get("driver1_name"),
                    driver1_phone_number=serialized_data.get("driver1_phone_number"),
                    driver2_name=serialized_data.get("driver2_name"),
                    driver2_phone_number=serialized_data.get("driver2_phone_number"),
                    status=0,
                    created_by=user_data,
                    depot=depot_data
                )
                return Response(status=status.HTTP_200_OK, data={
                    "code": "Success",
                    "message": "Own Depot Bus Entry Data Added Successfully.",
                    "result": []
                })
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={
                    "code": "Fail",
                    "message": "Something Went Wrong.",
                    "result": []
                })
        except Exception as e:
            print("Exception", e)
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })


class GetAllOwnDepotBusWithdrawAPIView(APIView):
    def get(self, request):
        own_depot_bus_withdraw_instances = OwnDepotBusWithdraw.objects.filter(~Q(status=2))
        own_depot_bus_withdraw_details = [bus.get_complete_details() for bus in own_depot_bus_withdraw_instances]
        return Response(status=status.HTTP_200_OK, data={
            "code": "Success",
            "message": "All Own Depot Bus Withdraw Data Fetched Successfully.",
            "result": own_depot_bus_withdraw_details
        })


class OwnDepotBusWithdrawAPIView(APIView):
    def get(self, request):
        own_depot_bus_withdraw_id = request.GET.get("own_depot_bus_withdraw_id")
        serializer_instance = app_serializers.GetOwnDepotBusWithdrawSerializer(
            data={"own_depot_bus_withdraw_id": own_depot_bus_withdraw_id}
        )
        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            own_depot_bus_withdraw_instance = OwnDepotBusWithdraw.objects.get(
                id=serialized_data.get("own_depot_bus_withdraw_id")
            )
            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "Own Depot Bus Withdraw Data Fetched Successfully.",
                "result": own_depot_bus_withdraw_instance.get_complete_details()
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })

    def post(self, request):
        serializer_instance = app_serializers.OwnDepotBusWithdrawSerializer(data=request.data)

        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            vehicle_details = VehicleDetails.objects.get(bus_number=serialized_data.get("bus_number"))
            depot_data = Depot.objects.get(id=vehicle_details.depot.id)
            user_data = User.objects.get(id=serialized_data.get("user_id"))
            own_depot_bus_withdraw = OwnDepotBusWithdraw.objects.create(
                bus_number=serialized_data.get("bus_number"),
                status=0,
                created_by=user_data,
                depot=depot_data
            )
            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "Own Depot Bus Withdraw Data Added Successfully.",
                "result": []
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })


class GetAllUpJourneyAPIView(APIView):
    def get(self, request):
        up_journey_instances = StatisticsDateEntry.objects.filter(~Q(status=2))
        up_journey_details = [instance.get_complete_details() for instance in up_journey_instances]
        return Response(status=status.HTTP_200_OK, data={
            "code": "Success",
            "message": "All Up Journey Data Fetched Successfully.",
            "result": up_journey_details
        })


class UpJourneyAPIView(APIView):
    def get(self, request):
        up_journey_id = request.GET.get("up_journey_id")
        serializer_instance = app_serializers.GetUpJourneySerializer(
            data={"up_journey_id": up_journey_id}
        )
        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            up_journey_instance = StatisticsDateEntry.objects.get(
                id=serialized_data.get("up_journey_id")
            )
            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "Up Journey Data Fetched Successfully.",
                "result": up_journey_instance.get_complete_details()
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })

    def post(self, request):
        serializer_instance = app_serializers.UpDownJourneySerializer(data=request.data)

        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            user_data = User.objects.get(id=serialized_data.get("user_id"))
            statistics_data_entry = StatisticsDateEntry.objects.create(
                bus_unique_code=serialized_data.get("bus_unique_code"),
                total_ticket_amount=serialized_data.get("total_ticket_amount"),
                total_adult_passengers=serialized_data.get("total_adult_passengers"),
                total_child_passengers=serialized_data.get("total_child_passengers"),
                mhl_adult_passengers=serialized_data.get("mhl_adult_passengers"),
                mhl_child_passengers=serialized_data.get("mhl_child_passengers"),
                mhl_adult_amount=serialized_data.get("mhl_adult_amount"),
                mhl_child_amount=serialized_data.get("mhl_child_amount"),
                entry_type="up",
                # service_operated_date=serialized_data.get("user_id"),
                status=0,
                created_by=user_data
            )
            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "Up Journey Data Added Successfully.",
                "result": []
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })


class GetAllDownJourneyAPIView(APIView):
    def get(self, request):
        down_journey_instances = StatisticsDateEntry.objects.filter(~Q(status=2))
        down_journey_details = [instance.get_complete_details() for instance in down_journey_instances]
        return Response(status=status.HTTP_200_OK, data={
            "code": "Success",
            "message": "All Down Journey Data Fetched Successfully.",
            "result": down_journey_details
        })


class DownJourneyAPIView(APIView):
    def get(self, request):
        down_journey_id = request.GET.get("down_journey_id")
        serializer_instance = app_serializers.GetDownJourneySerializer(
            data={"down_journey_id": down_journey_id}
        )
        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            down_journey_instance = StatisticsDateEntry.objects.get(
                id=serialized_data.get("down_journey_id")
            )
            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "Down Journey Data Fetched Successfully.",
                "result": down_journey_instance.get_complete_details()
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })

    def post(self, request):
        serializer_instance = app_serializers.UpDownJourneySerializer(data=request.data)

        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            user_data = User.objects.get(id=serialized_data.get("user_id"))
            statistics_data_entry = StatisticsDateEntry.objects.create(
                bus_unique_code=serialized_data.get("bus_unique_code"),
                total_ticket_amount=serialized_data.get("total_ticket_amount"),
                total_adult_passengers=serialized_data.get("total_adult_passengers"),
                total_child_passengers=serialized_data.get("total_child_passengers"),
                mhl_adult_passengers=serialized_data.get("mhl_adult_passengers"),
                mhl_child_passengers=serialized_data.get("mhl_child_passengers"),
                mhl_adult_amount=serialized_data.get("mhl_adult_amount"),
                mhl_child_amount=serialized_data.get("mhl_child_amount"),
                entry_type="down",
                # service_operated_date=serialized_data.get("user_id"),
                status=0,
                created_by=user_data
            )
            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "Down Journey Data Added Successfully.",
                "result": []
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })


class GetAllHSDOilSubmissionAPIView(APIView):
    def get(self, request):
        hsd_oil_submission_instances = HsdOilSubmission.objects.filter(~Q(status=2))
        hsd_oil_submission_details = [instance.get_complete_details() for instance in hsd_oil_submission_instances]
        return Response(status=status.HTTP_200_OK, data={
            "code": "Success",
            "message": "All HSD Oil Submission Data Fetched Successfully.",
            "result": hsd_oil_submission_details
        })


class HSDOilSubmissionAPIView(APIView):
    def get(self, request):
        hsd_oil_submission_id = request.GET.get("hsd_oil_submission_id")
        serializer_instance = app_serializers.GetHSDOilSubmissionSerializer(
            data={"hsd_oil_submission_id": hsd_oil_submission_id}
        )
        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            down_journey_instance = HsdOilSubmission.objects.get(
                id=serialized_data.get("hsd_oil_submission_id")
            )
            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "HSD Oil Submission Data Fetched Successfully.",
                "result": down_journey_instance.get_complete_details()
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })

    def post(self, request):
        serializer_instance = app_serializers.HSDOilSubmissionSerializer(data=request.data)

        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            vehicle_detail_data = VehicleDetails.objects.get(bus_number=serialized_data.get("bus_number"))
            special_bus_data = SpecialBusDataEntry.objects.get(bus_number=vehicle_detail_data)
            user_data = User.objects.get(id=serialized_data.get("user_id"))
            hsd_oil_submission_detail = HsdOilSubmission.objects.create(
                special_bus_data_entry=special_bus_data,
                hsd_liters=serialized_data.get("hsd_liters"),
                mts_no=serialized_data.get("mts_no"),
                point_name=serialized_data.get("point_name"),
                created_by=user_data,
                unique_no_bus_no=serialized_data.get("unique_no_bus_no"),
                status=0
            )
            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "HSD Oil Subimission Data Added Successfully.",
                "result": []
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })


class GetAllBusesOnHandAPIView(APIView):
    def get(self, request):
        buses_on_hand_instances = BusesOnHand.objects.filter(~Q(status=2))
        buses_on_details = [instance.get_complete_details() for instance in buses_on_hand_instances]
        return Response(status=status.HTTP_200_OK, data={
            "code": "Success",
            "message": "All Buses On hand Data Fetched Successfully.",
            "result": buses_on_details
        })


class BusesOnHandAPIView(APIView):
    def get(self, request):
        buses_on_hand_id = request.GET.get("buses_on_hand_id")
        serializer_instance = app_serializers.GetBusesOnHandSerializer(
            data={"buses_on_hand_id": buses_on_hand_id}
        )
        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            buses_on_hand_instance = BusesOnHand.objects.get(
                id=serialized_data.get("buses_on_hand_id")
            )
            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "Buses On Hand Data Fetched Successfully.",
                "result": buses_on_hand_instance.get_complete_details()
            })
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })

    def post(self, request):
        serializer_instance = app_serializers.BusesOnHandSerializer(data=request.data)

        if not serializer_instance.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer_instance.errors)

        serialized_data = serializer_instance.validated_data

        try:
            out_depot_vehicle_receive_data = OutDepotVehicleReceive.objects.get(
                unique_no=serialized_data.get("unique_code")
            )
            special_bus_data = out_depot_vehicle_receive_data.special_bus_data_entry
            point_name_data = PointData.objects.get(point_name=serialized_data.get("point_name"))
            user_data = User.objects.get(id=serialized_data.get("user_id"))
            buses_on_hand_detail = BusesOnHand.objects.create(
                unique_code=serialized_data.get("unique_code"),
                status=0,
                special_bus_data_entry=special_bus_data,
                created_by=user_data,
                bus_in_out=serialized_data.get("bus_in_out"),
                point_name=point_name_data
            )

            return Response(status=status.HTTP_200_OK, data={
                "code": "Success",
                "message": "Buses On Hand Data Added Successfully.",
                "result": []
            })
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                "code": "Fail",
                "message": "Something Went Wrong.",
                "result": []
            })


class PointNameAPIView(APIView):
    def get(self, request):
        point_name_instances = PointData.objects.filter(~Q(status=2))
        point_name_details = [instance.get_details() for instance in point_name_instances]
        return Response(status=status.HTTP_200_OK, data={
            "code": "Success",
            "message": "All Point Data Fetched Successfully.",
            "result": point_name_details
        })
