from django.apps import AppConfig


class IcfCovidStatusConfig(AppConfig):
    name = 'icf_covid_status'
    verbose_name = "covid statuses"


    def ready(self):
        import icf_covid_status.signals

