from django.utils.translation import ugettext_lazy as _


DEFAULT_CURRENCY = "USD"
# Default interval for posting
DEFAULT_INTERVAL = 30

INVOICE_EMAIL_SUBJECT = _("Invoice for iCUBEFRAM Credits")
INVOICE_EMAIL_BODY = _("""Dear {},\nFind attached an invoice for your purchase order for iCUBEFARM credits. For
questions about this invoice, please contact billing@icubefarm.com""")
INVOICE_EMAIL_CC = "mosesibe@gmail.com"
PAYMENT_RECEIPT_EMAIL_CC = "devops@icubefarm.com"

ICUBE_ADDRESS = {
    'name' : "iCUBEFARM GE S.L.",
    'address_1' :"Barrio Paraiso, S/N",
    'address_2' : "Malabo",
    'city' : "Equitorial Guinea",
    'phone' : "Telephone: + 240 333 091204",
    'registration_number':"Business registration number: 00185R-13"
}

ACCOUNT_DETAILS = {
    'bank_code' : "50004",
    'bank_agency':"05110",
    'account_number':"42006842012 – 05",
    'swift_code':"BGFIGQGQXXX",
    'IBAN':"GQ70 5000 4051 1042 0068 42012  05",
    'bank_name': _("BGFI Bank Guinea Ecuatorial"),
    'bank_address': _("Calle Bata, Malabo, Equatorial Guinea"),
    'beneficiary_name': _("iCUEFARM GE SL Operationes")

}

PURCHASE_CREDITS = "purchase_credits"
CREATE_JOB = "create_job"
SPONSORED_JOB = "sponsored_job"
CREATE_ENTITY = "create_entity"
SPONSORED_ENTITY = "sponsored_entity"
CREATE_EVENT = "create_event"
SPONSORED_EVENT = "sponsored_event"
CREATE_CAREER_FAIR = "create_career_fair"
SPONSORED_CAREER_FAIR = "sponsored_career_fair"



Non_Refund_Policy = _("""iCUBEFARM will not generate any type of refund of money.The amounts paid will not be returned
for any reason.\n All sales final are not refundable, not return, not exchange, not transfer, etc. In accordance with
the\n conditions mentioned above and under no circumstances, the amount paid for the services of\n the iCUBEFARM.com
portal is reimbursable.""")


PAYMENT_RECEIPT_EMAIL_BODY = _("""Dear {},\nFind attached payment receipt for your purchase order for iCUBEFARM credits. For
questions about this payment, please contact billing@icubefarm.com""")

PAYMENT_RECEIPT_SUBJECT = _("Payment receipt for iCUBEFRAM Credits")

EXCHANGE_RATE = _("If paying into the above bank account -  the fixed exchange rate is 1USD = 600 XFA")



FEATURED_EVENT_RECEIPT_SUBJECT = _("Payment receipt for Featured event participation")

FEATURED_EVENT_RECEIPT_EMAIL_BODY = _("""Dear {},\nFind attached payment receipt for your purchase order for iCUBEFARM featured event participation. For
questions about this payment, please contact billing@icubefarm.com""")


FEATURED_EVENT_RECEIPT_EMAIL_CC = "devops@icubefarm.com"

# ------------------------------------------------------------------------------

SUBSCRIPTION_DETAILS ={

    'subscription_plan_name': _("subscription_plan_name"),
    'entity_name': _("entity_name"),
    'cost': _("cost"),
    'duration': _("duration"),
    'description': _("description"),
    # 'address': _("address")
}


SUBSCRIPTION_BANK_DETAILS = {
    'bank_name_info': _("bank_name_info"),
    'bank_address_info': _("bank_address_info"),
    'beneficiary_info': _("beneficiary_info"),
    'office_code': _("office_code"),
    'agency_code': _("agency_code"),
    'account_number': _("account_number"),
    'swift_code': _("swift_code"),
    'iban': _("iban")

}


SUBSCRIPTION_PLAN_ACCOUNT_DETAILS = {
    'bank_name': _("CCEIBANK"),
    'bank_address': _("Malabo II, Malabo, Equatorial Guinea"),
    'beneficiary': _("ICUBEFARM EG SL"),
    'office_code': "50001",
    'agency_code': "00001",
    'account_number': "01034651001-14",
    'swift_code': "CCEIGQGQ",
    'iban': "GQ70 50001 00001 01034651001-14"

}


SUBSCRIPTION_INFO = {

    'action_name': _("action_name"),
    'start_date': _("start_date"),
    'end_date': _("end_date")

}

