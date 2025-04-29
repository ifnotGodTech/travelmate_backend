from django.db import migrations, models
from django.db.models import F


def convert_escalation_reason_to_text(apps, schema_editor):
    Ticket = apps.get_model('tickets', 'Ticket')
    EscalationReason = apps.get_model('tickets', 'EscalationReason')
    for ticket in Ticket.objects.all():
        if ticket.escalation_reason_id:
            try:
                reason = EscalationReason.objects.get(id=ticket.escalation_reason_id)
                ticket.escalation_reason_text = reason.reason
                ticket.save(update_fields=['escalation_reason_text'])
            except EscalationReason.DoesNotExist:
                pass


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0002_ticket_ticket_id'),
    ]

    operations = [
        # Step 1: Add temporary text field
        migrations.AddField(
            model_name='Ticket',
            name='escalation_reason_text',
            field=models.TextField(blank=True, null=True),
        ),

        # Step 2: Convert data from foreign key to temporary text field
        migrations.RunPython(
            convert_escalation_reason_to_text,
            reverse_code=migrations.RunPython.noop,
        ),

        # Step 3: Drop the foreign key constraint explicitly (if needed)
        migrations.RunSQL(
            sql="""
            ALTER TABLE tickets_ticket
            DROP CONSTRAINT IF EXISTS tickets_ticket_escalation_reason_id_fkey;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),

        # Step 4: Remove the old ForeignKey field
        migrations.RemoveField(
            model_name='Ticket',
            name='escalation_reason',
        ),

        # Step 5: Add the new TextField with the same name
        migrations.AddField(
            model_name='Ticket',
            name='escalation_reason',
            field=models.TextField(blank=True, null=True),
        ),

        # Step 6: Copy data from temporary field to new field
        migrations.RunPython(
            code=lambda apps, schema_editor: apps.get_model('tickets', 'Ticket').objects.update(
                escalation_reason=F('escalation_reason_text')
            ),
            reverse_code=migrations.RunPython.noop,
        ),

        # Step 7: Remove the temporary field
        migrations.RemoveField(
            model_name='Ticket',
            name='escalation_reason_text',
        ),

        # Step 8: Delete the EscalationReason model
        migrations.DeleteModel(
            name='EscalationReason',
        ),
    ]