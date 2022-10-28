import os, sys

FILE_DIR=os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# This is so Django knows where to find stuff.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "icf.settings")
sys.path.append(PROJ_PATH)

# This is so my local_settings.py gets loaded.
os.chdir(PROJ_PATH)

# This is so models get loaded.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()


from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from guardian.models import GroupObjectPermission
from guardian.shortcuts import assign_perm

from icf_entity.models import Entity
from icf_events.models import EventPerms


all_entities = Entity.objects.all()

event_permissions = EventPerms.get_event_perms()

# Get all the entities
for entity in all_entities:

    print("Processing Entity: {}".format(entity.slug))
    # For each event permission, create a group and assign permission to the group
    for perm in event_permissions.values():
        # group_name = "{}_{}".format(instance.slug, perm.codename)
        print ("Creating group for Event Permission: {}".format(perm))
        group_name = EventPerms.get_entity_group(entity, perm)
        entity_event_group, created = Group.objects.get_or_create(name=group_name)
        perm_obj = Permission.objects.get(codename=perm)
        assign_perm(perm_obj, entity_event_group, entity)

    # Get all the entity admins and add them to event related groups
    entity_admin_group = Group.objects.get(name="{}_{}".format(entity.slug, "icf_ent_adm"))
    entity_admin_users = entity_admin_group.user_set.all()

    for adm_user in entity_admin_users:
        for ent_group in ['icf_evt_adm', 'icf_evt_cr', 'icf_evt_pub',]:
            print("Adding user : {} to Group : {}".format(adm_user.username, ent_group))
            adm_user.groups.add(Group.objects.get(name="{}_{}".format(entity.slug, ent_group)))



