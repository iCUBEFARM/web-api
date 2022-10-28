from django.contrib.auth.models import Group
from guardian.shortcuts import get_perms
from guardian.conf import settings
from rest_framework import permissions
from django.utils.translation import ugettext_lazy as _
from rest_framework.permissions import SAFE_METHODS

from icf_entity.permissions import ICFEntityUserPermManager
from icf_entity.models import EntityPerms, Entity
from icf_jobs.models import JobPerms, Job


class CanCreateJob(permissions.BasePermission):
    message = _("You do not have the permissions to create a job for entity")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_EDIT, JobPerms.JOB_ADMIN, JobPerms.JOB_CREATE, ]
    allowed_write_perms = allowed_read_perms

    def has_permission(self, request, view):

        user = request.user
        if user.username == settings.ANONYMOUS_USER_NAME:
            return False

        entity_slug = view.kwargs.get('entity_slug')

        entity = Entity.objects.get(slug=entity_slug)

        if entity:
            return any(perm in get_perms(request.user, entity) for perm in self.allowed_write_perms)

        return False

class CanEditJob(permissions.BasePermission):
    message = _("You do not have the permissions to create a job for entity")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_EDIT, JobPerms.JOB_ADMIN, JobPerms.JOB_CREATE, ]
    allowed_write_perms = allowed_read_perms

    def has_object_permission(self, request, view, obj):

        entity = obj.entity

        if request.user == obj.owner:
            return True

        return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)


class CanPublishJob(permissions.BasePermission):
    message = _("You do not have the permissions to publish a job for entity")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_EDIT, JobPerms.JOB_ADMIN, JobPerms.JOB_PUBLISH ]
    allowed_write_perms = allowed_read_perms

    def has_object_permission(self, request, view, obj):
        entity = obj.entity
        return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)


class CanMarkJobDelete(permissions.BasePermission):
    message = _("You do not have the permissions to mark a job as Delete for entity")
    allowed_read_perms = [JobPerms.JOB_PUBLISH ]
    allowed_write_perms = allowed_read_perms

    def has_permission(self, request, view):

        slug = view.kwargs.get('slug')
        # job = request.META['job']
        try:
            job = Job.objects.get(slug=slug)
            entity = job.entity
            return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)
        except Entity.DoesNotExist as dne:
            return False


class CanDeleteJob(permissions.BasePermission):
    message = _("You do not have the permissions to delete jobs for entity")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, JobPerms.JOB_ADMIN, ]
    allowed_write_perms = allowed_read_perms

    def has_object_permission(self, request, view, obj):

        entity = obj.entity
        # Any user with create permission can delete a draft
        if request.user.has_perm(JobPerms.JOB_CREATE, entity) and obj.status == Job.ITEM_DRAFT:
            return True

        return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)


class CanSeeJobsMarkedForDeleteList(permissions.BasePermission):
    message = _("You do not have permissions to see the jobs marked for Delete.")
    allowed_read_perms = [JobPerms.JOB_ADMIN]
    allowed_write_perms = allowed_read_perms

    def has_permission(self, request, view):

        entity_slug = view.kwargs.get('entity_slug')
        try:
            entity = Entity.objects.get(slug=entity_slug)
            return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)
        except Entity.DoesNotExist as dne:
            return False


class CanRejectMarkedForDeleteJob(permissions.BasePermission):
    message = _("You do not have the permissions to reject a job delete request for entity")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, JobPerms.JOB_ADMIN, ]
    allowed_write_perms = allowed_read_perms

    def has_permission(self, request, view):

        slug = view.kwargs.get('slug')
        try:
            job = Job.objects.get(slug=slug)
            entity = job.entity
            return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)
        except Job.DoesNotExist as dne:
            return False

    # def has_object_permission(self, request, view, obj):
    #     entity = obj.entity
    #     return any(perm in get_perms(request.user, entity) for perm in self.allowed_read_perms)


class CanRecruitApplicant(permissions.BasePermission):
    message = _("You do not have the permissions to recruit applicants")
    allowed_read_perms = [EntityPerms.ENTITY_ADMIN, EntityPerms.ENTITY_EDIT, JobPerms.JOB_ADMIN, JobPerms.JOB_RECRUIT]
    allowed_write_perms = allowed_read_perms


# class IsJobAdmin(ICFJobPermissionMixin, permissions.BasePermission):
#     message = _("Do not have job admin permission for the entity")
#     allowed_read_perms = [EntityPerms.ENTITY_ADMIN, JobPerms.JOB_ADMIN]
#     allowed_write_perms = allowed_read_perms


class ICFJobsUserPermManager:
    ADD_PERM = 1
    REMOVE_PERM = 2

    #
    # If the permission is one of the Entity permissions, set it
    # else, send entity_set_permission signal that can be processed
    # by other apps that have included permissions on the entity
    #
    @classmethod
    def set_user_perm(cls, action, user, entity, perm):

        job_perms = JobPerms.get_job_perms()

        #
        # If not a basic entity permission, send a signal
        # Other applications to handle
        #
        if perm not in job_perms.values():
            return None

        perms_for_user = []
        if perm == JobPerms.get_admin_perm():
            for value in job_perms.values():
                perms_for_user.append(value)
        else:
            perms_for_user.append(perm)

        for user_perm in perms_for_user:
            group_name = JobPerms.get_entity_group(entity, user_perm)
            group = Group.objects.get(name=group_name)

            if action == cls.ADD_PERM:
                user.groups.add(group)
            elif action == cls.REMOVE_PERM:
                user.groups.remove(group)

        return user

    @classmethod
    def add_user_perm(cls, sender, user=None, entity=None, perm=None, **kwargs):
        return cls.set_user_perm(cls.ADD_PERM, user, entity, perm)

    @classmethod
    def remove_user_perm(cls, sender, user=None, entity=None, perm=None, **kwargs):
        return cls.set_user_perm(cls.REMOVE_PERM, user, entity, perm)



