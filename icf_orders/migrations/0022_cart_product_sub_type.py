# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2021-10-07 09:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('icf_orders', '0021_cart_career_fair_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='cart',
            name='product_sub_type',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
