from rest_framework import status

from icf_generic.Exceptions import ICFException
from icf_orders.CalculateCreditHelper import CalculateCreditChargeHelper
from icf_orders.app_settings import PURCHASE_CREDITS
from icf_orders.models import CreditAction, CreditHistory, AvailableBalance
from django.utils.translation import ugettext_lazy as _


class EntityDefaultCreditManager:

    def assign_default_credits_to_entity(self, entity, user, no_of_credits):
        # create  new record in AvailableBalance Table and CreditHistory Table to the user for this entity
        try:
            action = CreditAction.objects.get(action=PURCHASE_CREDITS)
        except CreditAction.DoesNotExist:
            raise ICFException(_("Invalid action, please check and try again."),
                               status_code=status.HTTP_400_BAD_REQUEST)
        try:
            credit_history = CreditHistory.objects.get(entity=entity, user=user, action=action)
            # entity_balance = AvailableBalance.objects.get(entity=entity)
            pass
        except CreditHistory.DoesNotExist as cdne:
            CreditHistory.objects.create(entity=entity, user=user,
                                         available_credits=no_of_credits, action=action)
            entity_balance = AvailableBalance.objects.create(entity=entity, user=user,
                                                             available_credits=no_of_credits)
            CalculateCreditChargeHelper().assign_all_credits_to_job(entity, no_of_credits)
