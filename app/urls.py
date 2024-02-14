from django.urls import path
from .views import *
from django.contrib import admin
from . import views

app_name = "app"
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('do_login', views.do_login, name="do_login"),
    path('dashboard', dashboard, name='dashboard'),
    path('logout_user', views.logout_user, name="logout_user"),
    path('show/profile', views.show_profile, name="show_profile"),

    path('users/list', views.users_list, name='users_list'),
    path('users/add', views.user_add, name='user_add'),
    path('users/edit', views.user_edit, name='user_edit'),
    path('users/update', views.user_update, name='user_update'),
    path('get/depot/point/name', views.get_depot_point_names, name='get_depot_point_names'),

    path('user/type/list', views.user_type_list, name='user_type_list'),
    path('user/type/add', views.user_type_add, name='user_type_add'),
    path('user/type/edit', views.user_type_edit, name='user_type_edit'),
    path('user/type/update', views.user_type_update, name='user_type_update'),

    path('depot/list', views.depots_list, name='depots_list'),
    path('depot/add', views.depot_add, name='depot_add'),
    path('depot/edit', views.depot_edit, name='depot_edit'),
    path('depot/update', views.depot_update, name='depot_update'),
    path('depot/import', views.depot_import, name='depot_import'),

    path('operation/type/list', views.operation_type_list, name='operation_type_list'),
    path('operation/type/add', views.operation_type_add, name='operation_type_add'),
    path('operation/type/edit', views.operation_type_edit, name='operation_type_edit'),
    path('operation/type/update', views.operation_type_update, name='operation_type_update'),
    path('operation/type/import', views.operation_type_import, name='operation_type_import'),

    path('vehicle/list', views.vehicle_list, name='vehicle_list'),
    path('vehicle/add', views.vehicle_add, name='vehicle_add'),
    path('vehicle/edit', views.vehicle_edit, name='vehicle_edit'),
    path('vehicle/update', views.vehicle_update, name='vehicle_update'),
    path('vehicle/import', views.vehicle_names_import, name='vehicle_names_import'),

    path('vehicle/details/list', views.vehicle_details_list, name='vehicle_details_list'),
    path('vehicle/details/add', views.vehicle_detail_add, name='vehicle_detail_add'),
    path('vehicle/details/edit', views.vehicle_detail_edit, name='vehicle_detail_edit'),
    path('vehicle/details/update', views.vehicle_detail_update, name='vehicle_detail_update'),
    path('vehicle/details/import', views.vehicle_details_import, name='vehicle_details_import'),

    path('spl/bus/data/entry/list', views.spl_bus_data_entry_list, name='spl_bus_data_entry_list'),
    path('spl/bus/data/entry/add', views.spl_bus_data_entry_add, name='spl_bus_data_entry_add'),
    path('spl/bus/data/entry/edit', views.spl_bus_data_entry_edit, name='spl_bus_data_entry_edit'),
    path('spl/bus/data/entry/update', views.spl_bus_data_entry_update, name='spl_bus_data_entry_update'),
    path('get/depot/vehicle/number', views.get_depot_vehicle_number, name='get_depot_vehicle_number'),

    # path('out/depot/buses/receive/form', views.out_depot_buses_receive_form, name='out_depot_buses_receive_form'),
    path('out/depot/buses/receive/list', views.out_depot_buses_receive_list, name='out_depot_buses_receive_list'),
    path('out/depot/buses/receive/add', views.out_depot_buses_receive_add, name='out_depot_buses_receive_add'),
    path('search/special/bus/data', views.search_special_bus_data, name='search_special_bus_data'),
    path('out/depot/buses/receive/edit', views.out_depot_vehicle_receive_edit, name='out_depot_vehicle_receive_edit'),
    path('out/depot/buses/receive/update', views.out_depot_vehicle_receive_update,
         name='out_depot_vehicle_receive_update'),

    path('own/depot/bus/details/entry/list', views.own_depot_bus_details_entry_list, name='own_depot_bus_details_entry_list'),
    path('own/depot/bus/details/entry/add', views.own_depot_bus_details_entry_add, name='own_depot_bus_details_entry_add'),
    path('own/depot/bus/details/entry/edit', views.own_depot_bus_details_entry_edit, name='own_depot_bus_details_entry_edit'),
    path('own/depot/bus/details/entry/update', views.own_depot_bus_details_entry_update, name='own_depot_bus_details_entry_update'),

    path('own/depot/bus/withdraw/list', views.own_depot_bus_withdraw_list, name='own_depot_bus_withdraw_list'),
    path('own/depot/bus/withdraw/add', views.own_depot_bus_withdraw_add, name='own_depot_bus_withdraw_add'),
    path('own/depot/bus/withdraw/edit', views.own_depot_bus_withdraw_edit, name='own_depot_bus_withdraw_edit'),
    path('own/depot/bus/withdraw/update', views.own_depot_bus_withdraw_update, name='own_depot_bus_withdraw_update'),


    path('statistics/trip/start/add', views.trip_start_add, name='trip_start_add'),
    path('statistics/search/trip/end/form', views.search_trip_end_form, name='search_trip_end_form'),
    path('statistics/trip/end/add', views.trip_end_add, name='trip_end_add'),
    path('get/out/own/depot/bus/number', views.get_out_and_own_depot_bus_number,
         name='get_out_and_own_depot_bus_number'),


    path('out/depot/buses/send/back/list', views.out_depot_vehicle_send_back_list,
         name='out_depot_vehicle_send_back_list'),
    path('out/depot/buses/send/back/add', views.out_depot_vehicle_send_back_add, name='out_depot_vehicle_send_back_add'),
    path('out/depot/buses/send/back/edit', views.out_depot_vehicle_send_back_edit,
         name='out_depot_vehicle_send_back_edit'),
    path('out/depot/buses/send/back/update', views.out_depot_vehicle_send_back_update,
         name='out_depot_vehicle_send_back_update'),
    path('out/depot/buses/send/back/validate/log/sheet', views.validate_log_sheet, name='validate_log_sheet'),
    path('get/out/depot/vehicle/receive/bus/number', views.get_out_depot_vehicle_receive_bus_number,
         name='get_out_depot_vehicle_receive_bus_number'),

    path('hsd/oil/submission/list', views.hsd_oil_submission_list, name='hsd_oil_submission_list'),
    # path('hsd/oil/submission/form', views.hsd_oil_submission_form, name='hsd_oil_submission_form'),
    path('hsd/oil/submission/add', views.hsd_oil_submission_add, name='hsd_oil_submission_add'),
    path('search/unique/bus/number/special/bus/data', views.search_unique_no_bus_no_special_bus_data,
         name='search_unique_no_bus_no_special_bus_data'),
    path('hsd/oil/submission/edit', views.hsd_oil_submission_edit, name='hsd_oil_submission_edit'),
    path('hsd/oil/submission/update', views.hsd_oil_submission_update, name='hsd_oil_submission_update'),

    path('buses/on/hand/list', views.buses_on_hand_list, name='buses_on_hand_list'),
    path('buses/on/hand/add', views.buses_on_hand_add, name='buses_on_hand_add'),
    path('buses/on/hand/edit', views.buses_on_hand_edit, name='buses_on_hand_edit'),
    path('buses/on/hand/update', views.buses_on_hand_update, name='buses_on_hand_update'),

    path('reports/summary/sending/buses/list', views.summary_sending_buses_list, name='summary_sending_buses_list'),

    path('reports/buses/dispatched/list', views.buses_dispatched_list, name='buses_dispatched_list'),
    path('reports/buses/dispatched/display/details', views.buses_dispatched_display_details, name='buses_dispatched_display_details'),

    path('reports/buses/reached/list', views.buses_reached_list, name='buses_reached_list'),
    path('reports/buses/reached/display/details', views.buses_reached_display_details, name='buses_reached_display_details'),

    path('reports/buses/not/reached/list', views.buses_not_reached_list, name='buses_not_reached_list'),
    path('reports/buses/not/reached/display/details', views.buses_not_reached_display_details,
         name='buses_not_reached_display_details'),


    path('reports/search/depot/list', views.search_depot_list, name='search_depot_list'),
    path('reports/display/operating/depot/list', views.display_operating_depot_list, name='display_operating_depot_list'),

    path('reports/status/return/back/buses/list', views.status_return_back_buses_list,
         name='status_return_back_buses_list'),
    path('reports/buses/sending/back/list', views.buses_sending_back_list,
         name='buses_sending_back_list'),

    path('reports/search/handling/bus/details/list', views.search_handling_bus_details_list, name='search_handling_bus_details_list'),
    path('reports/display/unique/no/crew/details', views.display_unique_no_crew_details, name='display_unique_no_crew_details'),
    path('reports/display/bus/no/crew/details', views.display_bus_no_crew_details,
         name='display_bus_no_crew_details'),

    path('reports/search/bus/details', views.search_bus_details, name='search_bus_details'),

    path('reports/search/route/wise/buses/to/list', views.search_route_wise_buses_to_list, name='search_route_wise_buses_to_list'),
    path('reports/search/route/wise/buses/from/list', views.search_route_wise_buses_from_list,
         name='search_route_wise_buses_from_list'),

    path('reports/search/hour/wise/dispatched/buses/list', views.search_hour_wise_dispatched_buses_list,
         name='search_hour_wise_dispatched_buses_list'),


    path('reports/en/route/wise/buses/list', views.en_route_wise_list, name='en_route_wise_list'),
    path('reports/en/route/wise/bus/details', views.en_route_bus_details, name='en_route_bus_details'),

    path('point_data/list', views.point_data_list, name='point_data_list'),
    path('point_data/import', views.point_data_import, name='point_data_import'),
    path('point_data/add', views.point_name_add, name='point_name_add'),
    path('point_data/edit', views.point_name_edit, name='point_name_edit'),
    path('point_data/update', views.point_name_update, name='point_name_update'),

    path('reports/dashboard/details/list', views.dashboard_details_list, name='dashboard_details_list'),
    path('reports/dashboard/details/entry/type/list', views.dashboard_details_entry_type,
         name='dashboard_details_entry_type'),

    path('api/create/user/', views.create_user, name='create_user'),

    # Medaram REST API STARTS FROM HERE
    path("api/login/", views.LoginAPIView.as_view()),
    path("api/get-all-depot/", views.DepotAPIView.as_view()),
    path("api/get-all-operation-type/", views.OperationTypeAPIView.as_view()),
    path("api/get-all-special-bus-entry/", views.AllSplBusEntryAPIView.as_view()),
    path("api/get-depot-vehicle/", views.DepotVehicleAPIView.as_view()),
    path("api/special-bus-entry/", views.SplBusEntryAPIView.as_view()),

    path("api/search-bus-number/", views.SearchBusNumberAPI.as_view()),

    path("api/get-all-out-depot-vehicle-receive/", views.GetAllOutDepotVehicleReceiveAPIView.as_view()),
    path("api/out-depot-vehicle-receive/", views.OutDepotVehicleReceiveAPIView.as_view()),

    path("api/get-all-out-depot-vehicle-send-back/", views.GetAllOutDepotVehicleSendBackAPIView.as_view()),
    path("api/out-depot-vehicle-send-back/", views.OutDepotVehicleSendBackAPIView.as_view()),

    path("api/get-all-own-depot-bus-detail/", views.GetAllOwnDepotBusDetailAPIView.as_view()),
    path("api/own-depot-bus-detail/", views.OwnDepotBusDetailAPIView.as_view()),

    path("api/get-all-own-depot-bus-withdraw/", views.GetAllOwnDepotBusWithdrawAPIView.as_view()),
    path("api/own-depot-bus-withdraw/", views.OwnDepotBusWithdrawAPIView.as_view()),

    path("api/get-all-up-journey/", views.GetAllUpJourneyAPIView.as_view()),
    path("api/up-journey/", views.UpJourneyAPIView.as_view()),

    path("api/get-all-down-journey/", views.GetAllDownJourneyAPIView.as_view()),
    path("api/down-journey/", views.DownJourneyAPIView.as_view()),

    path("api/get-all-hsd-oil-submission/", views.GetAllHSDOilSubmissionAPIView.as_view()),
    path("api/hsd-oil-submission/", views.HSDOilSubmissionAPIView.as_view()),

    path("api/get-all-buses-on-hand/", views.GetAllBusesOnHandAPIView.as_view()),
    path("api/buses-on-hand/", views.BusesOnHandAPIView.as_view()),

    path("api/get-all-point-names/", views.PointNameAPIView.as_view()),

]
