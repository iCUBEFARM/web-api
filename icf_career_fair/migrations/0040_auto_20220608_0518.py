# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2022-06-08 05:18
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('icf_career_fair', '0039_careerfairadvertisement_careerfairadvertisementviews'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='careerfairadvertisement',
            options={'ordering': ['-created', 'career_fair'], 'verbose_name_plural': 'Career Fair Advertisements'},
        ),
    ]
