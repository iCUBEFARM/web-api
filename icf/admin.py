from django.contrib import admin
from django.contrib.sites.models import Site
from django.contrib.auth.models import Group
from allauth.account.models import EmailAddress


# Register your models here.
from icf_auth.models import UserProfile, User
