from django.db import migrations


def set_consolidated_budget_only(apps, schema_editor):
    Company = apps.get_model('core', 'Company')
    Company.objects.filter(code='CONSOLIDATED').update(is_budget_only=True)


def unset_consolidated_budget_only(apps, schema_editor):
    Company = apps.get_model('core', 'Company')
    Company.objects.filter(code='CONSOLIDATED').update(is_budget_only=False)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0012_company_is_budget_only'),
    ]

    operations = [
        migrations.RunPython(set_consolidated_budget_only, unset_consolidated_budget_only),
    ]

