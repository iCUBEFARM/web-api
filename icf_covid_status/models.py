from django.db import models
from django.utils.translation import ugettext_lazy as _

from icf_auth.models import User
from icf_generic.models import Country


class EGSector(models.Model):
    name = models.CharField(max_length=200, unique=True, blank=True)
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name_plural = 'EGSectors'
        ordering = ('name',)

    def __str__(self):
        return self.name


class CurrentWorkStatus(models.Model):
    name = models.CharField(max_length=200, unique=True, blank=True)
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name_plural = 'Current Work Statuses'
        ordering = ('name',)

    def __str__(self):
        return self.name


class CurrentCompensationStatus(models.Model):
    name = models.CharField(max_length=200, unique=True, blank=True)
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name_plural = 'Current Compensation Statuses'
        ordering = ('name',)

    def __str__(self):
        return self.name


class UserWorkStatus(models.Model):
    user = models.OneToOneField(User, unique=True, on_delete=models.CASCADE, null=False, blank=False)
    company_name = models.CharField(max_length=200, blank=False, null=False)
    position = models.CharField(max_length=200, blank=False, null=False)
    sector = models.ForeignKey(EGSector, on_delete=models.CASCADE, null=False, blank=False)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, null=False, blank=False)
    current_work_status = models.ForeignKey(CurrentWorkStatus, on_delete=models.CASCADE, null=False, blank=False)
    current_compensation_status = models.ForeignKey(CurrentCompensationStatus, on_delete=models.CASCADE, null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    class Meta:
        verbose_name_plural = 'User Work Statuses'
        # ordering = ('name',)

    def __str__(self):
        return self.user.username + " " + self.company_name






