# Generated by Django 5.0.13 on 2025-03-26 18:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cars', '0005_booking_transfer_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='passengers',
            field=models.IntegerField(default=1),
        ),
    ]
