from django.db import models


# Create your models here.


class PointData(models.Model):
    point_name = models.CharField(max_length=256, null=True, blank=True)
    depot_name = models.ForeignKey("Depot", on_delete=models.CASCADE, null=True, blank=True)
    region = models.CharField(max_length=256, null=True, blank=True)
    zone = models.CharField(max_length=256, null=True, blank=True)
    status = models.IntegerField(help_text="0=active;1=inactive;2=delete", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_details(self):
        return{
            "id":self.id,
            "point_names":self.point_name
        }


class User(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=256, null=True, blank=True)
    email = models.CharField(max_length=256, null=True, blank=True)
    password = models.CharField(max_length=256, null=True, blank=True)
    phone_number = models.CharField(max_length=256, null=True, blank=True)
    user_type = models.ForeignKey("UserType", on_delete=models.CASCADE, null=True)
    depot = models.ForeignKey("Depot", on_delete=models.CASCADE, null=True)
    point_name = models.ForeignKey(PointData, on_delete=models.CASCADE, related_name="user_point_data",
                                   null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.IntegerField(help_text="0=active;1=inactive;2=delete")

    def get_details(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone_number,
            # "user_type": self.user_type
        }

    def display_password(self, requesting_user_type):
        # Check if the requesting user type is 'Super Admin'
        if requesting_user_type == 'Super_admin':
            # You can add additional checks based on your requirements
            # Display the password for Super Admin
            return self.password
        else:
            return "Permission denied"


class UserType(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=256, null=True, blank=True)
    employee_designation = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.IntegerField(help_text="0=active;1=inactive;2=delete")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_type_created_user', default="",
                                   null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_type_updated_user', null=True,
                                   blank=True, default="")


class Depot(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=256, null=True, blank=True)
    depot_code = models.CharField(max_length=256, null=True, blank=True)
    buses_allotted = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.IntegerField(help_text="0=active;1=inactive;2=delete")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='depot_created_user', default="",
                                   null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='depot_updated_user', null=True,
                                   blank=True, default="")

    def get_details(self):
        return {
            "id": self.id,
            "name": self.name,
            "depot_code": self.depot_code
        }


class Vehicle(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=256, null=True, blank=True)
    vehicle_owner = models.CharField(max_length=256, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.IntegerField(help_text="0=active;1=inactive;2=delete")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicle_created_user', default="",
                                   null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicle_updated_user', null=True,
                                   blank=True, default="")


class OperationType(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=256, null=True, blank=True)
    description = models.CharField(max_length=256, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.IntegerField(help_text="0=active;1=inactive;2=delete")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='opt_type_created_user', default="",
                                   null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='opt_type_updated_user', null=True,
                                   blank=True, default="")

    def get_details(self):
        return {
            "id": self.id,
            "name": self.name
        }


# bus_number means vechicle_no

class VehicleDetails(models.Model):
    id = models.AutoField(primary_key=True)
    depot = models.ForeignKey(Depot, on_delete=models.CASCADE, related_name="vehicle_details_depot")
    depot_name = models.CharField(max_length=256, null=True, blank=True)
    bus_number = models.CharField(max_length=256, null=True, blank=True)
    opt_type = models.ForeignKey(OperationType, on_delete=models.CASCADE, related_name="vehicle_details_opt_type")
    vehicle_name = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="vehicle_details_vehicle")
    region_name = models.CharField(max_length=256, null=True, blank=True)
    zone_name = models.CharField(max_length=256, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    vehicle_owner = models.CharField(max_length=256, null=True, blank=True)
    status = models.IntegerField(help_text="0=active;1=inactive;2=delete")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicle_details_created_user',
                                   default="", null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicle_details_updated_user',
                                   null=True, blank=True, default="")

    def get_details(self):
        return {
            "id": self.id,
            "bus_number": self.bus_number
        }


# bus_type means operation_type
# bus_number means vechicle_no

