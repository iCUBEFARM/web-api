# class CalculateProductPurchaseChargeHelper:

    # def calculate_charges_without_tax_in_cents(self, cost_for_credit, no_of_credits):
    #     total_amount_in_USD = (eval(cost_for_credit.cost) * no_of_credits / cost_for_credit.credits)
    #     total_amount_in_cents = (eval(cost_for_credit.cost) * no_of_credits / cost_for_credit.credits) * 100
    #
    #     amount_withput_tax_dict = {
    #         'total_amount_without_tax_in_cents': total_amount_in_cents,
    #         'total_amount_without_tax_in_USD': total_amount_in_USD
    #
    #     }
    #
    #     return amount_withput_tax_dict

    # def calculate_product_charge_with_tax_in_cents_and_USD(self, entity, total_amount_in_cents):
    #     try:
    #         # total_amount_in_USD = (self.total_amount / 100)
    #         country_tax = CountryTax.objects.get(country=entity.address.city.state.country)
    #         VAT_CENTS = total_amount_in_cents * (country_tax.percentage / 100)
    #         total_amount_with_tax_in_cents = round(total_amount_in_cents + VAT_CENTS)
    #         total_amount_with_tax_in_USD = total_amount_with_tax_in_cents / 100
    #         VAT_USD = (VAT_CENTS / 100)
    #
    #     except CountryTax.DoesNotExist as cnd:
    #         country_tax = CountryTax.objects.get(country__country__iexact=settings.DEFAULT_COUNTRY_FOR_COUNTRY_TAX)
    #         VAT_CENTS = round(total_amount_in_cents * (country_tax.percentage / 100))
    #         total_amount_with_tax_in_cents = round(total_amount_in_cents + VAT_CENTS)
    #         total_amount_with_tax_in_USD = total_amount_with_tax_in_cents / 100
    #         VAT_USD = (VAT_CENTS / 100)
    #
    #     amount_dict = {
    #
    #         'total_amount_with_tax_in_cents': total_amount_with_tax_in_cents,
    #         'total_amount_with_tax_in_USD': total_amount_with_tax_in_USD,
    #         'VAT_CENTS': VAT_CENTS,
    #         'VAT_USD': VAT_USD
    #
    #     }
    #
    #     return amount_dict