CREDIT_DETAILS = {

    'entity_name': _("entity_name"),
    'entity_address': _("entity_address"),
    'entity_city': _("entity_city")

}


FEATURED_EVENT_PARTICIPANT_DETAILS = {

    'featured_event_name': _("featured_event_name"),
    'entity_name': _("entity_name"),
    'entity_email': _("entity_email"),
    'contact_no': _("contact_no"),
    'name_of_representative': _("name_of_representative"),
    'participants': _("participants"),
    'address': _("address")

}

CAREER_FAIR_PARTICIPANT_DETAILS = {

    'career_fair_name': _("career_fair_name"),
    'entity_name': _("entity_name"),
    'participant_type': _("participant_type"),
    'representative_email': _("representative_email"),
    'name_of_representative': _("name_of_representative"),
    'address': _("address")

}


SUBSCRIPTION_PLAN_RECEIPT_EMAIL_BODY = _("""Dear {0},\nFind attached payment receipt for your purchase order for {1}. For
questions about this payment, please contact billing@icubefarm.com""")


SUBSCRIPTION_PLAN_RECEIPT_SUBJECT = _("Payment receipt for Subscription purchase")


SUBSCRIPTION_PLAN_RECEIPT_EMAIL_CC = ["devops@icubefarm.com", ]


PURCHASE_CREDITS_PAYMENT_FAILURE_NOTIFICATION_EMAIL = "billing@icubefarm.com"
# PURCHASE_CREDITS_PAYMENT_FAILURE_NOTIFICATION_EMAIL = "renuka.nm@thinkcoretech.com"


PURCHASE_CREDITS_PAYMENT_FAILURE_SUBJECT = "Payment Failed : {0} while purchasing credits for entity "


PURCHASE_CREDITS_PAYMENT_FAILURE_EMAIL_BODY = "Details: <br>Payment Type:{0} <br> Entity Name :{1} <br> User :{2} <br> User Email :{3} <br> " \
                                            "Total Cost: {4}"


PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_SUBJECT = "Payment Failed : {0} while purchasing subscription for entity "


PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_EMAIL_BODY = "Details: <br>Payment Type:{0} <br> Entity Name :{1} <br> User :{2} <br> User Email :{3} <br> " \
                                            "Total Cost: {7}"

PURCHASE_SUBSCRIPTION_PAYMENT_FAILURE_NOTIFICATION_EMAIL = "billing@icubefarm.com",

# ---------------------------------------------------------------------------

PRODUCT_PURCHASE_RECEIPT_SUBJECT = _("Payment receipt for products purchase.")

PRODUCT_PURCHASE_RECEIPT_EMAIL_BODY = _("""Dear {0},<br> Find attached payment receipt for your purchase order of products.
 For questions about this payment, please contact billing@icubefarm.com""")


PRODUCT_PURCHASE_RECEIPT_EMAIL_CC = ["devops@icubefarm.com", ]


PURCHASE_PRODUCTS_PAYMENT_FAILURE_SUBJECT = _("Payment Failed : {0} while purchasing products.")

PURCHASE_PRODUCTS_PAYMENT_FAILURE_EMAIL_BODY =\
    "Details: <br>Payment Type:{0}  <br> User :{1} <br> User Email :{2} <br> " \
    "Total Cost: {3}"

PURCHASE_PRODUCTS_PAYMENT_FAILURE_NOTIFICATION_EMAIL = "billing@icubefarm.com",

BILLING_ADDRESS_DETAILS = {
    'Name': _("Name"),
    'Email': _("Email"),
    'Address': _("Address"),
    'Contact_no': _("Contact_no")
}


PRODUCTS_BANK_DETAILS = {
    'bank_name_info': _("bank_name_info"),
    'bank_address_info': _("bank_address_info"),
    'beneficiary_info': _("beneficiary_info"),
    'office_code': _("office_code"),
    'agency_code': _("agency_code"),
    'account_number': _("account_number"),
    'swift_code': _("swift_code"),
    'iban': _("iban")
}

PRODUCTS_ACCOUNT_DETAILS = {
    'bank_name': _("CCEIBANK"),
    'bank_address': _("Malabo II, Malabo, Equatorial Guinea"),
    'beneficiary': _("ICUBEFARM EG SL"),
    'office_code': "50001",
    'agency_code': "00001",
    'account_number': "01034651001-14",
    'swift_code': "CCEIGQGQ",
    'iban': "GQ70 50001 00001 01034651001-14"

}









