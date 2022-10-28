from django.contrib.auth import authenticate
from django.core.exceptions import ObjectDoesNotExist
from knox.models import AuthToken

from icf_auth import app_settings
from icf_auth.rate_limiter.naive_flow_rate import NaiveFlowRate
from icf_auth.rate_limiter.smooth_flow_rate import SmoothFlowRate
from rest_auth.serializers import TokenSerializer, PasswordResetSerializer
from rest_framework import serializers, exceptions
from allauth.account import app_settings as allauth_settings
from allauth.account.adapter import get_adapter
from allauth.utils import email_address_exists
from allauth.account.utils import setup_user_email
from django.utils.translation import ugettext_lazy as _
from rest_framework.serializers import ModelSerializer, Serializer
from rest_framework.utils import model_meta

from icf import settings
from icf_auth.models import RegistrationOTP, User, UserProfile, UserProfileImage, RegistrationEmailOTP
from icf_auth.rate_limiter.throttle import Throttle
from icf_generic.api.serializers import AddressSerializer, AddressRetrieveSerializer
from icf_generic.models import Address, Country
from icf_integrations.email_otp import IcfEmailOTPManager
from icf_integrations.mobile import IcfOTPManager

import logging

from icf_orders.models import Cart

logger = logging.getLogger(__name__)


class ICFRegisterSerializer(serializers.Serializer):

    email = serializers.EmailField(required=allauth_settings.EMAIL_REQUIRED)
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    # The verified mobile number
    mobile = serializers.RegexField(regex=r'^\+?1?\d{9,15}$')

    # Mobile phone verified time
    time = serializers.DateTimeField(required=False)

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        if allauth_settings.UNIQUE_EMAIL:
            if email and email_address_exists(email):
                raise serializers.ValidationError(
                    _("A user is already registered with this e-mail address."))
        return email

    def validate_password1(self, password):
        return get_adapter().clean_password(password)

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError(_("The two password fields didn't match. Try again"))
        return data

    def custom_signup(self, request, user):
        pass

    def get_cleaned_data(self):
        return {
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
            'mobile': self.validated_data.get('mobile', ''),
            'mobile_verified_time': self.validated_data.get('time', '')
        }

    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()

        # Check if the verified phone number is sent along with the request
        mobile = self.cleaned_data.get('mobile')
        mobile_verified_time = self.cleaned_data.get('mobile_verified_time')

        # Look for the object in DB
        try:
            db_obj = RegistrationOTP.objects.get(mobile=mobile, updated=mobile_verified_time,
                                                 status=RegistrationOTP.REG_OTP_VERIFIED)
        except ObjectDoesNotExist as e:
            logger.exception(e)
            raise serializers.ValidationError({'mobile': _('Verify your phone number to continue registration')})

        adapter.save_user(request, user, self)
        self.custom_signup(request, user)
        setup_user_email(request, user, [])
        # try:
        #     # check if there any  entry for the current mobile no with resume file in
        #     # UnregisteredUserFileUpload table (if any unregistered user  uploaded resume with this mobile no)
        #     unregistered_user_file_upload_obj = UnregisteredUserFileUpload.objects.get(mobile=self.validated_data.get('mobile'))
        #     try:
        #         job_profile_file_upload_obj = JobProfileFileUpload.objects.get(user=user)
        #         job_profile_file_upload_obj.resume_src = unregistered_user_file_upload_obj.resume_src
        #         job_profile_file_upload_obj.save(update_fields=["resume_src", ])
        #
        #     except JobProfileFileUpload.DoesNotExist as jfe:
        #         job_profile_file_upload_obj = JobProfileFileUpload.objects.create(user=user, resume_src=unregistered_user_file_upload_obj.resume_src)
        #
        #     unregistered_user_file_upload_obj.delete()
        # except UnregisteredUserFileUpload.DoesNotExist as ufde:
        #     pass

        return user


