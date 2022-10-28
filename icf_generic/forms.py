import threading
import time

from dal import autocomplete
from django import forms
from django.forms import ModelForm

from icf_generic.models import QuestionCategory, FAQCategory


class CreateFAQForm(ModelForm):

    category = forms.ModelMultipleChoiceField(queryset=FAQCategory.objects.all(),
                                          widget=autocomplete.ModelSelect2Multiple(
                                            url='/api/generic/faq-category-autocomplete/'), required=False)

    def __init__(self, *args, **kwargs):
        super(CreateFAQForm, self).__init__(*args, **kwargs)

    class Meta:
        model = QuestionCategory
        fields = '__all__'
