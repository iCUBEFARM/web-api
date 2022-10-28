from django.utils.translation import ugettext_lazy as _

SEND_INVITE_TO_JOB_SEEKER_EMAIL = _("Invitation to apply")

common_body = _("""Dear {job_seeker_user_name},<br><p>
{entity_name} is inviting you to apply their following open roles.</p>
<p> If you are interested in this opportunity, reply to this message here and we will get in touch.</p><br>
Job links:
""")

message_user_name_part = _("""<span style="font-size:16px;font-weight: bold;">Dear {job_seeker_user_name},</span><br>""")
message_text_body_part = _("""<p>
{entity_name} is inviting you to apply their following open roles.</p>
<p> If you are interested in this opportunity, reply to this message here and we will get in touch.</p><br>
Job links:
""")
