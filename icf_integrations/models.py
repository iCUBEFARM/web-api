from django.db import models

# Create your models here.
class SentGroupSms(models.Model):
    messages = models.CharField(max_length=1000,null=True,blank=True)
    sent_at = models.DateTimeField(auto_now=True,auto_now_add=False)
    success_count = models.IntegerField(default=0)
    failure_count = models.IntegerField(default=0)

    def __str__(self):
        return self.messages

    class Meta:
        verbose_name_plural = 'Send Group Sms'