import os

from django.db import IntegrityError

from icf_entity.api.tests.entity_test_data import CREATE_ENTITIES, ENTITY_BROCHURES, ENTITY_PROMOTIONAL_VIDEOS
from icf_entity.api.tests.test_mixins import EntityTestMixin, EntityBrochureTestMixin, EntityPromoVideoTestMixin
from icf_entity.models import Entity, EntityBrochure, EntityPromotionalVideo
from rest_framework.test import APITestCase

# class EntityBrochure(models.Model):
#     brochure_name = models.CharField(max_length=150)
#     entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
#     brochure = models.FileField(upload_to=upload_entity_brochure_media_location,
#                               validators=[validate_file_extension], max_length=200, null=True, blank=True)
#     created = models.DateTimeField(auto_now_add=True, auto_now=False)
#     updated = models.DateTimeField(auto_now_add=False, auto_now=True)
#
#
#
# class EntityPromotionalVideo(models.Model):
#     promotional_video_name = models.CharField(max_length=150)
#     entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
#     promotional_video_url = models.URLField(blank=True)
#     created = models.DateTimeField(auto_now_add=True, auto_now=False)
#     updated = models.DateTimeField(auto_now_add=False, auto_now=True)

# class Entity(models.Model):
#
#     ENTITY_CREATED = 1
#     ENTITY_ACTIVE = 2
#     ENTITY_INACTIVE = 3
#
#     ENTITY_STATUS_CHOICES = (
#         (ENTITY_ACTIVE, _('Active')),
#         (ENTITY_INACTIVE, _('Inactive')),
#     )
#
#
#     LOGO_WIDTH = 300
#     LOGO_HEIGHT = 300
#
#     name = models.CharField(_("name"), max_length=200, blank=False, null=False)

#     email = models.EmailField(blank=False)
#     phone = models.CharField(validators=[User.PHONE_REGEX], max_length=25, blank=False)  # validators should be a list
#     description = models.CharField(_("description"), max_length=1000, blank=False, null=False )


class EntityModelTest(EntityTestMixin, APITestCase):

    def test_create_entity(self):
        entity_data = CREATE_ENTITIES[0]
        entity, created = self.create_entity(name=entity_data.get("name"),
                                             email=entity_data.get("email"),
                                             phone=entity_data.get("phone"),
                                             description=entity_data.get("description"),
                                             )
        self.assertEqual(created, True, "Entity Creation Failed")

    # Phone is a mandatory field
    def test_create_entity_without_phone(self):
        entity_data = CREATE_ENTITIES[1]
        with self.assertRaises(IntegrityError):
            entity, created = self.create_entity(name=entity_data.get("name"),
                                             email=entity_data.get("email"),
                                             phone=entity_data.get("phone"),
                                             description=entity_data.get("description"),
                                                 )
            entity.full_clean()


class EntityBrochureModelTest(EntityTestMixin, EntityBrochureTestMixin, APITestCase):

    def test_single_brochure(self):
        entity_data = CREATE_ENTITIES[0]
        entity, created = self.create_entity(name=entity_data.get("name"),
                                             email=entity_data.get("email"),
                                             phone=entity_data.get("phone"),
                                             description=entity_data.get("description"),
                                             )

        entity_brochure_data = ENTITY_BROCHURES[0]
        entity_brochure = self.add_brochure(brochure_name=entity_brochure_data.get("brochure_name"),
                                            entity=entity, brochure_file=entity_brochure_data.get("brochure"))

        result = EntityBrochure.objects.get(brochure_name=entity_brochure_data.get("brochure_name"),
                                            entity=entity)
        self.assertEqual(result.brochure_name, entity_brochure_data.get("brochure_name"), "Creation of Brochure Failed")

    def test_multiple_brochures(self):
        entity_data = CREATE_ENTITIES[0]

        entity, created = self.create_entity(name=entity_data.get("name"),
                                             email=entity_data.get("email"),
                                             phone=entity_data.get("phone"),
                                             description=entity_data.get("description"),
                                             )

        entity_brochures_data = ENTITY_BROCHURES
        for entity_brochure_data in entity_brochures_data:

            entity_brochure_created = self.add_brochure(brochure_name=entity_brochure_data.get("brochure_name"),
                                                entity=entity,
                                                brochure_file=entity_brochure_data.get("brochure"))

            result_from_db = EntityBrochure.objects.get(brochure_name=entity_brochure_data.get("brochure_name"),
                                                entity=entity)

            self.assertEqual(result_from_db.brochure_name, entity_brochure_created.brochure_name, "Creation of Brochure Failed")


class EntityPromotionalVideoModelTest(EntityTestMixin, EntityPromoVideoTestMixin, APITestCase):
    def test_single_promo_video(self):
        entity_data = CREATE_ENTITIES[0]

        entity, created = self.create_entity(name=entity_data.get("name"),
                                             email=entity_data.get("email"),
                                             phone=entity_data.get("phone"),
                                             description=entity_data.get("description"),
                                             )

        promotional_video_data = ENTITY_PROMOTIONAL_VIDEOS[0]

        promo_video_created = self.add_promotional_video(name=promotional_video_data.get("promotional_video_name"),
                                            entity=entity,
                                            url=promotional_video_data.get("promotional_video_url"))

        result_from_db = EntityPromotionalVideo.objects.get(promotional_video_name=promotional_video_data.get("promotional_video_name"))

        self.assertEqual(result_from_db.promotional_video_name, promo_video_created.promotional_video_name, "Creation of Promotional Video Failed")

    def test_multiple_promo_videos(self):
        entity_data = CREATE_ENTITIES[0]

        entity, created = self.create_entity(name=entity_data.get("name"),
                                             email=entity_data.get("email"),
                                             phone=entity_data.get("phone"),
                                             description=entity_data.get("description"),
                                             )

        promotional_videos_data = ENTITY_PROMOTIONAL_VIDEOS

        for promotional_video_data in promotional_videos_data:
            promo_video_created = self.add_promotional_video(name=promotional_video_data.get("promotional_video_name"),
                                                entity=entity,
                                                url=promotional_video_data.get("promotional_video_url"))

            result_from_db = EntityPromotionalVideo.objects.get(promotional_video_name=promotional_video_data.get("promotional_video_name"))

            self.assertEqual(result_from_db.promotional_video_name, promo_video_created.promotional_video_name, "Creation of Promotional Video Failed")


