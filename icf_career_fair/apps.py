from django.apps import AppConfig


class IcfCareerFairsConfig(AppConfig):
    name = 'icf_career_fair'
    verbose_name = "career fairs"

    def ready(self):
        import icf_career_fair.signals

