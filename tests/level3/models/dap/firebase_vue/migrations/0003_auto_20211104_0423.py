# Generated by Django 3.2 on 2021-11-04 04:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('firebase_vue', '0002_rename_lev_user_grp'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='salt',
            field=models.CharField(blank=True, max_length=24, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='signature',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
