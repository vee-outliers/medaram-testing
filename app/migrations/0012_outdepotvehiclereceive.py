# Generated by Django 3.2.5 on 2024-02-02 11:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0011_auto_20240202_0004'),
    ]

    operations = [
        migrations.CreateModel(
            name='OutDepotVehicleReceive',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unique_no', models.IntegerField()),
                ('new_log_sheet_no', models.IntegerField()),
                ('hsd_top_oil_liters', models.IntegerField()),
                ('mts_no', models.IntegerField()),
                ('bus_reported_date', models.DateField()),
                ('bus_reported_time', models.TimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bus_number', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='out_depot_bus_vehicle', to='app.vehicledetails')),
                ('created_by', models.ForeignKey(blank=True, default='', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='out_depot_vehicle_created_user', to='app.user')),
                ('special_bus_data_entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='out_depot_special_bus', to='app.specialbusdataentry')),
                ('updated_by', models.ForeignKey(blank=True, default='', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='out_depot_vehicle_updated_user', to='app.user')),
            ],
        ),
    ]
