# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2021-09-29 16:34
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('icf_entity', '0009_auto_20210911_1304'),
        ('icf_generic', '0021_auto_20200121_1138'),
        ('icf_orders', '0016_billingaddress_zip_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductDraft',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('unit', models.PositiveIntegerField(default=1)),
                ('cost', models.DecimalField(decimal_places=2, max_digits=8)),
                ('is_active', models.BooleanField(default=False)),
                ('description', models.TextField(blank=True, null=True)),
                ('product_type', models.SmallIntegerField(choices=[(1, 'SUBSCRIPTION'), (2, 'CREDIT'), (3, 'EVENT_PRODUCT'), (4, 'CAREER_FAIR_PRODUCT'), (5, 'OTHER')], default=3)),
                ('buyer_type', models.SmallIntegerField(choices=[(1, 'Individual'), (2, 'Entity'), (3, 'Sponsor'), (4, 'Other')], default=1)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='icf_generic.Currency')),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_draft', to='icf_entity.Entity')),
                ('parent_product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='icf_orders.ProductDraft')),
            ],
        ),
    ]