class SpecialBusDataEntry(models.Model):
    id = models.AutoField(primary_key=True)
    special_bus_sending_depot = models.ForeignKey(Depot, on_delete=models.CASCADE,
                                                  related_name="special_bus_sending_depot")
    special_bus_reporting_depot = models.ForeignKey(Depot, on_delete=models.CASCADE,
                                                    related_name="special_bus_reporting_depot")
    bus_type = models.ForeignKey(OperationType, on_delete=models.CASCADE, related_name="special_bus_opt_type")
    bus_number = models.ForeignKey(VehicleDetails, on_delete=models.CASCADE, related_name="special_bus_vehicle")
    log_sheet_no = models.CharField(max_length=256, null=True, blank=True)
    driver1_name = models.CharField(max_length=256, null=True, blank=True)
    driver1_staff_no = models.CharField(max_length=256, null=True, blank=True)
    driver1_phone_number = models.CharField(max_length=256, null=True, blank=True)
    driver2_name = models.CharField(max_length=256, null=True, blank=True)
    driver2_staff_no = models.CharField(max_length=256, null=True, blank=True)
    driver2_phone_number = models.CharField(max_length=256, null=True, blank=True)
    incharge_name = models.CharField(max_length=256, null=True, blank=True)
    incharge_phone_number = models.CharField(max_length=256, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.IntegerField(help_text="0=active;1=inactive;2=delete")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='special_bus_created_user',
                                   default="", null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='special_bus_updated_user',
                                   null=True, blank=True, default="")

    def get_basic_details(self):
        return {
            "id": self.id,
            "bus_sending_depot": self.special_bus_sending_depot.name,
            "bus_reporting_depot": self.special_bus_reporting_depot.name,
            "bus_type": self.bus_type.name,
            "bus_number": self.bus_number.bus_number,
        }

    def get_complete_detail(self):
        return {
            "bus_sending_depot": self.special_bus_sending_depot.name,
            "bus_reporting_depot": self.special_bus_reporting_depot.name,
            "bus_type": self.bus_type.name,
            "bus_number": self.bus_number.bus_number,
            "log_sheet_no": self.log_sheet_no,
            "driver1_name": self.driver1_name,
            "driver1_staff_no": self.driver1_staff_no,
            "driver1_phone_number": self.driver1_phone_number,
            "driver2_name": self.driver2_name,
            "driver2_staff_no": self.driver2_staff_no,
            "driver2_phone_number": self.driver2_phone_number,
            "incharge_name": self.incharge_name,
            "incharge_phone_no": self.incharge_phone_number,
        }


class OutDepotVehicleReceive(models.Model):
    bus_number = models.ForeignKey(VehicleDetails, on_delete=models.CASCADE, related_name="out_depot_bus_vehicle")
    special_bus_data_entry = models.ForeignKey(SpecialBusDataEntry, on_delete=models.CASCADE,
                                               related_name="out_depot_special_bus")
    out_depot_bus_sending_depot = models.ForeignKey(Depot, on_delete=models.CASCADE,
                                                    related_name="out_depot_bus_sending_depot", null=True, blank=True)
    out_depot_bus_reporting_depot = models.ForeignKey(Depot, on_delete=models.CASCADE,
                                                      related_name="out_depot_bus_reporting_depot", null=True,
                                                      blank=True)
    unique_no = models.CharField(max_length=256, null=True, blank=True)
    new_log_sheet_no = models.IntegerField()
    hsd_top_oil_liters = models.IntegerField()
    mts_no = models.IntegerField()
    bus_reported_date = models.DateField(null=True, blank=True)
    bus_reported_time = models.TimeField(null=True, blank=True)
    status = models.IntegerField(help_text="0=active;1=inactive;2=delete", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='out_depot_vehicle_created_user',
                                   null=True, blank=True, default="")
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='out_depot_vehicle_updated_user',
                                   null=True, blank=True, default="")

    def get_complete_details(self):
        return {
            # "id":self.id,
            "bus_number": self.bus_number.bus_number,
            "unique_no": self.unique_no,
            "new_log_sheet_no": self.new_log_sheet_no,
            "hsd_top_oil_liters": self.hsd_top_oil_liters,
            "mts_no": self.mts_no,
            "bus_reported_date": self.bus_reported_date,
            "bus_reported_time": self.bus_reported_time,
        }


