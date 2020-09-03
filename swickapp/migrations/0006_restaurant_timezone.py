# Generated by Django 3.0.7 on 2020-09-03 19:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swickapp', '0005_auto_20200812_2140'),
    ]

    operations = [
        migrations.AddField(
            model_name='restaurant',
            name='timezone',
            field=models.CharField(choices=[('ALASKA', 'US/Alaska'), ('ARIZONA', 'US/Arizona'), ('EASTERN', 'US/Eastern'), ('HAWAII', 'US/Hawaii'), ('CENTRAL', 'US/Central'), ('MOUNTAIN', 'US/Mountain'), ('PACIFIC', 'US/Pacific')], default='EASTERN', max_length=16),
            preserve_default=False,
        ),
    ]
