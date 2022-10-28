from pytz import unicode

from icf_orders.models import CountryTax, CreditDistribution
from icf import settings
import logging

from icf_generic.models import Type

from django.utils.translation import gettext_lazy as _


payment_logger = logging.getLogger("icf.integrations.payment")


class CalculateCreditChargeHelper:

    def calculate_charges_and_tax_in_for_credit_product(self, product, no_of_credits, entity):
        ''' calculate credit cost  '''

        total_amount_without_tax_in_USD = (float(product.cost) / product.unit) * no_of_credits

        try:
            if entity.address:
                country_tax = CountryTax.objects.get(country=entity.address.city.state.country)
            else:
                country_tax = CountryTax.objects.get(country__country__iexact=settings.DEFAULT_COUNTRY_FOR_COUNTRY_TAX)

            VAT_USD = float(total_amount_without_tax_in_USD) * (country_tax.percentage / 100)
            total_amount_with_tax_in_USD = float(total_amount_without_tax_in_USD) + VAT_USD
            total_amount_with_tax_in_cents = int(round(total_amount_with_tax_in_USD, 2) * 100)  # round off the value so we should get the calculation in cents properly
            VAT_CENTS = (VAT_USD * 100)

        except CountryTax.DoesNotExist as cnd:
            country_tax = CountryTax.objects.get(country__country__iexact=settings.DEFAULT_COUNTRY_FOR_COUNTRY_TAX)
            VAT_USD = float(total_amount_without_tax_in_USD) * (country_tax.percentage / 100)
            total_amount_with_tax_in_USD = float(total_amount_without_tax_in_USD) + VAT_USD
            total_amount_with_tax_in_cents = int(round(total_amount_with_tax_in_USD, 2) * 100)  # round off the value so we should get the calculation in cents properly
            VAT_CENTS = (VAT_USD * 100)

        amount_dict = {

            'total_amount_with_tax_in_cents': total_amount_with_tax_in_cents,
            'total_amount_with_tax_in_USD': total_amount_with_tax_in_USD,
            'VAT_CENTS': VAT_CENTS,
            'VAT_USD': VAT_USD

        }

        return amount_dict

    def calculate_charges_without_tax_in_cents(self, cost_for_credit, no_of_credits):

        total_amount_in_USD = (float(cost_for_credit.cost) / cost_for_credit.unit) * no_of_credits
        total_amount_in_cents = int(round((float(cost_for_credit.cost) / cost_for_credit.unit) * no_of_credits, 2) * 100)

        amount_withput_tax_dict = {
            'total_amount_without_tax_in_cents': total_amount_in_cents,
            'total_amount_without_tax_in_USD': total_amount_in_USD

        }

        return amount_withput_tax_dict

    def calculate_charge_with_tax_in_cents_and_USD(self, total_amount_without_tax_in_USD, entity):
        try:
            if entity and entity.address:
                country_tax = CountryTax.objects.get(country=entity.address.city.state.country)
            else:
                country_tax = CountryTax.objects.get(country__country__iexact=settings.DEFAULT_COUNTRY_FOR_COUNTRY_TAX)

            VAT_USD = float(total_amount_without_tax_in_USD) * (country_tax.percentage / 100)
            total_amount_with_tax_in_USD = float(total_amount_without_tax_in_USD) + VAT_USD
            total_amount_with_tax_in_cents = int(round(total_amount_with_tax_in_USD, 2) * 100)  # round off the value so we should get the calculation in cents properly
            VAT_CENTS = (VAT_USD * 100)

        except CountryTax.DoesNotExist as cnd:
            country_tax = CountryTax.objects.get(country__country__iexact=settings.DEFAULT_COUNTRY_FOR_COUNTRY_TAX)
            VAT_USD = float(total_amount_without_tax_in_USD) * (country_tax.percentage / 100)
            total_amount_with_tax_in_USD = float(total_amount_without_tax_in_USD) + VAT_USD
            total_amount_with_tax_in_cents = int(round(total_amount_with_tax_in_USD, 2) * 100)  # round off the value so we should get the calculation in cents properly
            VAT_CENTS = (VAT_USD * 100)

        amount_dict = {

            'total_amount_with_tax_in_cents': total_amount_with_tax_in_cents,
            'total_amount_with_tax_in_USD': total_amount_with_tax_in_USD,
            'VAT_CENTS': VAT_CENTS,
            'VAT_USD': VAT_USD

        }

        return amount_dict

    def assign_all_credits_to_job(self, entity, no_of_credits):

        try:
            entity = entity
            job_str = unicode(_('job'))
            app = Type.objects.get(name__iexact=job_str)
            credit_distribution = CreditDistribution.objects.filter(entity=entity, app=app).first()
            if credit_distribution:
                credits_to_be_updated = credit_distribution.credits + no_of_credits
                credit_distribution.credits = credits_to_be_updated
                credit_distribution.save(update_fields=['credits'])
            else:
                CreditDistribution.objects.create(entity=entity, app=app, credits=no_of_credits)
        except Exception as e:
            payment_logger.info("exception while assigning all credits to job reason ".format(str(e)))
            raise









