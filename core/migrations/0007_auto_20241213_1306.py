# Generated by Django 5.1.3 on 2024-12-13 05:06

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_auto_20241213_1300'),
    ]

    operations = [
        migrations.AddField(
            model_name='interview',
            name='address',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
    ]