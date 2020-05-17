# Generated by Django 3.0.6 on 2020-05-13 07:55

from decimal import Decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swickapp', '0013_auto_20200513_0225'),
    ]

    operations = [
        migrations.AlterField(
            model_name='meal',
            name='price',
            field=models.DecimalField(decimal_places=2, max_digits=7, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]),
        ),
        migrations.AlterField(
            model_name='order',
            name='total',
            field=models.DecimalField(decimal_places=2, max_digits=7),
        ),
        migrations.AlterField(
            model_name='ordermeal',
            name='total',
            field=models.DecimalField(decimal_places=2, max_digits=7),
        ),
    ]