from django.db import models
from django.utils.translation import ugettext_lazy as _

from icf_generic.models import Country, Language, Type

# Create your models here.
class Announcement(models.Model):

    DRAFT= 1
    ACTIVE = 2
    CLOSED = 3

    STATUS_CHOICES = (
        (DRAFT, _('Draft')), (ACTIVE, _('Active')), (CLOSED, _('Closed')), )

    title = models.CharField(_("title"), max_length=150)
    description = models.CharField(_("description"), max_length=150, blank=False, null=False)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, blank=True, null=True)
    language = models.ForeignKey(Language, on_delete=models.CASCADE, blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, blank=True, null=True)
    item_type = models.ForeignKey(Type, on_delete=models.CASCADE, blank=True, null=True)
    url = models.CharField(_("url"), max_length=170, blank=True, null=True)
    button_text = models.CharField(_("button_text"), max_length=170, blank=True, null=True)
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"))
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)

    def __str__(self):
        return "{}".format(self.title)

    class Meta:
        verbose_name_plural = 'Announcement'
        ordering = ['-created', ]