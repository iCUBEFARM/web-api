# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2021-10-20 11:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('icf_career_fair', '0016_careerfairparticipant_entity_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='description_en',
            field=models.TextField(null=True, verbose_name='description'),
        ),
        migrations.AddField(
            model_name='session',
            name='description_es',
            field=models.TextField(null=True, verbose_name='description'),
        ),
        migrations.AddField(
            model_name='session',
            name='description_fr',
            field=models.TextField(null=True, verbose_name='description'),
        ),
        migrations.AddField(
            model_name='session',
            name='title_en',
            field=models.CharField(max_length=80, null=True, verbose_name='title'),
        ),
        migrations.AddField(
            model_name='session',
            name='title_es',
            field=models.CharField(max_length=80, null=True, verbose_name='title'),
        ),
        migrations.AddField(
            model_name='session',
            name='title_fr',
            field=models.CharField(max_length=80, null=True, verbose_name='title'),
        ),
        migrations.AddField(
            model_name='sessionoptional',
            name='description_en',
            field=models.TextField(null=True, verbose_name='description'),
        ),
        migrations.AddField(
            model_name='sessionoptional',
            name='description_es',
            field=models.TextField(null=True, verbose_name='description'),
        ),
        migrations.AddField(
            model_name='sessionoptional',
            name='description_fr',
            field=models.TextField(null=True, verbose_name='description'),
        ),
        migrations.AddField(
            model_name='sessionoptional',
            name='title_en',
            field=models.CharField(max_length=80, null=True, verbose_name='title'),
        ),
        migrations.AddField(
            model_name='sessionoptional',
            name='title_es',
            field=models.CharField(max_length=80, null=True, verbose_name='title'),
        ),
        migrations.AddField(
            model_name='sessionoptional',
            name='title_fr',
            field=models.CharField(max_length=80, null=True, verbose_name='title'),
        ),
        migrations.AddField(
            model_name='speaker',
            name='entity_name_en',
            field=models.CharField(max_length=80, null=True, verbose_name='entity_name'),
        ),
        migrations.AddField(
            model_name='speaker',
            name='entity_name_es',
            field=models.CharField(max_length=80, null=True, verbose_name='entity_name'),
        ),
        migrations.AddField(
            model_name='speaker',
            name='entity_name_fr',
            field=models.CharField(max_length=80, null=True, verbose_name='entity_name'),
        ),
        migrations.AddField(
            model_name='speaker',
            name='name_en',
            field=models.CharField(max_length=80, null=True, verbose_name='name'),
        ),
        migrations.AddField(
            model_name='speaker',
            name='name_es',
            field=models.CharField(max_length=80, null=True, verbose_name='name'),
        ),
        migrations.AddField(
            model_name='speaker',
            name='name_fr',
            field=models.CharField(max_length=80, null=True, verbose_name='name'),
        ),
        migrations.AddField(
            model_name='speaker',
            name='position_en',
            field=models.CharField(max_length=80, null=True, verbose_name='position'),
        ),
        migrations.AddField(
            model_name='speaker',
            name='position_es',
            field=models.CharField(max_length=80, null=True, verbose_name='position'),
        ),
        migrations.AddField(
            model_name='speaker',
            name='position_fr',
            field=models.CharField(max_length=80, null=True, verbose_name='position'),
        ),
        migrations.AddField(
            model_name='speakeroptional',
            name='entity_name_en',
            field=models.CharField(max_length=80, null=True, verbose_name='entity_name'),
        ),
        migrations.AddField(
            model_name='speakeroptional',
            name='entity_name_es',
            field=models.CharField(max_length=80, null=True, verbose_name='entity_name'),
        ),
        migrations.AddField(
            model_name='speakeroptional',
            name='entity_name_fr',
            field=models.CharField(max_length=80, null=True, verbose_name='entity_name'),
        ),
        migrations.AddField(
            model_name='speakeroptional',
            name='name_en',
            field=models.CharField(max_length=80, null=True, verbose_name='name'),
        ),
        migrations.AddField(
            model_name='speakeroptional',
            name='name_es',
            field=models.CharField(max_length=80, null=True, verbose_name='name'),
        ),
        migrations.AddField(
            model_name='speakeroptional',
            name='name_fr',
            field=models.CharField(max_length=80, null=True, verbose_name='name'),
        ),
        migrations.AddField(
            model_name='speakeroptional',
            name='position_en',
            field=models.CharField(max_length=80, null=True, verbose_name='position'),
        ),
        migrations.AddField(
            model_name='speakeroptional',
            name='position_es',
            field=models.CharField(max_length=80, null=True, verbose_name='position'),
        ),
        migrations.AddField(
            model_name='speakeroptional',
            name='position_fr',
            field=models.CharField(max_length=80, null=True, verbose_name='position'),
        ),
        migrations.AddField(
            model_name='support',
            name='brand_name_en',
            field=models.CharField(max_length=80, null=True, verbose_name='brand_name'),
        ),
        migrations.AddField(
            model_name='support',
            name='brand_name_es',
            field=models.CharField(max_length=80, null=True, verbose_name='brand_name'),
        ),
        migrations.AddField(
            model_name='support',
            name='brand_name_fr',
            field=models.CharField(max_length=80, null=True, verbose_name='brand_name'),
        ),
        migrations.AddField(
            model_name='supportoptional',
            name='brand_name_en',
            field=models.CharField(max_length=80, null=True, verbose_name='brand_name'),
        ),
        migrations.AddField(
            model_name='supportoptional',
            name='brand_name_es',
            field=models.CharField(max_length=80, null=True, verbose_name='brand_name'),
        ),
        migrations.AddField(
            model_name='supportoptional',
            name='brand_name_fr',
            field=models.CharField(max_length=80, null=True, verbose_name='brand_name'),
        ),
    ]
