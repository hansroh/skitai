# Generated by Django 3.2 on 2021-11-04 05:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('firebase_vue', '0005_auto_20211104_0430'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='grp',
            field=models.CharField(choices=[('guest', 'guest'), ('user', 'user'), ('staff', 'staff'), ('admin', 'admin')], default='user', max_length=16),
        ),
    ]
