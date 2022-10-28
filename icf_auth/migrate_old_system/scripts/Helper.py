from icf_generic.models import Language


class Helper:
    @staticmethod
    def get_language_id(language_code):
            language = Language.objects.filter(code__iexact=language_code).first()
            if not language:
                raise Language.DoesNotExist()
            else:
                return language


gender_choices_dict = {
    "m": "M",
    "f": "F"
}
