import os

from django.conf import settings
from django.urls import reverse
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APITestCase
import icf_entity.api.tests.entity_test_data as entity_test_data
from icf_auth.models import User

from icf_entity.api.tests.test_mixins import EntityTestMixin, EntityBrochureTestMixin, EntityPromoVideoTestMixin
from icf_entity.models import EntityUser, Industry, Sector, CompanySize, Entity
from icf_generic.models import Type, City, Category
from icf_orders.models import CreditAction
from copy import deepcopy


def test_log(api, data=None, response=None):
    # if getattr(settings, 'TEST_CONSOLE_LOG', False):
    print("\n/{}\n* {}\n{}/".format('*' * 30, api, '*' * 31))
    if response:
        print("{}".format(response.wsgi_request))
    if data:
        print("Input Data: {}".format(data))
    if response:
        print("Response Status Code: {} \nResponse Data: {}".format(response.status_code, response.content))


class EntityViewTest(EntityPromoVideoTestMixin, EntityBrochureTestMixin, EntityTestMixin, APITestCase):

    def setUp(self) -> None:
        self.entity_create_url = 'new-entity-create'
        self.entity_update_url = 'entity-update'
        self.brochure_list_url = 'entity-brochure-list'  # Same will be used for create
        self.brochure_detail_url = 'entity-brochure-detail'
        self.promotional_video_list_url = 'entity-promotional-video-list'  # Same will be used for create
        self.promotional_video_detail_url = 'entity-promotional-video-detail'
        self.entity_detail_url = 'entity-detail'

        self.create_entity_dependent_master_data()

        # Check if dependent data is there
        self.assertGreater(CreditAction.objects.count(), 0, "Credit Actions Not created")
        self.assertGreater(Type.objects.count(), 0, "Type Objects Not created")
        self.assertGreater(Industry.objects.count(), 0, "Industries Not created")
        self.assertGreater(Sector.objects.count(), 0, "Sectors Not created")

        user_data = entity_test_data.USER_DATA[0]
        user1, created = User.objects.get_or_create(mobile=user_data.get("mobile"),
                                                    email=user_data.get("email"),
                                                    first_name=user_data.get("first_name"),
                                                    last_name=user_data.get("last_name"))

        self.assertEqual(created, True, "Create user failed")

        user1.set_password(user_data.get("password"))
        user1.save()
        self.token = AuthToken.objects.create(user1)

        self.user = user1
        self.client.force_authenticate(user=user1)

    def test_entity_create(self):
        entity_data = self.create_entity_ref_data()

        response = self.client.post(reverse(self.entity_create_url), entity_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        test_log("Entity: Create", data=entity_data, response=response)

    def test_entity_update(self):
        create_ref_data = self.create_entity_ref_data()

        response = self.client.post(reverse(self.entity_create_url), create_ref_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        test_log("Entity: Create", data=create_ref_data, response=response)

        update_data = self.update_entity_ref_data(existing_data=response.data)

        update_response = self.client.put(reverse(self.entity_update_url, kwargs={'slug': update_data['slug']}),
                                          update_data,
                                          format='json')

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        test_log("Entity: Update", data=update_data, response=update_response)



    def test_entity_retrieve(self):
        entity_data = deepcopy(entity_test_data.CREATE_ENTITIES[0])
        entity = self.create_entity_new(entity_data=entity_data)

        entity_promo_videos_data = entity_test_data.ENTITY_PROMOTIONAL_VIDEOS
        for entity_promo_video_data in entity_promo_videos_data:
            entity_promo_video_created = self.add_promotional_video(
                name=entity_promo_video_data.get("promotional_video_name"),
                entity=entity,
                url=entity_promo_video_data.get("promotional_video_url"))

        entity_brochures_data = entity_test_data.ENTITY_BROCHURES
        for entity_brochure_data in entity_brochures_data:
            entity_brochure_created = self.add_brochure(brochure_name=entity_brochure_data.get("brochure_name"),
                                                        entity=entity,
                                                        brochure_file=entity_brochure_data.get("brochure"))

        entity_retrieve_response = self.client.get(reverse(self.entity_detail_url,
                                                           kwargs={'slug': entity.slug}),
                                                   format='json')

        self.assertEqual(entity_retrieve_response.status_code, status.HTTP_200_OK)
        test_log("Entity: Details", data="", response=entity_retrieve_response)


    # def test_entity_retrieve(self):
    #     entity_data = deepcopy(entity_test_data.CREATE_ENTITIES[0])
    #     # Fix ids of objects when required
    #     industry_name = entity_data.get("industry")
    #     sector_name = entity_data.get("sector")
    #     city_name = entity_data.get("address").get("city")
    #
    #     industry_obj = Industry.objects.get(industry=industry_name)
    #     sector_obj = Sector.objects.get(sector=sector_name)
    #     city_obj = City.objects.get(city=city_name)
    #
    #     entity_data["industry"] = industry_obj.id
    #     entity_data["sector"] = sector_obj.id
    #     entity_data["address"]["city"] = city_obj.id
    #
    #     response = self.client.post(reverse(self.entity_create_url), entity_data, format='json')
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #
    #     test_log("Entity: Create", data=entity_data, response=response)
    #
    #     entity_slug = response.data.get("slug")
    #
    #     entity_promo_video_data = entity_test_data.ENTITY_PROMOTIONAL_VIDEOS[0]
    #     video_name = entity_promo_video_data.get("promotional_video_name")
    #     video_url = entity_promo_video_data.get("promotional_video_url")
    #     video_create_response = self.client.post(
    #         reverse(self.promotional_video_list_url, kwargs={'slug': entity_slug}),
    #         {'promotional_video_name': video_name, 'promotional_video_url': video_url},
    #         format='json')
    #
    #     self.assertEqual(video_create_response.status_code, status.HTTP_201_CREATED)
    #
    #     entity_brochure_data = entity_test_data.ENTITY_BROCHURES[0]
    #     brochure_name = entity_brochure_data.get("brochure_name"),
    #     brochure_file = entity_brochure_data.get("brochure")
    #     file_path = os.path.join(entity_test_data.TEST_FILES_PATH, brochure_file)
    #     with open(file_path, "rb") as fp:
    #         brochure_create_response = self.client.post(reverse(self.brochure_list_url, kwargs={'slug': entity_slug}),
    #                                                     {"brochure": fp, "brochure_name": brochure_name},
    #                                                     format='multipart')
    #     self.assertEqual(brochure_create_response.status_code, status.HTTP_201_CREATED)
    #
    #     entity_retrieve_response = self.client.get(reverse(self.entity_detail_url,
    #                                                        kwargs={'slug': entity_slug}),
    #                                                format='json')
    #
    #     self.assertEqual(entity_retrieve_response.status_code, status.HTTP_200_OK)
    #     test_log("Entity: Details", data="", response=entity_retrieve_response)


class EntityBrochureViewTest(EntityBrochureTestMixin, EntityTestMixin, APITestCase):
    def setUp(self) -> None:
        self.entity_create_url = 'new-entity-create'
        self.entity_update_url = 'entity-update'
        self.brochure_list_url = 'entity-brochure-list'  # Same will be used for create
        self.brochure_detail_url = 'entity-brochure-detail'

        self.create_entity_dependent_master_data()

        # Check if dependent data is there
        self.assertGreater(CreditAction.objects.count(), 0, "Credit Actions Not created")
        self.assertGreater(Type.objects.count(), 0, "Type Objects Not created")
        self.assertGreater(Industry.objects.count(), 0, "Industries Not created")
        self.assertGreater(Sector.objects.count(), 0, "Sectors Not created")

        user_data = entity_test_data.USER_DATA[0]
        user1, created = User.objects.get_or_create(mobile=user_data.get("mobile"),
                                                    email=user_data.get("email"),
                                                    first_name=user_data.get("first_name"),
                                                    last_name=user_data.get("last_name"))

        self.assertEqual(created, True, "Create user failed")

        user1.set_password(user_data.get("password"))
        user1.save()
        self.token = AuthToken.objects.create(user1)

        self.user = user1
        self.client.force_authenticate(user=user1)

    def test_entity_brochure_create(self):
        entity_data = self.create_entity_ref_data()

        response = self.client.post(reverse(self.entity_create_url), entity_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # test_log("Entity: Create", data=entity_data, response=response)

        entity_slug = response.data.get("slug")

        entity_brochure_data = entity_test_data.ENTITY_BROCHURES[0]
        brochure_name = entity_brochure_data.get("brochure_name")
        brochure_file = entity_brochure_data.get("brochure")
        file_path = os.path.join(entity_test_data.TEST_FILES_PATH, brochure_file)
        with open(file_path, "rb") as fp:
            brochure_create_response = self.client.post(reverse(self.brochure_list_url, kwargs={'slug': entity_slug}),
                                                        {"brochure": fp, "brochure_name": brochure_name},
                                                        format='multipart')
        self.assertEqual(brochure_create_response.status_code, status.HTTP_201_CREATED)

        test_log("Entity Brochure Create", data=entity_brochure_data, response=brochure_create_response)

    def test_entity_brochure_list(self):
        entity_data = self.create_entity_ref_data()

        response = self.client.post(reverse(self.entity_create_url), entity_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # test_log("Entity: Create", data=entity_data, response=response)

        entity_slug = response.data.get("slug")
        entity = Entity.objects.get(slug=entity_slug)

        entity_brochures_data = entity_test_data.ENTITY_BROCHURES
        for entity_brochure_data in entity_brochures_data:
            entity_brochure_created = self.add_brochure(brochure_name=entity_brochure_data.get("brochure_name"),
                                                        entity=entity,
                                                        brochure_file=entity_brochure_data.get("brochure"))

        brochure_list_response = self.client.get(reverse(self.brochure_list_url, kwargs={'slug': entity.slug}),
                                                 format='json')

        self.assertEqual(brochure_list_response.status_code, status.HTTP_200_OK)

        test_log("Entity Brochure List", data=entity_brochures_data, response=brochure_list_response)

    def test_entity_brochure_delete(self):
        entity_data = self.create_entity_ref_data()

        response = self.client.post(reverse(self.entity_create_url), entity_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # test_log("Entity: Create", data=entity_data, response=response)

        entity_slug = response.data.get("slug")
        entity = Entity.objects.get(slug=entity_slug)

        entity_brochure_data = entity_test_data.ENTITY_BROCHURES[0]
        entity_brochure_created = self.add_brochure(brochure_name=entity_brochure_data.get("brochure_name"),
                                                    entity=entity,
                                                    brochure_file=entity_brochure_data.get("brochure"))

        brochure_delete_response = self.client.delete(reverse(self.brochure_detail_url,
                                                              kwargs={'slug': entity.slug,
                                                                      'pk': entity_brochure_created.pk}),
                                                      format='json')

        self.assertEqual(brochure_delete_response.status_code, status.HTTP_204_NO_CONTENT)

        test_log("Entity Brochure Delete", data="{'slug': entity_slug, 'pk':pk}", response=brochure_delete_response)


class EntityPromotionalVideoViewTest(EntityPromoVideoTestMixin, EntityTestMixin, APITestCase):
    def setUp(self) -> None:
        self.entity_create_url = 'new-entity-create'
        self.entity_update_url = 'entity-update'
        self.promotional_video_list_url = 'entity-promotional-video-list'  # Same will be used for create
        self.promotional_video_detail_url = 'entity-promotional-video-detail'
        self.entity_detail_url = 'entity-detail'
        self.brochure_list_url = 'entity-brochure-list'  # Same will be used for create

        self.create_entity_dependent_master_data()

        # Check if dependent data is there
        self.assertGreater(CreditAction.objects.count(), 0, "Credit Actions Not created")
        self.assertGreater(Type.objects.count(), 0, "Type Objects Not created")
        self.assertGreater(Industry.objects.count(), 0, "Industries Not created")
        self.assertGreater(Sector.objects.count(), 0, "Sectors Not created")

        user_data = entity_test_data.USER_DATA[0]
        user1, created = User.objects.get_or_create(mobile=user_data.get("mobile"),
                                                    email=user_data.get("email"),
                                                    first_name=user_data.get("first_name"),
                                                    last_name=user_data.get("last_name"))

        self.assertEqual(created, True, "Create user failed")

        user1.set_password(user_data.get("password"))
        user1.save()
        self.token = AuthToken.objects.create(user1)

        self.user = user1
        self.client.force_authenticate(user=user1)


    def test_entity_promotional_video_create(self):
        entity_data = self.create_entity_ref_data()

        response = self.client.post(reverse(self.entity_create_url), entity_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # test_log("Entity: Create", data=entity_data, response=response)

        entity_slug = response.data.get("slug")

        entity_promo_video_data = entity_test_data.ENTITY_PROMOTIONAL_VIDEOS[0]
        video_name = entity_promo_video_data.get("promotional_video_name")
        video_url = entity_promo_video_data.get("promotional_video_url")
        video_create_response = self.client.post(
            reverse(self.promotional_video_list_url, kwargs={'slug': entity_slug}),
            {'promotional_video_name': video_name, 'promotional_video_url': video_url},
            format='json')

        self.assertEqual(video_create_response.status_code, status.HTTP_201_CREATED)

        test_log("Entity Promotional Video Create", data=entity_promo_video_data, response=video_create_response)

    def test_entity_promotional_video_list(self):
        entity_data = self.create_entity_ref_data()

        response = self.client.post(reverse(self.entity_create_url), entity_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # test_log("Entity: Create", data=entity_data, response=response)

        entity_slug = response.data.get("slug")
        entity = Entity.objects.get(slug=entity_slug)

        entity_promo_videos_data = entity_test_data.ENTITY_PROMOTIONAL_VIDEOS
        for entity_promo_video_data in entity_promo_videos_data:
            entity_promo_video_created = self.add_promotional_video(
                name=entity_promo_video_data.get("promotional_video_name"),
                entity=entity,
                url=entity_promo_video_data.get("promotional_video_url"))

        video_list_response = self.client.get(reverse(self.promotional_video_list_url,
                                                      kwargs={'slug': entity.slug}),
                                              format='json')

        self.assertEqual(video_list_response.status_code, status.HTTP_200_OK)

        test_log("Entity Promotional Video List", data=entity_promo_videos_data, response=video_list_response)

    def test_entity_promotional_video_delete(self):
        entity_data = self.create_entity_ref_data()

        response = self.client.post(reverse(self.entity_create_url), entity_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # test_log("Entity: Create", data=entity_data, response=response)

        entity_slug = response.data.get("slug")
        entity = Entity.objects.get(slug=entity_slug)

        entity_promo_video_data = entity_test_data.ENTITY_PROMOTIONAL_VIDEOS[0]
        entity_promo_video_created = self.add_promotional_video(
            name=entity_promo_video_data.get("promotional_video_name"),
            entity=entity,
            url=entity_promo_video_data.get("promotional_video_url"))

        video_delete_response = self.client.delete(reverse(self.promotional_video_detail_url,
                                                           kwargs={'slug': entity.slug,
                                                                   'pk': entity_promo_video_created.pk}),
                                                   format='json')

        self.assertEqual(video_delete_response.status_code, status.HTTP_204_NO_CONTENT)

        test_log("Entity Promo Video Delete", data="{'slug': entity_slug, 'pk':pk}", response=video_delete_response)

