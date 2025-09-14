from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_set_consolidated_budget_only'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActiveState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state_code', models.CharField(max_length=2, unique=True)),
                ('state_name', models.CharField(max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Active State',
                'verbose_name_plural': 'Active States',
                'ordering': ['state_name'],
            },
        ),
    ]

