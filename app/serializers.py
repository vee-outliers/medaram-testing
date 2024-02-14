from rest_framework import serializers

class LoginSerializer(serializers.Serializer):
    user_email_phone = serializers.CharField(required=True)
    user_password = serializers.CharField(required=True)

class DepotVehicleSerializer(serializers.Serializer):
    special_bus_sending_depot = serializers.IntegerField(required=True)

class GetSplBusDataEntrySerializer(serializers.Serializer):
    special_bus_data_id = serializers.IntegerField(required=True)

class SplBusEntrySerializer(serializers.Serializer):
    bus_sending_depot = serializers.IntegerField(required=True)
    bus_reporting_depot = serializers.IntegerField(required=True)
    bus_type = serializers.IntegerField(required=True)
    bus_number = serializers.IntegerField(required=True)
    log_sheet_no = serializers.CharField(required=True)
    driver1_name = serializers.CharField(required=True)
    driver1_staff_no = serializers.CharField(required=True)
    driver1_phone_number = serializers.CharField(required=True)
    driver2_name = serializers.CharField(required=True)
    driver2_staff_no = serializers.CharField(required=True)
    driver2_phone_number = serializers.CharField(required=True)
    incharge_name = serializers.CharField(required=True)
    incharge_phone_no = serializers.CharField(required=True)

class SearchBusNumberSerializer(serializers.Serializer):
    bus_number = serializers.CharField(required=True)

class GetOutDepotVehicleReceiveSerializer(serializers.Serializer):
    out_depot_vehicle_receive_id = serializers.IntegerField(required=True)

class OutDepotVehicleReceiveSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    bus_number = serializers.CharField(required=True)
    unique_no = serializers.IntegerField(required=True)
    new_log_sheet_no = serializers.IntegerField(required=True)
    hsd_top_oil_lts = serializers.IntegerField(required=True)
    mts_no = serializers.IntegerField(required=True)
    bus_reported_date = serializers.CharField(required=True)
    bus_reported_time = serializers.CharField(required=True)

class GetOutDepotVehicleSendBackSerializer(serializers.Serializer):
    out_depot_vehicle_send_back_id = serializers.IntegerField(required=True)

class OutDepotVehicleSendBackSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    unique_no = serializers.CharField(required=True)
    bus_number = serializers.CharField(required=True)
    log_sheet_no = serializers.IntegerField(required=True)

class GetOwnDepotBusDetailSerializer(serializers.Serializer):
    own_depot_bus_detail_id = serializers.IntegerField(required=True)

class OwnDepotBusDetailSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    bus_number = serializers.CharField(required=True)
    unique_number = serializers.CharField(required=True)
    bus_type = serializers.CharField(required=True)
    log_sheet_no = serializers.IntegerField(required=True)
    driver1_name = serializers.CharField(required=True)
    driver1_phone_number = serializers.CharField(required=True)
    driver2_name = serializers.CharField(required=True)
    driver2_phone_number = serializers.CharField(required=True)

class GetOwnDepotBusWithdrawSerializer(serializers.Serializer):
    own_depot_bus_withdraw_id = serializers.IntegerField(required=True)

class OwnDepotBusWithdrawSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    bus_number = serializers.CharField(required=True)

class GetUpJourneySerializer(serializers.Serializer):
    up_journey_id = serializers.IntegerField(required=True)

class GetDownJourneySerializer(serializers.Serializer):
    down_journey_id = serializers.IntegerField(required=True)

class UpDownJourneySerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    bus_unique_code = serializers.IntegerField(required=True)
    total_ticket_amount = serializers.IntegerField(required=True)
    total_adult_passengers = serializers.IntegerField(required=True)
    total_child_passengers = serializers.IntegerField(required=True)
    mhl_adult_passengers = serializers.IntegerField(required=True)
    mhl_child_passengers = serializers.IntegerField(required=True)
    mhl_adult_amount = serializers.IntegerField(required=True)
    mhl_child_amount = serializers.IntegerField(required=True)

class GetHSDOilSubmissionSerializer(serializers.Serializer):
    hsd_oil_submission_id = serializers.IntegerField(required=True)

class HSDOilSubmissionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    bus_number = serializers.CharField(required=True)
    unique_no_bus_no = serializers.CharField(required=True)
    point_name = serializers.CharField(required=True)
    hsd_liters = serializers.CharField(required=True)
    mts_no = serializers.CharField(required=True)

class GetBusesOnHandSerializer(serializers.Serializer):
   buses_on_hand_id = serializers.IntegerField(required=True)

class BusesOnHandSerializer(serializers.Serializer):
   user_id = serializers.IntegerField(required=True)
   point_name = serializers.CharField(required=True)
   unique_code = serializers.CharField(required=True)
   bus_in_out = serializers.CharField(required=True)