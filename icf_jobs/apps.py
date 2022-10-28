from django.apps import AppConfig


class IcfJobsConfig(AppConfig):
    name = 'icf_jobs'
    verbose_name = "jobs"

    def ready(self):
        import icf_jobs.signals

