# Generated by Django 3.0.6 on 2020-05-17 21:13

from decimal import Decimal
import django.contrib.postgres.fields
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swickapp', '0022_auto_20200517_2111'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customization',
            name='price_additions',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.DecimalField(decimal_places=2, max_digits=7, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='price additions (separate with commas, insert 0 if no addition)'), size=None),
        ),
    ]