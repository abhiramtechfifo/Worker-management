import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_alter_assignment_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='OwnerPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('note', models.CharField(blank=True, max_length=255)),
                ('date', models.DateField(default=django.utils.timezone.localdate)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owner_payments', to='api.owner')),
            ],
        ),
    ]
