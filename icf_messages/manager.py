from icf_messages.models import ICFNotification


class ICFNotificationManager:

    @classmethod
    def add_notification(cls, user=None,message=None, message_french=None, message_spanish=None, details=None, details_french=None, details_spanish=None):
        notification = ICFNotification.objects.populate(True).create(
                        user=user,
                        message=message,
                        message_en=message,
                        message_fr=message_french,
                        message_es=message_spanish,
                        details=details,
                        details_en=details,
                        details_fr=details_french,
                        details_es=details_spanish
                        )
        return notification

    @classmethod
    def get_notication_list(cls, user=None):
        notification = ICFNotification.objects.filter(user=user,deleted_at=None)
        return notification




