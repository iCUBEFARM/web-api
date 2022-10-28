# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-11-21 11:16
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('icf_generic', '0004_auto_20181119_1249'),
        ('icf_entity', '0005_pending_entityuser'),
        ('icf_item', '0003_auto_20181108_1729'),
    ]

    operations = [
        migrations.CreateModel(
            name='ItemDraft',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=80, verbose_name='title')),
                ('description', models.CharField(blank=True, max_length=2500, null=True, verbose_name='description')),
                ('status', models.SmallIntegerField(blank=True, choices=[(1, 'Draft'), (2, 'Active'), (3, 'Expired'), (4, 'Closed'), (5, 'Marked for delete'), (6, 'Deleted')], null=True)),
                ('expiry', models.DateTimeField(blank=True, null=True)),
                ('slug', models.SlugField(blank=True, unique=True)),
                ('start_date', models.DateTimeField(blank=True, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='icf_generic.Category')),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='icf_entity.Entity')),
                ('item_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='icf_generic.Type')),
                ('location', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='icf_generic.Address')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Items',
                'ordering': ['-created'],
            },
        ),
    ]
