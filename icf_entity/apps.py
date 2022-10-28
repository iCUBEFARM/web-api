from django.apps import AppConfig


class IcfEntityConfig(AppConfig):
    name = 'icf_entity'
    verbose_name = "entities"


    def ready(self):
        import icf_entity.signals

