from django.apps import AppConfig


class IcfEventsConfig(AppConfig):
    name = 'icf_events'
    verbose_name = "entity events"

    def ready(self):
        import icf_events.signals
