from django.apps import AppConfig


class IcfFeaturedeventsConfig(AppConfig):
    name = 'icf_featuredevents'
    verbose_name = "featured events"

    def ready(self):
        import icf_featuredevents.signals