class TempICFRegisterSerializer(serializers.Serializer):

    email = serializers.EmailField(required=allauth_settings.EMAIL_REQUIRED)
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    nationality = serializers.CharField(write_only=True)

    # The verified mobile number
    mobile = serializers.RegexField(regex=r'^\+?1?\d{9,15}$')

    # Mobile phone verified time
    time = serializers.DateTimeField(required=False)
    email_verified_time = serializers.DateTimeField(required=False)

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        if allauth_settings.UNIQUE_EMAIL:
            if email and email_address_exists(email):
                raise serializers.ValidationError(
                    _("A user is already registered with this e-mail address."))
        return email

    def validate_password1(self, password):
        return get_adapter().clean_password(password)

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError(_("The two password fields didn't match. Try again"))
        return data

    def custom_signup(self, request, user):
        pass

    def get_cleaned_data(self):
        return {
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
            'email_verified_time': self.validated_data.get('email_verified_time', ''),
            'mobile': self.validated_data.get('mobile', ''),
            'mobile_verified_time': self.validated_data.get('time', ''),
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
            'nationality': self.validated_data.get('nationality', ''),
        }

    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()

        # Check if the verified phone number is sent along with the request
        mobile = self.cleaned_data.get('mobile')
        mobile_verified_time = self.cleaned_data.get('mobile_verified_time')
        email = self.cleaned_data.get('email')
        email_verified_time = self.cleaned_data.get('email_verified_time')

        # Look for the object in DB
        try:
            db_obj = RegistrationOTP.objects.get(mobile=mobile, updated=mobile_verified_time,
                                                 status=RegistrationOTP.REG_OTP_VERIFIED)
            email_obj = RegistrationEmailOTP.objects.get(email=email, mobile=mobile, updated=email_verified_time,
                                                 status=RegistrationOTP.REG_OTP_VERIFIED)
        except RegistrationOTP.DoesNotExist as e:
            logger.exception(e)
            raise serializers.ValidationError({'mobile': _('Verify your phone number to continue registration')})
        except RegistrationEmailOTP.DoesNotExist as e:
            logger.exception(e)
            raise serializers.ValidationError({'email': _('Verify your email to continue registration')})

        adapter.save_user(request, user, self)
        self.custom_signup(request, user)
        setup_user_email(request, user, [])
        # try:
        #     # check if there any  entry for the current mobile no with resume file in
        #     # UnregisteredUserFileUpload table (if any unregistered user  uploaded resume with this mobile no)
        #     unregistered_user_file_upload_obj = UnregisteredUserFileUpload.objects.get(mobile=self.validated_data.get('mobile'))
        #     try:
        #         job_profile_file_upload_obj = JobProfileFileUpload.objects.get(user=user)
        #         job_profile_file_upload_obj.resume_src = unregistered_user_file_upload_obj.resume_src
        #         job_profile_file_upload_obj.save(update_fields=["resume_src", ])
        #
        #     except JobProfileFileUpload.DoesNotExist as jfe:
        #         job_profile_file_upload_obj = JobProfileFileUpload.objects.create(user=user, resume_src=unregistered_user_file_upload_obj.resume_src)
        #
        #     unregistered_user_file_upload_obj.delete()
        # except UnregisteredUserFileUpload.DoesNotExist as ufde:
        #     pass

        return user


