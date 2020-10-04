# Generated by Django 3.0.7 on 2020-10-04 07:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('swickapp', '0006_meal_enabled'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='meal',
            name='restaurant',
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256)),
                ('restaurant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='swickapp.Restaurant')),
            ],
        ),
        migrations.AlterField(
            model_name='meal',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='meal', to='swickapp.Category'),
        ),
    ]
