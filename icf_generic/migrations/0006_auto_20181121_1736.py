# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-11-21 12:06
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('icf_generic', '0005_addressoptional'),
    ]

    operations = [
        migrations.AlterField(
            model_name='addressoptional',
            name='address_1',
            field=models.CharField(blank=True, max_length=300, null=True, verbose_name='address'),
        ),
        migrations.AlterField(
            model_name='addressoptional',
            name='address_2',
            field=models.CharField(blank=True, max_length=300, null=True, verbose_name='address continued'),
        ),
    ]
