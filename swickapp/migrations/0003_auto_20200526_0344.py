# Generated by Django 3.0.6 on 2020-05-26 03:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swickapp', '0002_auto_20200524_0649'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='orderitem',
            name='meal',
        ),
        migrations.RemoveField(
            model_name='orderitemcustomization',
            name='customization',
        ),
        migrations.AddField(
            model_name='orderitem',
            name='meal_name',
            field=models.CharField(default='a', max_length=256),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='orderitemcustomization',
            name='customization_name',
            field=models.CharField(default='b', max_length=256),
            preserve_default=False,
        ),
    ]
