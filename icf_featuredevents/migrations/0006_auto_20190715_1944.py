# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2019-07-15 14:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('icf_featuredevents', '0005_auto_20190627_1542'),
    ]

    operations = [
        migrations.CreateModel(
            name='FeaturedEventAndProduct',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='featuredeventandcategory',
            name='category',
        ),
        migrations.RemoveField(
            model_name='featuredeventandcategory',
            name='featured_event',
        ),
        migrations.RemoveField(
            model_name='featuredeventandcategory',
            name='product',
        ),
        migrations.RemoveField(
            model_name='eventproduct',
            name='category',
        ),
    ]