class OutDepotVehicleSentBack(models.Model):
    unique_no = models.CharField(max_length=256, null=True, blank=True)
    bus_number = models.CharField(max_length=256, null=True, blank=True)
    log_sheet_no = models.CharField(max_length=256, null=True, blank=True)
    special_bus_data_entry = models.ForeignKey(SpecialBusDataEntry, on_delete=models.CASCADE,
                                               related_name="out_depot_vehicle_sent_special_bus")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='out_depot_vehicle_sent_created_user',
                                   null=True, blank=True, default="")
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='out_depot_vehicle_sent_updated_user',
                                   null=True, blank=True, default="")
    status = models.IntegerField(help_text="0=active;1=inactive;2=delete", null=True, blank=True)

    def get_complete_details(self):
        return {
            # "id":self.id,
            "unique_no": self.unique_no,
            "bus_number": self.bus_number,
            "log_sheet_no": self.log_sheet_no,
        }


class OwnDepotBusDetailsEntry(models.Model):
    bus_number = models.ForeignKey(VehicleDetails, on_delete=models.CASCADE, related_name="own_depot_bus_detail_vehicle_details",
                                   null=True, blank=True)
    unique_no = models.CharField(max_length=256, null=True, blank=True)
    bus_type = models.CharField(max_length=256, null=True, blank=True)
    log_sheet_no = models.CharField(max_length=256, null=True, blank=True)
    driver1_name = models.CharField(max_length=256, null=True, blank=True)
    driver1_phone_number = models.CharField(max_length=256, null=True, blank=True)
    driver1_staff_no = models.CharField(max_length=256, null=True, blank=True)
    driver2_name = models.CharField(max_length=256, null=True, blank=True)
    driver2_phone_number = models.CharField(max_length=256, null=True, blank=True)
    driver2_staff_no = models.CharField(max_length=256, null=True, blank=True)
    incharge_name = models.CharField(max_length=256, null=True, blank=True)
    incharge_phone_number = models.CharField(max_length=256, null=True, blank=True)
    depot = models.ForeignKey(Depot, on_delete=models.CASCADE, null=True, blank=True)
    status = models.IntegerField(help_text="0=active;1=inactive;2=delete")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='own_depot_bus_details_entry_created_user',
                                   null=True, blank=True, default="")
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='own_depot_bus_details_entry_updated_user',
                                   null=True, blank=True, default="")

    def get_complete_details(self):
        return {
            # "id":self.id,
            "bus_number": self.bus_number,
            "unique_no": self.unique_no,
            "bus_type": self.bus_type,
            "log_sheet_no": self.log_sheet_no,
            "driver1_name": self.driver1_name,
            "driver1_phone_number": self.driver1_phone_number,
            "driver2_name": self.driver2_name,
            "driver2_phone_number": self.driver2_phone_number,
        }


class OwnDepotBusWithdraw(models.Model):
    bus_number = models.CharField(max_length=256, null=True, blank=True)
    depot = models.ForeignKey(Depot, on_delete=models.CASCADE, null=True, blank=True)
    status = models.IntegerField(help_text="0=active;1=inactive;2=delete")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='own_depot_bus_withdraw_created_user',
                                   null=True, blank=True, default="")
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='own_depot_bus_withdraw_updated_user',
                                   null=True, blank=True, default="")

    def get_complete_details(self):
        return {
            # "id":self.id,
            "bus_number": self.bus_number,
        }


