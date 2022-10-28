# Generated by Django 3.2.14 on 2022-09-01 00:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('icf_jobs', '0032_userfreelanceservice'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userfreelanceservice',
            name='category',
        ),
        migrations.CreateModel(
            name='UserAwardRecognition',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=500, verbose_name='title')),
                ('year', models.PositiveIntegerField()),
                ('award_institution', models.SmallIntegerField(choices=[(1, 'Paticipant'), (2, 'Moderator')], default=1)),
                ('award_level', models.SmallIntegerField(choices=[(1, 'Nominated'), (2, 'Selected')], default=1)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('job_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='icf_jobs.userjobprofile')),
            ],
            options={
                'verbose_name_plural': 'UserAwardRecognitions',
            },
        ),
    ]