class NewICFRegisterSerializer(serializers.Serializer):

    email = serializers.EmailField(required=allauth_settings.EMAIL_REQUIRED)
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    nationality = serializers.IntegerField(write_only=True)

    # The verified mobile number
    mobile = serializers.RegexField(regex=r'^\+?1?\d{9,15}$')

    # Mobile phone verified time
    time = serializers.DateTimeField(required=False)

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        if allauth_settings.UNIQUE_EMAIL:
            if email and email_address_exists(email):
                raise serializers.ValidationError(
                    _("A user is already registered with this e-mail address."))
        return email

    def validate_password1(self, password):
        return get_adapter().clean_password(password)

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError(_("The two password fields didn't match. Try again"))
        return data

    def custom_signup(self, request, user):
        pass

    def get_cleaned_data(self):
        return {
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
            # 'email_verified_time': self.validated_data.get('email_verified_time', ''),
            'mobile': self.validated_data.get('mobile', ''),
            'mobile_verified_time': self.validated_data.get('time', ''),
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
            'nationality': self.validated_data.get('nationality', ''),
        }

    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()

        # Check if the verified phone number is sent along with the request
        mobile = self.cleaned_data.get('mobile')
        mobile_verified_time = self.cleaned_data.get('mobile_verified_time')
        email = self.cleaned_data.get('email')
        # email_verified_time = self.cleaned_data.get('email_verified_time')

        # Look for the object in DB
        try:
            # test if mobile is verified.
            db_obj = RegistrationOTP.objects.get(mobile=mobile, updated=mobile_verified_time,
                                                 status=RegistrationOTP.REG_OTP_VERIFIED)
            # email_obj = RegistrationEmailOTP.objects.get(email=email, mobile=mobile, updated=email_verified_time,
            #                                      status=RegistrationOTP.REG_OTP_VERIFIED)
        except RegistrationOTP.DoesNotExist as e:
            logger.exception(e)
            raise serializers.ValidationError({'mobile': _('Verify your phone number to continue registration')})
        # except RegistrationEmailOTP.DoesNotExist as e:
        #     logger.exception(e)
        #     raise serializers.ValidationError({'email': _('Verify your email to continue registration')})

        adapter.save_user_info(request, user, self)
        self.custom_signup(request, user)
        nationality = self.cleaned_data.get('nationality', None)
        try:
            user_profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist as ue:
            user_profile = UserProfile.objects.create(user=user)
        if nationality:
            country = Country.objects.get(id=nationality)
            user_profile.nationality = country
            user_profile.save(update_fields=['nationality'])
        setup_user_email(request, user, [])
        # send email to user email with token
        data = {
            "email": user.email,
            "mobile": request.data.get('mobile')
        }
        serializer = EmailOTPSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        # serializer.email = serializer.validated_data['email']
        # serializer.mobile = serializer.validated_data['mobile']
        # obj = serializer.save()
        otp_sender = serializer.get_otp_manager()

        icf_email_otp_message = app_settings.ICF_EMAIL_OTP_MESSAGE.format(to_email=email)
        email_otp_response = otp_sender.generate_email_otp(email, message=icf_email_otp_message)
        if email_otp_response:
            obj, created = RegistrationEmailOTP.objects.update_or_create(email=email, mobile=mobile,
                                                                         defaults={'key': otp_sender.get_key(),
                                                                                   'status': RegistrationEmailOTP.REG_OTP_SENT
                                                                                   }
                                                                         )
        adapter.send_confirmation_mail_with_otp(request, email_otp_response.get('message'), user, signup=True)


        # try:
        #     # check if there any  entry for the current mobile no with resume file in
        #     # UnregisteredUserFileUpload table (if any unregistered user  uploaded resume with this mobile no)
        #     unregistered_user_file_upload_obj = UnregisteredUserFileUpload.objects.get(mobile=self.validated_data.get('mobile'))
        #     try:
        #         job_profile_file_upload_obj = JobProfileFileUpload.objects.get(user=user)
        #         job_profile_file_upload_obj.resume_src = unregistered_user_file_upload_obj.resume_src
        #         job_profile_file_upload_obj.save(update_fields=["resume_src", ])
        #
        #     except JobProfileFileUpload.DoesNotExist as jfe:
        #         job_profile_file_upload_obj = JobProfileFileUpload.objects.create(user=user, resume_src=unregistered_user_file_upload_obj.resume_src)
        #
        #     unregistered_user_file_upload_obj.delete()
        # except UnregisteredUserFileUpload.DoesNotExist as ufde:
        #     pass

        return user



