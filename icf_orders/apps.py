from django.apps import AppConfig


class IcfCreditsConfig(AppConfig):
    name = 'icf_orders'
    verbose_name = 'Orders'

    def ready(self):
        import icf_orders.signals
