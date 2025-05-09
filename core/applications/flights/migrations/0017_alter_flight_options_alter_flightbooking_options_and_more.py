# Generated by Django 5.0.13 on 2025-03-30 04:25

import auto_prefetch
import core.applications.flights.models
import django.db.models.deletion
import django.db.models.manager
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0016_alter_flightbooking_booking_reference'),
        ('stay', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='flight',
            options={'base_manager_name': 'prefetch_manager'},
        ),
        migrations.AlterModelOptions(
            name='flightbooking',
            options={'base_manager_name': 'prefetch_manager'},
        ),
        migrations.AlterModelOptions(
            name='passengerbooking',
            options={'base_manager_name': 'prefetch_manager'},
        ),
        migrations.AlterModelOptions(
            name='paymentdetail',
            options={'base_manager_name': 'prefetch_manager'},
        ),
        migrations.AlterModelManagers(
            name='flight',
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('prefetch_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='flightbooking',
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('prefetch_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='passengerbooking',
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('prefetch_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='paymentdetail',
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('prefetch_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.RemoveField(
            model_name='flight',
            name='booking',
        ),
        migrations.RemoveField(
            model_name='flightbooking',
            name='booking_status',
        ),
        migrations.RemoveField(
            model_name='flightbooking',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='flightbooking',
            name='total_price',
        ),
        migrations.RemoveField(
            model_name='flightbooking',
            name='updated_at',
        ),
        migrations.RemoveField(
            model_name='flightbooking',
            name='user',
        ),
        migrations.RemoveField(
            model_name='passengerbooking',
            name='booking',
        ),
        migrations.AddField(
            model_name='flight',
            name='flight_booking',
            field=auto_prefetch.ForeignKey(default='1', on_delete=django.db.models.deletion.CASCADE, related_name='flights', to='flights.flightbooking'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='flightbooking',
            name='booking',
            field=auto_prefetch.OneToOneField(default='1', on_delete=django.db.models.deletion.CASCADE, related_name='flight_booking', to='stay.booking'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='passengerbooking',
            name='flight_booking',
            field=auto_prefetch.ForeignKey(default='1', on_delete=django.db.models.deletion.CASCADE, related_name='passenger_bookings', to='flights.flightbooking'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='flightbooking',
            name='booking_reference',
            field=models.CharField(default=core.applications.flights.models.FlightBooking.generate_booking_reference, max_length=10, unique=True),
        ),
        migrations.AlterField(
            model_name='passenger',
            name='gender',
            field=models.CharField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], max_length=1),
        ),
        migrations.AlterField(
            model_name='passengerbooking',
            name='passenger',
            field=auto_prefetch.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='flights.passenger'),
        ),
        migrations.AlterField(
            model_name='paymentdetail',
            name='booking',
            field=auto_prefetch.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='payment', to='stay.booking'),
        ),
    ]
