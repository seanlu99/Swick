# Generated by Django 3.0.6 on 2020-05-12 19:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swickapp', '0008_auto_20200512_1920'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ordermeal',
            name='quantity',
            field=models.IntegerField(),
        ),
    ]