from django.contrib.contenttypes.models import ContentType

from icf_entity.models import Sector, Industry, CompanySize
from icf_generic.models import City, Category, Type
from icf_jobs.migrate_old_system.data.Category_Mapping_Dictionary import category_dict


class Utility:

    # @staticmethod
    # def get_type_obj():
    #     try:
    #         type_obj = Type.objects.get(name=type_name.lower())
    #         return type_obj
    #     except Type.DoesNotExist as cdn:
    #         type_obj = Type.objects.create(name=type_name.lower())
    #         return type_obj

    @staticmethod
    def get_city(registered_address_city):
        registered_address_city = registered_address_city.lstrip().rstrip()
        city = City.objects.filter(city__iexact=registered_address_city).first()
        if not city:
            raise City.DoesNotExist()
        else:
            return city

    @staticmethod
    def get_sector(sectorname):
            sectorname = sectorname.lstrip().rstrip()
            sector = Sector.objects.filter(sector__iexact=sectorname).first()
            if not sector:
                raise Sector.DoesNotExist()
            else:
                return sector

    @staticmethod
    def get_industry(industryname):
        industryname = industryname.lstrip().rstrip()
        industry_name_dict_value = category_dict.get(industryname,'xxxxxx')
        industry = Industry.objects.filter(industry__iexact=industry_name_dict_value).first()
        if not industry:
            # raise Industry.DoesNotExist()
            industry = Industry.objects.create(industry=industry_name_dict_value)
            return industry
        else:
            return industry

    @staticmethod
    def get_category(categoryname):
        categoryname = categoryname.lstrip().rstrip()
        category_name_dict_value = category_dict.get(categoryname,'xxxxxx')
        category = Category.objects.filter(name__iexact=category_name_dict_value).first()
        if not category:
            content_type = ContentType.objects.get(model='entity')
            type_obj = Type.objects.get(content_type=content_type)
            category = Category.objects.create(name=category_name_dict_value, type=type_obj)
            return category
        else:
            return category

    @staticmethod
    def get_company_size(companysize):
        companysize = companysize.lstrip().rstrip()
        try:
            companysize_obj = CompanySize.objects.get(size__iexact=companysize)
        except CompanySize.DoesNotExist as cdn:
            companysize_obj = CompanySize.objects.create(size=companysize)
        return companysize_obj