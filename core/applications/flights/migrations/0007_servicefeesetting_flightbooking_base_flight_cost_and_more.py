# Generated by Django 5.0.13 on 2025-03-25 14:37

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0006_flight_passengerbooking_paymentdetail_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServiceFeeSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('percentage', models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('is_active', models.BooleanField(default=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddField(
            model_name='flightbooking',
            name='base_flight_cost',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='flightbooking',
            name='service_fee',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='paymentdetail',
            name='additional_details',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='flightbooking',
            name='booking_reference',
            field=models.CharField(default='B73026CE0C', max_length=10, unique=True),
        ),
        migrations.AlterField(
            model_name='passenger',
            name='gender',
            field=models.CharField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], max_length=10),
        ),
    ]
