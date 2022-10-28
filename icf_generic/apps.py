from django.apps import AppConfig


class IcfGenericConfig(AppConfig):
    name = 'icf_generic'
    verbose_name = "general"

    def ready(self):
        import icf_generic.signals


