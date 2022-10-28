from copy import deepcopy

from django.contrib.contenttypes.models import ContentType
from django.core.files import File
from django.core.files.base import ContentFile
import icf_entity.api.tests.entity_test_data as entity_test_data
# from icf_entity.api.tests.entity_test_data import TEST_FILES_PATH, ICF_TYPES, CREDIT_ACTIONS, INDUSTRIES, SECTORS, \
#     LOCATION
from icf_entity.models import Entity, EntityBrochure, EntityPromotionalVideo, Industry, Sector, CompanySize
import os

from icf_generic.models import Type, Country, State, City, Category, Address
from icf_jobs.models import Job
from icf_orders.models import CreditAction


class EntityDependentMixin(object):
    def create_generic_icf_types(self):

        obj_types_data = entity_test_data.ICF_TYPES
        for obj_type_data in obj_types_data:
            obj_type = Type()
            obj_type.content_type = ContentType.objects.get(model=obj_type_data.get("content_type_model_name"))
            obj_type.name = obj_type_data.get("name")
            obj_type.save()

    def create_generic_cities(self):
        location_data = entity_test_data.LOCATION
        country, created1 = Country.objects.get_or_create(country=location_data.get("country"))
        state, created2 = State.objects.get_or_create(country=country, state=location_data.get("state"))
        city, created3 = City.objects.get_or_create(state=state, city=location_data.get("city"))

    def create_order_credit_actions(self):
        credit_actions_data = entity_test_data.CREDIT_ACTIONS
        for credit_action_data in credit_actions_data:
            credit_action = CreditAction()
            credit_action.action = credit_action_data.get("action")
            credit_action.action_desc = credit_action_data.get("action_desc")
            credit_action.credit_required = credit_action_data.get("credit_required")
            credit_action.interval = credit_action_data.get("interval")
            credit_action.content_type = Type.objects.get(name=credit_action_data.get("type"))
            credit_action.save()

    def create_entity_master_data(self):
        industries_data = entity_test_data.INDUSTRIES
        sectors_data = entity_test_data.SECTORS
        company_sizes_data = entity_test_data.COMPANY_SIZE
        categories_data = entity_test_data.CATEGORIES

        for industry_data in industries_data:
            Industry.objects.get_or_create(industry=industry_data.get("industry"),
                                           description=industry_data.get("description"))

        for sector_data in sectors_data:
            Sector.objects.get_or_create(sector=sector_data.get("sector"),
                                         description=sector_data.get("description"))

        for company_size_data in company_sizes_data:
            CompanySize.objects.get_or_create(size=company_size_data.get("size"),
                                              description=company_size_data.get("description"))

        for category_data in categories_data:
            category_type_obj = Type.objects.get(name=category_data.get("type"))
            Category.objects.get_or_create(name=category_data.get("name"),
                                           description=category_data.get("description"),
                                           type=category_type_obj
                                           )


class EntityTestMixin(EntityDependentMixin, object):

    def create_entity_dependent_master_data(self):
        self.create_generic_icf_types()
        self.create_generic_cities()
        self.create_order_credit_actions()
        self.create_entity_master_data()

    def create_entity(self, name=None, email=None, phone=None, description=None):
        entity, created = Entity.objects.get_or_create(name=name, email=email,
                                                       phone=phone,
                                                       description=description)
        return entity, created

    def create_entity_new(self, entity_data=None):

        industry_name = entity_data.get("industry")
        sector_name = entity_data.get("sector")
        city_name = entity_data.get("address").get("city")

        industry_obj = Industry.objects.get(industry=industry_name)
        sector_obj = Sector.objects.get(sector=sector_name)
        city_obj = City.objects.get(city=city_name)

        entity, created = Entity.objects.get_or_create(name=entity_data.get("name"),
                                                       email=entity_data.get("email"),
                                                       phone=entity_data.get("phone"),
                                                       alternate_phone=entity_data.get("alternate_phone"),
                                                       website=entity_data.get("website"),
                                                       industry=industry_obj,
                                                       sector=sector_obj)
        address = Address.objects.create(address_1=entity_data.get("address").get("address_1"),
                                         address_2=entity_data.get("address").get("address_2"),
                                         city=city_obj)
        entity.address = address
        entity.save()
        return entity

    def create_entity_ref_data(self):
        entity_data = deepcopy(entity_test_data.CREATE_ENTITIES[0])

        # Fix ids of objects when required
        industry_name = entity_data.get("industry")
        sector_name = entity_data.get("sector")
        city_name = entity_data.get("address").get("city")

        industry_obj = Industry.objects.get(industry=industry_name)
        sector_obj = Sector.objects.get(sector=sector_name)
        city_obj = City.objects.get(city=city_name)

        entity_data["industry"] = industry_obj.id
        entity_data["sector"] = sector_obj.id
        entity_data["address"]["city"] = city_obj.id
        return entity_data

    def update_entity_ref_data(self, existing_data=None):
        update_ref_data = entity_test_data.UPDATE_ENTITIES[0]
        update_data = existing_data
        company_size_name = update_ref_data.get("company_size")
        category_name = update_ref_data.get("category")

        company_size_obj = CompanySize.objects.get(size=company_size_name)
        category_obj = Category.objects.get(name=category_name)

        update_data["category"] = category_obj.id
        update_data["company_size"] = company_size_obj.id
        update_data["linked_in"] = update_ref_data.get("linked_in")
        update_data["twitter"] = update_ref_data.get("twitter")
        update_data["schedule_appointment"] = update_ref_data.get("schedule_appointment")
        update_data["description"] = update_ref_data.get("description")
        return update_data


class EntityBrochureTestMixin(object):
    def add_brochure(self, brochure_name=None, entity=None, brochure_file=None):
        instance = EntityBrochure()
        instance.brochure_name = brochure_name
        instance.entity = entity
        file_path = None
        if brochure_file is not None:
            file_path = os.path.join(entity_test_data.TEST_FILES_PATH, brochure_file)
            django_file = File(open("{}".format(file_path), "rb"))
            instance.brochure = django_file
            instance.brochure.name = brochure_file

        instance.save()

        return instance


class EntityPromoVideoTestMixin(object):
    def add_promotional_video(self, name=None, entity=None, url=None):
        instance = EntityPromotionalVideo()
        instance.entity = entity
        instance.promotional_video_name = name
        instance.promotional_video_url = url

        instance.save()

        return instance
