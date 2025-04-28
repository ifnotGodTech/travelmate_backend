from django.db import migrations, models, connection
from django.db.migrations.operations.base import Operation


class DisableTriggersOperation(Operation):
    def __init__(self):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        schema_editor.execute("SET session_replication_role = replica;")

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        schema_editor.execute("SET session_replication_role = DEFAULT;")

    def state_forwards(self, app_label, state):
        pass

    def describe(self):
        return "Disable triggers during migration"


def convert_escalation_reason_to_text(apps, schema_editor):
    Ticket = apps.get_model('tickets', 'Ticket')
    for ticket in Ticket.objects.all():
        if ticket.escalation_reason_id:
            EscalationReason = apps.get_model('tickets', 'EscalationReason')
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
        # Disable triggers temporarily
        DisableTriggersOperation(),

        # First add temporary text field
        migrations.AddField(
            model_name='ticket',
            name='escalation_reason_text',
            field=models.TextField(blank=True, null=True),
        ),
        
        # Then convert the data
        migrations.RunPython(
            convert_escalation_reason_to_text,
            reverse_code=migrations.RunPython.noop
        ),
        
        # Remove the old ForeignKey field
        migrations.RemoveField(
            model_name='ticket',
            name='escalation_reason',
        ),
        
        # Add the new TextField with the same name
        migrations.AddField(
            model_name='ticket',
            name='escalation_reason',
            field=models.TextField(blank=True, null=True),
        ),

        # Copy data from temporary field
        migrations.RunPython(
            lambda apps, schema_editor: apps.get_model('tickets', 'Ticket').objects.all().update(
                escalation_reason=models.F('escalation_reason_text')
            ),
            reverse_code=migrations.RunPython.noop
        ),

        # Remove the temporary field
        migrations.RemoveField(
            model_name='ticket',
            name='escalation_reason_text',
        ),
        
        # Finally, remove the EscalationReason model
        migrations.DeleteModel(
            name='EscalationReason',
        ),

        # Re-enable triggers
        migrations.RunSQL("SET session_replication_role = DEFAULT;"),
    ]