from django.core.exceptions import ValidationError
from django.utils import dateformat
import re
from django_date_extensions.fields import ApproximateDateField, ApproximateDate
import datetime


class ICFApproxDate(ApproximateDate):

    IGNORE_YEAR = 9999

    def __init__(self, year=0, month=0, day=0, present=False):
        if present:
            if year or month or day:
                raise ValueError("Present can have no year, month or day")
        else:
            if month:
                months = range(1,13)
                if month not in months:
                    raise ValueError("Invalid month")

            if year and month and day:
                datetime.date(year, month, day)
            elif year and month:
                datetime.date(year, month, 1)
            elif year and day:
                raise ValueError("You cannot specify just a year and a day")
            elif year:
                datetime.date(year, 1, 1)
            else:
                raise ValueError("You must specify a year")

        self.present = present

        if present:
            year = self.IGNORE_YEAR

        super(ICFApproxDate, self).__init__(year=year, month=month, day=day)

    def __repr__(self):
        if self.present:
            return str(self)
        else:
            return super(ICFApproxDate, self).__repr__()

    def __str__(self):
        if self.present:
            return 'present'
        else:
            return super(ICFApproxDate, self).__str__()

    def __eq__(self, other):
        if isinstance(other, (datetime.date, datetime.datetime)):
            return (self.year, self.month, self.day) == \
                   (other.year, other.month, other.day)

        if not isinstance(other, ICFApproxDate):
            return False

        if self.present and other.present:
            return True

        return (self.year, self.month, self.day) == \
               (other.year, other.month, other.day)

    def __lt__(self, other):
        if other is None:
            return False

        if isinstance(other, ICFApproxDate):
            if self.present or other.present:
                return not self.present

        return (self.year, self.month, self.day) < (other.year, other.month, other.day)

ansi_date_re = re.compile(r'^\d{4}-\d{1,2}-\d{1,2}$')


class ICFApproxDateField(ApproximateDateField):

    # def __init__(self, *args, **kwargs):
    #     kwargs['max_length'] = 10
    #     super(ICFApproxDateField, self).__init__(*args, **kwargs)

    def from_db_value(self, value, expression=None, connection=None, context=None):

        if value == 'present':
            return ICFApproxDate(present=True)

        return super(ICFApproxDateField, self).from_db_value(value, expression=expression,
                                                             connection=connection, context=context)


    def get_prep_value(self, value):
        if value in (None, ''):
            return ''
        if isinstance(value, ApproximateDate):
            return repr(value)
        if isinstance(value, datetime.date):
            return dateformat.format(value, "Y-m-d")
        if value == 'present':
            return 'present'
        if value == 'future':
            return 'future'
        if value == 'past':
            return 'past'
        if not ansi_date_re.search(value):
            raise ValidationError('Enter a valid date in YYYY-MM-DD format.')
        return value