class TripStatistics(models.Model):
    id = models.AutoField(primary_key=True)
    unique_code = models.CharField(max_length=256, null=True, blank=True)
    bus_number = models.CharField(max_length=256, null=True, blank=True)
    total_ticket_amount = models.IntegerField(null=True, blank=True)
    total_adult_passengers = models.IntegerField(null=True, blank=True)
    total_child_passengers = models.IntegerField(null=True, blank=True)
    mhl_adult_passengers = models.IntegerField(null=True, blank=True)
    mhl_child_passengers = models.IntegerField(null=True, blank=True)
    mhl_adult_amount = models.IntegerField(null=True, blank=True)
    mhl_child_amount = models.IntegerField(null=True, blank=True)
    entry_type = models.CharField(max_length=256, null=True, blank=True)
    start_from_location = models.ForeignKey(PointData, on_delete=models.CASCADE,
                                            related_name="statistic_start_from_location_point_data",
                                            null=True, blank=True)
    start_to_location = models.ForeignKey(PointData, on_delete=models.CASCADE,
                                          related_name="statistic_start_to_location_point_data",
                                          null=True, blank=True)
    service_operated_date = models.DateField(null=True, blank=True)
    data_enter_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='statistics_data_entry_by',
                                      null=True, blank=True)
    trip_verify_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                       related_name='statistics_data_verify_by', default="", null=True,
                                       blank=True)
    trip_start = models.DateTimeField(auto_now_add=True)
    trip_end = models.DateTimeField(null=True, blank=True)
    trip_verified = models.BooleanField(default=False)
    trip_verified_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.IntegerField(help_text="0=active;1=inactive;2=delete")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='statistics_data_entry_created_user',
                                   default="", null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='statistics_data_entry_updated_user',
                                   null=True, blank=True, default="")

    def get_complete_details(self):
        return {
            "id": self.id,
            "bus_unique_code": self.bus_unique_code,
            "total_ticket_amount": self.total_ticket_amount,
            "total_adult_passengers": self.total_adult_passengers,
            "total_child_passengers": self.total_child_passengers,
            "mhl_adult_passengers": self.mhl_adult_passengers,
            "mhl_child_passengers": self.mhl_child_passengers,
            "mhl_adult_amount": self.mhl_adult_amount,
            "mhl_child_amount": self.mhl_child_amount,
        }


class HsdOilSubmission(models.Model):
    mts_no = models.IntegerField(null=True, blank=True)
    hsd_liters = models.IntegerField(null=True, blank=True)
    unique_no_bus_no = models.CharField(max_length=256, null=True, blank=True)
    point_name = models.CharField(max_length=256, null=True, blank=True)
    special_bus_data_entry = models.ForeignKey(SpecialBusDataEntry, on_delete=models.CASCADE,
                                               related_name="hsd_oil_submission_special_bus")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='hsd_oil_submission_created_user',
                                   null=True, blank=True, default="")
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='hsd_oil_submission_updated_user',
                                   null=True, blank=True, default="")
    status = models.IntegerField(help_text="0=active;1=inactive;2=delete", null=True, blank=True)
    shift = models.CharField(max_length=256, null=True, blank=True)

    def get_complete_details(self):
        return {
            # "id":self.id,
            "hsd_liters": self.hsd_liters,
            "mts_no": self.mts_no,
            "unique_no_bus_no": self.unique_no_bus_no,
            "point_name": self.point_name,
            "spl_bus_entry_id": self.special_bus_data_entry.id
        }


class BusesOnHand(models.Model):
    point_name = models.ForeignKey(PointData, on_delete=models.CASCADE, related_name="buses_on_hand_point_data",
                                   null=True, blank=True)
    unique_code = models.CharField(max_length=256, null=True, blank=True)
    bus_in_out = models.CharField(max_length=256, null=True, blank=True)
    special_bus_data_entry = models.ForeignKey(SpecialBusDataEntry, on_delete=models.CASCADE,
                                               related_name="buses_on_hand_special_bus")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='buses_on_hand_created_user',
                                   null=True, blank=True, default="")
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='buses_on_hand_updated_user',
                                   null=True, blank=True, default="")
    status = models.IntegerField(help_text="0=active;1=inactive;2=delete", null=True, blank=True)

    def get_complete_details(self):
       return{
           # "id":self.id,
           "point_name":self.point_name.point_name,
           "unique_code":self.unique_code,
           "bus_in_out":self.bus_in_out,
           "spl_bus_entry_id":self.special_bus_data_entry.id
       }