# class ICFLoginTokenSerializer(TokenSerializer):
#     user_profile = serializers.SerializerMethodField(read_only=True)
#
#     class Meta:
#         model = TokenModel
#         fields = ('key', 'user_profile',)
#
#     def get_user_profile(self, obj):
#         try:
#             return UserProfileRetrieveSerializer(UserProfile.objects.get(user=obj.user)).data
#         except UserProfile.DoesNotExist:
#             logger.debug("User profile does not exist for {}".format(obj.user.email))
#             return None


class ICFLoginTokenSerializer(TokenSerializer):
    user_profile = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AuthToken
        fields = ('token_key', 'user_profile',)

    def get_user_profile(self, obj):
        try:
            return UserProfileRetrieveSerializer(UserProfile.objects.get(user=obj.user)).data
        except UserProfile.DoesNotExist:
            logger.exception("User profile does not exist for {}".format(obj.user.email))
            return None


class ICFLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, allow_blank=False)
    password = serializers.CharField(style={'input_type': 'password'})

    def _validate_email(self, email, password):
        user = None
        print(email, password)

        if email and password:
            user = authenticate(email=email, password=password)
        else:
            logger.exception("Email and password are required to login")
            raise exceptions.ValidationError(_("Email and password are required to login"))

        return user

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        user = None

        # Authentication through email
        user = self._validate_email(email, password)

        # Did we get back an active user?
        if user:
            if not user.is_active:
                msg = _('Your account is disabled.')
                logger.exception(msg)
                raise exceptions.ValidationError(msg)
        else:
            msg = _('Your email or password is not correct.')
            logger.exception(msg)
            raise exceptions.ValidationError(msg)

        # If required, is the email verified?
        if 'rest_auth.registration' in settings.INSTALLED_APPS:
            from allauth.account import app_settings
            if app_settings.EMAIL_VERIFICATION == app_settings.EmailVerificationMethod.MANDATORY:
                email_address = user.emailaddress_set.get(email=user.email)
                if not email_address.verified:
                    raise serializers.ValidationError(_('Your email is not verified.'))

        attrs['user'] = user
        return attrs


class ICFPasswordResetSerializer(PasswordResetSerializer):
    """
    Serializer for requesting a password reset e-mail.
    """
    def get_email_options(self):
        """Override this method to change default e-mail options"""
        return {'subject_template_name': 'account/email/password_reset_subject.txt',
                'email_template_name': 'account/email/password_reset_email.html',
                'extra_email_context': None,
        }


class ICFEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, allow_blank=False)

    def validate_email(self, email):
        return email

    def validate(self, attrs):
        email = attrs.get('email')

        attrs['email'] = email
        return attrs


