# Generated by Django 5.0.13 on 2025-04-01 11:40

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0019_flightbooking_admin_notes_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='flight',
            options={'base_manager_name': 'prefetch_manager', 'ordering': ['itinerary_index', 'departure_datetime']},
        ),
        migrations.AddField(
            model_name='flight',
            name='aircraft_code',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='flight',
            name='aircraft_name',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='flight',
            name='arrival_terminal',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='flight',
            name='blacklisted_in_eu',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='flight',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='flight',
            name='departure_terminal',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='flight',
            name='duration',
            field=models.DurationField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='flight',
            name='fare_basis',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='flight',
            name='fare_brand',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='flight',
            name='fare_brand_label',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='flight',
            name='fare_class',
            field=models.CharField(blank=True, max_length=1),
        ),
        migrations.AddField(
            model_name='flight',
            name='included_checked_bags',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='flight',
            name='instant_ticketing_required',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='flight',
            name='itinerary_index',
            field=models.PositiveSmallIntegerField(default=0, help_text='Index for ordering flights in multi-city itineraries'),
        ),
        migrations.AddField(
            model_name='flight',
            name='number_of_stops',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='flight',
            name='operating_airline',
            field=models.CharField(blank=True, max_length=3),
        ),
        migrations.AddField(
            model_name='flight',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='flight',
            name='airline_name',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='flight',
            name='cabin_class',
            field=models.CharField(default='ECONOMY', max_length=20),
        ),
    ]
