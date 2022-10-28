# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2019-07-24 12:57
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('icf_orders', '0011_auto_20190723_1309'),
    ]

    operations = [
        migrations.AddField(
            model_name='icfpaymenttransaction',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=datetime.datetime(2019, 7, 24, 12, 57, 37, 122435, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='icfpaymenttransaction',
            name='updated',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
