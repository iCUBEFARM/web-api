# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-11-21 13:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('icf_item', '0005_auto_20181121_1735'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itemdraft',
            name='slug',
            field=models.SlugField(blank=True),
        ),
    ]