class MobileOTPSerializer(serializers.Serializer):
    mobile = serializers.RegexField(regex=r'^\+?1?\d{9,15}$')
    key = serializers.CharField(required=False, max_length=16)
    time = serializers.DateTimeField(required=False)
    status = serializers.IntegerField(required=False)
    otp = serializers.RegexField(regex=r'^\d{4,6}$', required=False)

    def validate_otp(self, otp):
        print("OTP received: {0}".format(otp))
        return otp

    def validate_mobile(self, mobile):
        return mobile

    def validate(self, attrs):
        return attrs

    def get_otp_manager(self, **kwargs):
        return IcfOTPManager(**kwargs)

    def save(self):
        otp_sender = self.get_otp_manager()

        self.otp = otp_sender.send_otp(self.mobile, message=settings.ICF_OTP_MESSAGE)
        if self.otp:
            obj, created = RegistrationOTP.objects.update_or_create(mobile=self.mobile,
                                                                    defaults={'key': otp_sender.get_key(),
                                                                              'status': RegistrationOTP.REG_OTP_SENT
                                                                              }
                                                                    )
            return obj
        else:
            return None

    def verify(self):

        # Received from user
        self.mobile = self.validated_data.get('mobile')
        self.time = self.validated_data.get('time')
        self.key = self.validated_data.get('key')
        self.otp = self.validated_data.get('otp')

        # Look for the object in DB
        try:
            db_obj = RegistrationOTP.objects.get(mobile=self.mobile, key=self.key, updated=self.time,
                                                 status=RegistrationOTP.REG_OTP_SENT)
        except ObjectDoesNotExist:
            logger.error("OTP record not found in the DB")
            return False

        # Changed for Mahendra

        try:
            if settings.ICF_SEND_OTP_DISABLED:
                db_obj.status = RegistrationOTP.REG_OTP_VERIFIED
                db_obj.save()
                self.time = db_obj.updated
                return True
        except AttributeError:
            pass

        otp_verifier = self.get_otp_manager(key=db_obj.key)

        # Verify the OTP
        if otp_verifier.verify_top(self.otp, valid_window=30):
            db_obj.status = RegistrationOTP.REG_OTP_VERIFIED
            db_obj.save()
            self.time = db_obj.updated
            return True

        return False


class EmailOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    mobile = serializers.RegexField(regex=r'^\+?1?\d{9,15}$')
    key = serializers.CharField(required=False, max_length=16)
    time = serializers.DateTimeField(required=False)
    status = serializers.IntegerField(required=False)
    otp = serializers.RegexField(regex=r'^\d{4,6}$', required=False)

    def validate_otp(self, otp):
        print("OTP received: {0}".format(otp))
        return otp

    def validate_email(self, email):
        return email

    def validate(self, attrs):
        return attrs

    def get_otp_manager(self, **kwargs):
        return IcfEmailOTPManager(**kwargs)

    def save(self):
        otp_sender = self.get_otp_manager()

        # self.otp = otp_sender.send_email_otp(self.email, message=settings.ICF_OTP_MESSAGE)
        self.otp = otp_sender.generate_email_otp(self.email, message=settings.ICF_OTP_MESSAGE)
        if self.otp:
            obj, created = RegistrationEmailOTP.objects.update_or_create(email=self.email, mobile=self.mobile,
                                                                    defaults={'key': otp_sender.get_key(),
                                                                              'status': RegistrationOTP.REG_OTP_SENT
                                                                              }
                                                                    )
            return obj
        else:
            return None

    def verify(self):

        # Received from user
        self.email = self.validated_data.get('email')
        self.mobile = self.validated_data.get('mobile')
        self.time = self.validated_data.get('time')
        self.key = self.validated_data.get('key')
        self.otp = self.validated_data.get('otp')

        # Look for the object in DB
        try:
            db_obj = RegistrationEmailOTP.objects.get(email=self.email, mobile=self.mobile, key=self.key, updated=self.time,
                                                 status=RegistrationOTP.REG_OTP_SENT)
        except ObjectDoesNotExist:
            logger.error("OTP record not found in the DB")
            return False


        # Changed for Mahendra

        try:
            if settings.ICF_SEND_OTP_DISABLED:
                db_obj.status = RegistrationOTP.REG_OTP_VERIFIED
                db_obj.save()
                self.time = db_obj.updated
                return True
        except AttributeError:
            pass

        otp_verifier = self.get_otp_manager(key=db_obj.key)

        # Verify the OTP
        if otp_verifier.verify_top(self.otp, valid_window=30):
            db_obj.status = RegistrationEmailOTP.REG_OTP_VERIFIED
            db_obj.save()
            self.time = db_obj.updated
            return True

        return False


class ResendEmailOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    mobile = serializers.RegexField(regex=r'^\+?1?\d{9,15}$')
    # key = serializers.CharField(required=False, max_length=16)
    # time = serializers.DateTimeField(required=False)
    # status = serializers.IntegerField(required=False)
    # otp = serializers.RegexField(regex=r'^\d{4,6}$', required=False)

    def validate_otp(self, otp):
        print("OTP received: {0}".format(otp))
        return otp

    def validate_email(self, email):
        return email

    def validate(self, attrs):
        return attrs

    def get_otp_manager(self, **kwargs):
        return IcfEmailOTPManager(**kwargs)

    def save(self):
        otp_sender = self.get_otp_manager()

        icf_email_otp_message = app_settings.ICF_EMAIL_OTP_MESSAGE.format(to_email=self.email)
        email_otp_response = otp_sender.generate_email_otp(self.email, message=icf_email_otp_message)
        if email_otp_response:
            obj, created = RegistrationEmailOTP.objects.update_or_create(email=self.email, mobile=self.mobile,
                                                                         defaults={'key': otp_sender.get_key(),
                                                                                   'status': RegistrationEmailOTP.REG_OTP_SENT
                                                                                   }
                                                                         )
            response_dict = {
                "obj": obj,
                "email_otp_response": email_otp_response
            }
            return response_dict
        else:
            logger.error("Could not generate OTP.")
            return None

    def verify(self):

        # Received from user
        self.email = self.validated_data.get('email')
        self.mobile = self.validated_data.get('mobile')
        self.time = self.validated_data.get('time')
        self.key = self.validated_data.get('key')
        self.otp = self.validated_data.get('otp')

        # Look for the object in DB
        try:
            db_obj = RegistrationEmailOTP.objects.get(email=self.email, mobile=self.mobile, key=self.key,
                                                      updated=self.time,
                                                      status=RegistrationOTP.REG_OTP_SENT)
        except ObjectDoesNotExist:
            logger.error("OTP record not found in the DB")
            return False

        # Changed for Mahendra

        try:
            if settings.ICF_SEND_OTP_DISABLED:
                db_obj.status = RegistrationOTP.REG_OTP_VERIFIED
                db_obj.save()
                self.time = db_obj.updated
                return True
        except AttributeError:
            pass

        otp_verifier = self.get_otp_manager(key=db_obj.key)

        # Verify the OTP
        if otp_verifier.verify_top(self.otp, valid_window=30):
            db_obj.status = RegistrationEmailOTP.REG_OTP_VERIFIED
            db_obj.save()
            self.time = db_obj.updated
            return True

        return False


class UserSerializer(ModelSerializer):

    class Meta:
        model = User
        fields = ['username', ]


class UserFirstAndLastNameSerializer(ModelSerializer):
    username = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ['username', ]

    def get_username(self, obj):
        # username = ''
        # if obj.first_name:
        #     username = username.join(obj.first_name)
        # if obj.last_name:
        #     username = username.join(" ").join(obj.last_name)
        return obj.first_name


class PasswordSerializer(ModelSerializer):

    class Meta:
        model = User
        fields = ['password', ]


class UserProfileCreateSerializer(ModelSerializer):
    # user = UserSerializer()
    # location = AddressSerializer()
    # language = LanguageSerializer()

    class Meta:
        model = UserProfile
        fields = [

            "dob",
            "gender",
            "biography",
            "location",
            "language",
            "nationality",

        ]

    def create(self, validated_data):
        user_id = self.context['request'].user.pk
        user_profile = UserProfile.objects.create(user_id=user_id,**validated_data)
        return user_profile


class UserEmailMobileSerializer(ModelSerializer):
    cart_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["email", "mobile", "first_name", "last_name", "cart_count"]

    def get_cart_count(self, obj):
        return Cart.objects.filter(user=obj).count()


