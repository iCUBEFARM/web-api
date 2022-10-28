# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2019-12-11 11:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('icf_generic', '0019_auto_20191211_1122'),
    ]

    operations = [
        migrations.AlterField(
            model_name='faqcategory',
            name='name',
            field=models.CharField(max_length=150, unique=True, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='faqcategory',
            name='name_en',
            field=models.CharField(max_length=150, null=True, unique=True, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='faqcategory',
            name='name_es',
            field=models.CharField(max_length=150, null=True, unique=True, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='faqcategory',
            name='name_fr',
            field=models.CharField(max_length=150, null=True, unique=True, verbose_name='name'),
        ),
    ]
