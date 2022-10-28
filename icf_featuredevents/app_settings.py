from django.utils.translation import ugettext_lazy as _


FEATURED_EVENT_DETAILS = {
    'event_name': _("event_name"),
    'entity_name': _("entity_name"),
    'email': _("email"),
    'contact_no': _("contact_no"),
    'name_of_representative': _("name_of_representative"),
    'address': _("address")

}


BANK_DETAILS = {
    'bank_name_info': _("bank_name_info"),
    'bank_address_info': _("bank_address_info"),
    'beneficiary_info': _("beneficiary_info"),
    'office_code': _("office_code"),
    'agency_code': _("agency_code"),
    'account_number': _("account_number"),
    'swift_code': _("swift_code"),
    'iban': _("iban")
}

FEATURED_EVENT_ACCOUNT_DETAILS = {
    'bank_name': _("CCEIBANK"),
    'bank_address': _("Malabo II, Malabo, Equatorial Guinea"),
    'beneficiary': _("ICUBEFARM EG SL"),
    'office_code': "50001",
    'agency_code': "00001",
    'account_number': "01034651001-14",
    'swift_code': "CCEIGQGQ",
    'iban': "GQ70 50001 00001 01034651001-14"

}


PRODUCT_INFO = {
    'product_name': _("product_name")

}


FEATURED_EVENT_RECEIPT_SUBJECT = _("Payment receipt for Featured event participation")

FEATURED_EVENT_RECEIPT_EMAIL_BODY = _("""Dear {0},\n Find attached payment receipt for your purchase order for iCUBEFARM {1} participation. For
questions about this payment, please contact billing@icubefarm.com""")


FEATURED_EVENT_RECEIPT_EMAIL_CC = ["devops@icubefarm.com", "renuka.nm@thinkcoretech.com"]


FEATURED_EVENT_PAYMENT_FAILURE_SUBJECT = "Payment Failed : {0}"


FEATURED_EVENT_PAYMENT_FAILURE_EMAIL_BODY = "Details: <br>Payment Type:{0} <br> Entity Name :{1} <br> User :{2} <br> User Email :{3} <br> " \
                                            "User Contact No :{4} <br>Products {5}Participants :{6} <br> Total Cost: {7}"


FEATURED_EVENT_PAYMENT_FAILURE_NOTIFICATION_EMAIL = "billing@icubefarm.com",


PRODUCT_INFO_STR = "<br>Product Name : {0}, Quantity : {1}<br>"