class UserProfileImageSerializer(ModelSerializer):

    class Meta:
        model = UserProfileImage
        fields = ['image', 'id']

    def get_image_url(self, obj):
        return obj.image.url

    def create(self, validated_data):
        user = self.context['user']
        try:
            profile = UserProfile.objects.get(user=user)
            obj = UserProfileImage.objects.get(user_profile = profile)
            obj.image = validated_data.get('image')
            obj.save()

        except ObjectDoesNotExist:

            profile = UserProfile.objects.get(user=user)
            obj, created = UserProfileImage.objects.get_or_create(user_profile=profile, **validated_data)

        return obj

    def update(self, instance, validated_data):
        image = validated_data.get('image')
        instance.image = image
        instance.save()
        return instance


class ICFLoginResponseSerializer(ModelSerializer):
    user_profile = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ["email", "mobile", "first_name", "last_name", "is_superuser", "user_profile"]

    def get_user_profile(self, obj):
        try:
            user_profile = UserProfile.objects.get(user=obj)
            return UserProfileRetrieveSerializer(user_profile).data
        except UserProfile.DoesNotExist:
            logger.exception("User profile does not exist for {}".format(obj.email))
            return None


class UserProfileRetrieveSerializer(ModelSerializer):
    user = UserEmailMobileSerializer()

    class Meta:
        model = UserProfile
        fields = "__all__"

    # def get_email(self, obj):
    #     return obj.user.email
    #
    # def get_mobile(selfs, obj):
    # #     return obj.user.mobile
    #
    # def update(self, instance, validated_data):
    #
    #     user = validated_data.pop('user')
    #


class UserProfileRetrieveUpdateSerializer(ModelSerializer):
    user = UserEmailMobileSerializer()
    profile_image = serializers.SerializerMethodField(read_only=True)
    location = AddressSerializer()
    profile_image_id = serializers.SerializerMethodField()
    slug = serializers.SerializerMethodField()
    is_superuser = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = "__all__"

    # def create(self, validated_data):
    #     logger.info(validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user")

        instance.user.first_name = user_data.get('first_name')
        instance.user.last_name = user_data.get('last_name')
        instance.user.save()

        location_data = validated_data.pop('location')
        if instance.location:
            instance.location.address_1 = location_data.get('address_1')
            instance.location.address_2 = location_data.get('address_2')
            instance.location.city = location_data.get('city')
            instance.location.save()
        else:
            location, address_created = Address.objects.update_or_create(userprofile=instance, **location_data)
            instance.location = location

        info = model_meta.get_field_info(instance)

        # Simply set each attribute on the instance, and then save it.
        # Note that unlike `.create()` we don't need to treat many-to-many
        # relationships as being a special case. During updates we already
        # have an instance pk for the relationships to be associated with.
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            else:
                setattr(instance, attr, value)

        instance.status = UserProfile.UPDATED
        instance.save()

        return instance

    def get_profile_image(self, obj):
        try:
            return obj.userprofileimage.image.url
        except ObjectDoesNotExist:
            return None

    def get_profile_image_id(self, obj):
        try:
            return obj.userprofileimage.id
        except ObjectDoesNotExist:
            return None

    def get_slug(self, obj):
        return obj.user.slug

    def get_is_superuser(self, obj):
        return obj.user.is_superuser


class UserProfileRetrieveSerializerForList(ModelSerializer):
    user = UserEmailMobileSerializer()
    profile_image = serializers.SerializerMethodField(read_only=True)
    location = AddressRetrieveSerializer()
    language = serializers.StringRelatedField()
    nationality = serializers.StringRelatedField()

    class Meta:
        model = UserProfile
        fields = "__all__"

    def get_profile_image(self, obj):
        try:
            user_profile_image_obj = UserProfileImage.objects.get(user_profile=obj)
            return user_profile_image_obj.image.url
        except UserProfileImage.DoesNotExist as e:
            # logger.info("Profile Image not found for {}".format(obj.user))
            return None


class UserEmailSerializer(ModelSerializer):

    class Meta:
        model = User
        fields = ['display_name', 'email', ]


class CheckIfExistingEmailUserSerializer(Serializer):
    email = serializers.EmailField()
