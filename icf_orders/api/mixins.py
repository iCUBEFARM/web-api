import math
from datetime import datetime, timedelta, date

import pytz
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.aggregates import Sum
from pytz import UTC

from icf_orders import app_settings
from icf_orders.app_settings import CREATE_JOB
from icf_orders.models import CreditHistory, CreditDistribution, CreditAction, AvailableBalance, Subscription, \
    SubscriptionAction
from icf_generic.Exceptions import ICFException
from rest_framework import status
from django.utils.translation import ugettext_lazy as _
import logging

logger = logging.getLogger(__name__)


class ICFCreditManager:
    NO_CREDITS = 0



    @classmethod
    def get_available_credit(cls, entity=None):
        credit = AvailableBalance.objects.filter(entity=entity).first()
        if credit:
            return credit.available_credits
        else:
            return cls.NO_CREDITS

    @classmethod
    def get_total_assigned_credit(cls, entity=None):
        credit = CreditDistribution.objects.filter(entity=entity).aggregate(Sum('credits'))['credits__sum']
        return credit or cls.NO_CREDITS


    @classmethod
    def get_unassigned_credit(cls, entity=None):
        try:
            available_credit = cls.get_available_credit(entity)
            assigned_credit = cls.get_total_assigned_credit(entity)
            return available_credit - assigned_credit
        except Exception:
            return cls.NO_CREDITS

    @classmethod
    def get_interval_for_action(cls, action):

        try:
            return CreditAction.objects.get(action=action).interval
        except Exception:
            return app_settings.DEFAULT_INTERVAL

    @classmethod
    def get_credit_for_action(cls, action=None, interval=1):
        try:
            credit_action = CreditAction.objects.get(action=action)
            return credit_action.credit_required * interval
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise ICFException(_("Invalid action, could not obtain required credits"), status_code=status.HTTP_400_BAD_REQUEST)

    @classmethod
    def get_num_of_intervals(cls, start_date, end_date, action):

        try:
            if (end_date - start_date).days == 0:
                return 1
            return math.ceil((end_date - start_date).days / cls.get_interval_for_action(action))
        except Exception as e:
            logger.debug("Invalid start date or end date")
            raise ICFException(_("Please review your start date and end date and try again. You can contact Customer Support to get help."),
                               status_code=status.HTTP_400_BAD_REQUEST)

    @classmethod
    def change_to_interval(cls, start1, end1, start2, end2, action):
        interval1 = cls.get_num_of_intervals(start1, end1, action)
        interval2 = cls.get_num_of_intervals(start2, end2, action)

        # Return the changed interval if the new interval is greater than the original
        if interval2 > interval1:
            return interval2 - interval1

        return 0

    @classmethod
    def is_valid_interval(cls, start_date, end_date):
        return end_date >= start_date

    @classmethod
    def is_allowed_interval(cls, start_date, end_date):
        if end_date >= start_date:
            today = datetime.now(pytz.utc).date()
            if start_date.date() >= today:
                return True

        return False

    # @classmethod
    # def check_entity_subscription(cls, entity=None, action=None, job_start_date=None, job_end_date=None, user=None, app=None):
    #     result_dict = {
    #         "subscription_with_overflow": False,
    #         "subscription_without_overflow": False,
    #     }
    #
    #     try:
    #         action_id = CreditAction.objects.get(action=action)
    #         subscribed_entity = Subscription.objects.filter(entity=entity, action=action_id).first()
    #         result_dict ={
    #             "subscription_without_overflow": False,
    #             "subscription_with_overflow": False,
    #         }
    #         if subscribed_entity:
    #             subscribed_entity_start_date_with_timezone = datetime(subscribed_entity.start_date.year, subscribed_entity.start_date.month, subscribed_entity.start_date.day, tzinfo=UTC)
    #             subscribed_entity_end_date_with_timezone = datetime(subscribed_entity.end_date.year, subscribed_entity.end_date.month, subscribed_entity.end_date.day, tzinfo=UTC)
    #
    #             if subscribed_entity_start_date_with_timezone <= job_start_date and subscribed_entity_end_date_with_timezone <= job_end_date and subscribed_entity.action_count < subscribed_entity.max_count:
    #                 # if subscribed_entity.action_count < subscribed_entity.max_count:
    #                 #     subscribed_entity.action_count = subscribed_entity.action_count+1
    #                 #     subscribed_entity.save(update_fields=['status'])
    #
    #                 result_dict["subscription_without_overflow"] = True
    #                 result_dict["subscription_with_overflow"] = False
    #
    #                 # return result_dict
    #             elif subscribed_entity_start_date_with_timezone <= job_start_date and subscribed_entity_end_date_with_timezone > job_end_date:
    #                 # intervals = cls.get_num_of_intervals(subscribed_entity.end_date, job_end_date, action)
    #                 # cls.charge_for_action(user=user, entity=entity, app=app, action=action, intervals=intervals)
    #                 result_dict["subscription_without_overflow"] = False
    #                 result_dict["subscription_with_overflow"] = True
    #
    #             else:
    #                 result_dict["subscription_without_overflow"] = False
    #                 result_dict["subscription_with_overflow"] = True
    #             return result_dict
    #     except Exception as e:
    #         print(str(e))
    #         return result_dict

    @classmethod
    def manage_entity_subscription(cls, entity=None, action=None, item_start_date=None, item_end_date=None, user=None, app=None):
        """ checks if the given entity has the subscription wirh possible conditions and if not charge for credit """
        try:
            action_obj = CreditAction.objects.get(action=action)
            subscribed_entity = Subscription.objects.filter(start_date__lte=datetime.today().date(), end_date__gt=datetime.today().date(), entity=entity, is_active=True).first()
            subscription_action = SubscriptionAction.objects.filter(subscription=subscribed_entity, action=action_obj).first()

            if subscribed_entity and subscription_action:
                subscribed_entity_start_date_with_timezone = datetime(subscribed_entity.start_date.year, subscribed_entity.start_date.month, subscribed_entity.start_date.day, tzinfo=UTC)
                subscribed_entity_end_date_with_timezone = datetime(subscribed_entity.end_date.year, subscribed_entity.end_date.month, subscribed_entity.end_date.day, 23, 59, 59, 999999, tzinfo=UTC)

                if subscribed_entity_start_date_with_timezone <= item_start_date and subscribed_entity_end_date_with_timezone >= item_end_date and subscription_action.action_count < subscription_action.max_count:
                    subscription_action.action_count += 1                 # update the action count by increamenting by 1
                    subscription_action.save(update_fields=['action_count'])

                elif subscribed_entity_start_date_with_timezone <= item_start_date and subscribed_entity_end_date_with_timezone < item_end_date and subscription_action.action_count < subscription_action.max_count:

                    # now make the job's start date  as (subcribed_entity's end_date + 1)
                    #  and charge for remaining days(no of overflown days)

                    jobs_start_date_to_charge_for_credits = subscribed_entity_end_date_with_timezone + timedelta(days=1)
                    intervals = cls.get_num_of_intervals(jobs_start_date_to_charge_for_credits, item_end_date, action)

                    # if the entity has insufficient credits for overflown days
                    # i.e   (job_end_date - subscribed_entity.end_date) = no of overflown days
                    # Icf Exception is raised saying insuffiecient credits for given intervals
                    #  and will not allow him to post the job in charge_for_action method

                    cls.charge_for_action(user=user, entity=entity, app=app, action=action, intervals=intervals)

                    # if the entity has sufficient credits for overflown days
                    # and charged credits successfully  update the action count
                    subscribed_entity.action_count += 1        # update the action count by increamenting by 1
                    subscribed_entity.save(update_fields=['action_count'])

                else:
                    # subscribed_entity_start_date_with_timezone <= job_start_date and subscribed_entity_end_date_with_timezone < job_start_date:
                    intervals = cls.get_num_of_intervals(item_start_date, item_end_date, action)
                    ICFCreditManager.charge_for_action(user=user, entity=entity, app=app, action=action,
                                                       intervals=intervals)

            else:
                intervals = cls.get_num_of_intervals(item_start_date, item_end_date, action)
                ICFCreditManager.charge_for_action(user=user, entity=entity, app=app, action=action, intervals=intervals)
        except Exception as e:
            # print(str(e))
            logger.error("something went wrong reason {}".format(str(e)))
            raise

    @classmethod
    def charge_for_action(cls, user=None, entity=None, app=None, action=None, intervals=1):

        credit_required = cls.get_credit_for_action(action=action, interval=intervals)

        try:
            assigned_credit = CreditDistribution.objects.get(entity=entity, app__content_type=app)
        except ObjectDoesNotExist:
            logger.exception("Insufficient credits available for the app")
            raise ICFException(_("Insufficient credits are avaialble for {}. Please contact your entity admin for clarification.".format(app)),
                               status_code=status.HTTP_400_BAD_REQUEST)

        available_balance = AvailableBalance.objects.filter(entity=entity).first()
        if not available_balance:
            logger.exception("There are no credits available for the entity")
            raise ICFException(_("Your entity has no credits left. Please contact your entity admin to request for credits."),
                               status_code=status.HTTP_400_BAD_REQUEST)

        # credit_history = CreditHistory.objects.filter(entity=entity).first()
        #
        # if not credit_history:
        #     raise ICFException(_("There are no credits available for the entity, please check with entity admin"),
        #                        status_code=status.HTTP_400_BAD_REQUEST)

        # available_credits = credit_history.available_credits
        available_credits = available_balance.available_credits

        if assigned_credit.credits >= credit_required:
            # update credit values in credit Usage and credit distribution
            update_available_credit = available_credits - credit_required
            try:
                action_obj = CreditAction.objects.get(action=action)
            except CreditAction.DoesNotExist as cadne:
                logger.exception("CreditAction object not found.".format(str(cadne)))
                raise ICFException(_("CreditAction not found."), status_code=status.HTTP_400_BAD_REQUEST)

            CreditHistory.objects.create(entity=entity, action=action_obj,
                                         debits=credit_required, user=user,
                                         available_credits=update_available_credit, is_active=True)

            assigned_credit.credits = assigned_credit.credits - credit_required
            assigned_credit.save(update_fields=['credits', ])
            available_balance.available_credits = update_available_credit
            available_balance.save(update_fields=['available_credits', ])

        else:
            logger.exception("Insufficient credits available to perform action")
            raise ICFException(_("You need more credits to perform this action. Please contact"
                                 " your entity admin to request for credits."), status_code=status.HTTP_400_BAD_REQUEST)
