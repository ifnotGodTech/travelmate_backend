from django.db import migrations, models
from django.utils import timezone

def backfill_ticket_ids(apps, schema_editor):
    Ticket = apps.get_model('tickets', 'Ticket')
    for ticket in Ticket.objects.all().order_by('created_at', 'id'):
        if not ticket.ticket_id:
            year = ticket.created_at.year if ticket.created_at else timezone.now().year
            count = Ticket.objects.filter(
                ticket_id__startswith=f'TKT{year}-'
            ).count()
            ticket.ticket_id = f'TKT{year}-{count+1:03d}'
            ticket.save(update_fields=['ticket_id'])

class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='ticket_id',
            field=models.CharField(max_length=12, null=True, blank=True),
        ),
        migrations.RunPython(backfill_ticket_ids),
        migrations.AlterField(
            model_name='ticket',
            name='ticket_id',
            field=models.CharField(max_length=12, unique=True, editable=False),
        ),
    ]