# Generated by Django 3.0.6 on 2020-05-11 23:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swickapp', '0002_remove_restaurant_restaurant_phone_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='restaurant',
            name='restaurant_image',
            field=models.ImageField(upload_to=''),
        ),
    ]