from django.utils.translation import ugettext_lazy as _

CAREER_FAIR_REVIEW_EMAIL_SUBJECT = _("Career Fair : {0} : Administrator Review")

"""
Emails to user
"""
CAREER_FAIR_SENT_FOR_REVIEW_EMAIL_BODY = _("""Dear {0},<br> You have successfully created a career fair.
It has been sent to the administrator for approval. You will receive an email notification with the approval status.
 For any questions about career fairs, please contact admin@icubefarm.com""")

CAREER_FAIR_ADMIN_APPROVED_EMAIL_BODY = _("""Dear {0},<br> Your career fair has been approved by the Administrator.
  For any questions about career fairs, please contact admin@icubefarm.com""")

CAREER_FAIR_ADMIN_REJECTED_EMAIL_BODY = _("""Dear {0},<br> We regret to inform that your career fair cannot be approved at this time.
 For any questions about career fairs, please contact admin@icubefarm.com""")

"""
Email sent to admin
"""
CAREER_FAIR_ADMIN_REVIEW_EMAIL_BODY = _("""A new career fair has been created. It is available at {0}.""")

CAREER_FAIR_EMAIL_CC = "devops@icubefarm.com"

FREE_CAREER_FAIR_SUBSCRIPTION_EMAIL_SUBJECT = _("Free 90 days subscription activated")
FREE_CAREER_FAIR_SUBSCRIPTION_EMAIL_BODY = _(
    """Dear {0},<br>  90 Days  Subscription for your company {1} Is Active from today {2} till {3}""")

ADD_ADVERTISEMENT_LINK_TO_OWNER_EMAIL_SUBJECT = _("Recently added advertisement on iCUBEFARM")
ADD_ADVERTISEMENT_LINK_TO_OWNER_EMAIL_BODY = _(
    """Dear {0},<br>  Your company {1} has successfully added an advertisement product for the new career fair. <br> \
    Please click on the link to visit the entity dashboard. Click on advertisements tab and upload advertisement \
    images. {2}""")

ADD_ADVERTISEMENT_LINK_TO_BUYER_EMAIL_SUBJECT = _("Recently purchased advertisement on iCUBEFARM")
ADD_ADVERTISEMENT_LINK_TO_BUYER_EMAIL_BODY = _(
    """Dear {0},<br>Your company {1}, has successfully purchased an advertisement for a career fair. \
     Please click on the link to visit the entity dashboard. Click on advertisements tab and upload advertisement \
    images. {2}""")


ADVERTISEMENT_APPROVED_EMAIL_SUBJECT = _("{0} Ad image approved for career fair {1}")
ADVERTISEMENT_APPROVED_EMAIL_BODY = _(
    """Dear {0},<br>The {2} image uploaded for career fair {3} by your company {1} has been approved.<br> \
     """)

ADVERTISEMENT_REJECTED_EMAIL_SUBJECT = _("{0} Ad image rejected for career fair {1}")
ADVERTISEMENT_REJECTED_EMAIL_BODY = _(
    """Dear {0},<br>The {2} image uploaded for career fair {3} by your company {1} has been approved.<br> \
     Please click on the link to manage advertisement {4}""")