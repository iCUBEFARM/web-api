import pytz
import requests
from django.contrib import messages
from allauth.account import app_settings as allauth_settings
from allauth.account.utils import complete_signup
from datetime import datetime

from allauth.account.adapter import get_adapter
from allauth.account.models import EmailConfirmation, EmailConfirmationHMAC, EmailAddress
from allauth.account.utils import send_email_confirmation
from allauth.account.views import ConfirmEmailView
from django.contrib.auth import get_user_model, login, user_logged_in
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.http.response import Http404
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from knox.models import AuthToken
from knox.views import LoginView as KnoxLoginView
from icf import settings

# Create your views here.
from rest_auth.registration.views import VerifyEmailView, sensitive_post_parameters_m
from rest_auth.serializers import TokenSerializer, PasswordResetConfirmSerializer, PasswordResetSerializer
from rest_framework import status, viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication, BasicAuthentication
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.decorators import api_view
from rest_framework.generics import RetrieveUpdateAPIView, CreateAPIView, RetrieveAPIView, GenericAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from icf_auth import adapter
from icf_auth.adapter import ICFAccountAdapter
from icf_auth.api.serializers import ICFEmailSerializer, \
    MobileOTPSerializer, UserProfileRetrieveUpdateSerializer, UserProfileCreateSerializer, \
    UserProfileRetrieveSerializer, UserProfileImageSerializer, UserSerializer, PasswordSerializer, ICFLoginSerializer, \
    ICFLoginResponseSerializer, ICFRegisterSerializer, ICFPasswordResetSerializer, EmailOTPSerializer, \
    NewICFRegisterSerializer, ResendEmailOTPSerializer

# class ICFRegisterView(RegisterView):
#     serializer_class = ICFRegisterSerializer
from icf_auth.models import UserProfile, UserProfileImage, User, UserBrowserInfo, RegistrationEmailOTP

import logging

from icf_auth.util import send_email_verification_confirmation, verified_email_address_exists
from icf_generic.Exceptions import ICFException
from icf_generic.models import Language
from icf_integrations.newsletter import ICFNewsletterManager
from icf_jobs.api.serializers import CheckIfExistingUserSerializer
from icf_auth.api.serializers import CheckIfExistingEmailUserSerializer
from icf_jobs.models import UnregisteredUserFileUpload, JobProfileFileUpload
from drf_yasg.utils import swagger_auto_schema

logger = logging.getLogger(__name__)


@api_view()
def django_rest_auth_null(request, *args, **kwargs):
    return Response(status=status.HTTP_400_BAD_REQUEST)


class SendMobileOTP(APIView):

    def get_serializer(self, *args, **kwargs):
        return MobileOTPSerializer(*args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Send OTP!!!!!!!!!!"
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.mobile = serializer.validated_data['mobile']
        obj = serializer.save()
        if obj:
            return Response({
                'details': _('We sent you an SMS verification code, use the code to continue registration.'),
                'mobile': obj.mobile,
                'updated': obj.updated,
         #       'otp': serializer.otp,
                'key': obj.key
            }, status=status.HTTP_200_OK)
        else:
            logger.info("Could not send OTP to {}".format(serializer.mobile))
            return Response({'detail': _('Unable to send SMS Verification Code, please try again later')}, status=status.HTTP_400_BAD_REQUEST)


class VerifyMobileOTP(APIView):
    allowed_methods = ('POST', 'OPTIONS', 'HEAD')

    def get_serializer(self, *args, **kwargs):
        return MobileOTPSerializer(*args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Verity OTP!!!!!!!!!!"
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.verify():
            return Response ({
                'details': _('We have successfully verified your mobile number'),
                'mobile': serializer.mobile,
                'time': serializer.time,
                'key': serializer.key
            }, status=status.HTTP_200_OK)
        else:
            logger.info("Verification of Mobile number failed for {}".format(serializer.mobile))

            return Response ({
                'detail': _('Unable to verify your mobile number'),
            }, status=status.HTTP_400_BAD_REQUEST)


class SendEmailOTP(APIView):

    def get_serializer(self, *args, **kwargs):
        return EmailOTPSerializer(*args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Send Email OTP!!!!!!!!!!"
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.email = serializer.validated_data['email']
        serializer.mobile = serializer.validated_data['mobile']
        obj = serializer.save()
        if obj:
            return Response({
                'details': _('We sent you an email verification code, use the code to continue registration.'),
                'email': obj.email,
                'mobile': obj.mobile,
                'updated': obj.updated,
         #       'otp': serializer.otp,
                'key': obj.key
            }, status=status.HTTP_200_OK)
        else:
            logger.info("Could not send OTP to {}".format(serializer.email))
            return Response({'detail': _('Unable to send email Verification Code, please try again later')}, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailOTP(APIView):
    allowed_methods = ('POST', 'OPTIONS', 'HEAD')

    def get_serializer(self, *args, **kwargs):
        return EmailOTPSerializer(*args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Email OTP verification"
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.verify():
            try:
                email_address = EmailAddress.objects.get(email__iexact=serializer.email)
                email_address.verified = True
                email_address.save(update_fields=['verified'])
                user = User.objects.get(email=serializer.email)
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')

                token = AuthToken.objects.create(user)

                user_logged_in.send(sender=user.__class__, request=request, user=user)

                send_email_verification_confirmation(user.email)

                try:
                    user = User.objects.get(email=email_address.email)
                    # subscribe user to newsletter
                    email = user.email

                    try:
                        language_code = request.LANGUAGE_CODE
                        icf_news_letter_manager = ICFNewsletterManager()
                        icf_news_letter_manager.get_newsletter_service(email,
                                                                       language_code, user)  # Subscribe to Newsletter
                        # Users_List
                    except Language.DoesNotExist as lne:
                        logger.exception(
                            "Language code Not Exist cannot add the user with email {email} to the Newsletter\n".format(
                                email=email))
                        pass
                except User.DoesNotExist as udne:
                    logger.exception(str(udne))
                    raise ICFException(_("User does not exist with this email address"),
                                       status_code=status.HTTP_400_BAD_REQUEST)

                return Response({
                    'user': ICFLoginResponseSerializer(request.user).data,
                    'key': token,
                }, status=status.HTTP_200_OK)
            except EmailAddress.DoesNotExist as e:
                logger.exception("EmailAddress object not found.")
                raise ICFException(_("Email verification failed. Please contact admin."),
                                   status_code=status.HTTP_200_OK)
            except User.DoesNotExist as ue:
                logger.exception("User object not found.")
                raise ICFException(_("Email verification failed. Please contact admin."),
                                   status_code=status.HTTP_200_OK)
            except Exception as e:
                logger.exception("Something went wrong. reason:{reason}".format(reason=str(e)))
                raise ICFException(_("Email verification failed. Please contact admin."),
                                   status_code=status.HTTP_200_OK)
            # return Response({
            #     'details': _('We have successfully verified your email.'),
            #     'email': serializer.email,
            #     'mobile': serializer.mobile,
            #     'time': serializer.time,
            #     'key': serializer.key
            # }, status=status.HTTP_200_OK)
        else:
            logger.info("Verification of email failed for {}".format(serializer.email))

            return Response ({
                'detail': _('Unable to verify your email.'),
            }, status=status.HTTP_400_BAD_REQUEST)


class ICFVerifyEmailView(ConfirmEmailView):

    def get(self, request, *args, **kwargs):
        # url = request.build_absolute_uri()
        # return Response(requests.post(url, data=kwargs))
        try:
            self.object = self.get_object()
            if allauth_settings.CONFIRM_EMAIL_ON_GET:
                return self.post(request,*args, **kwargs)
        except Http404:
            self.object = None
        ctx = self.get_context_data()
        return self.render_to_response(ctx)

    @swagger_auto_schema(
        operation_summary="Send Email verification"
    )

    def post(self, request, *args, **kwargs):
        # serializer = self.get_serializer(data=request.data)
        # serializer.is_valid(raise_exception=True)
        # self.kwargs['key'] = serializer.validated_data['key']
        confirmation = self.get_object()
        confirmation.confirm(self.request)
        get_adapter(self.request).add_message(
            self.request,
            messages.SUCCESS,
            'account/messages/email_confirmed.txt',
            {'email': confirmation.email_address.email})
        if allauth_settings.LOGIN_ON_EMAIL_CONFIRMATION:
            resp = self.login_on_confirm(confirmation)
            if resp is not None:
                return resp
        # Don't -- allauth doesn't touch is_active so that sys admin can
        # use it to block users et al
        #
        # user = confirmation.email_address.user
        # user.is_active = True
        # user.save()
        logger.info("Sent verification email to  {}".format(confirmation.email_address.email))

        try:
            user = User.objects.get(email=confirmation.email_address.email)
            # subscribe user to newsletter
            email = user.email

            try:
                language_code = request.LANGUAGE_CODE
                icf_news_letter_manager = ICFNewsletterManager()
                icf_news_letter_manager.get_newsletter_service(email,
                                                               language_code, user)  # Subscribe to Newsletter
                # Users_List
            except Language.DoesNotExist as lne:
                logger.exception(
                    "Language code Not Exist cannot add the user with email {email} to the Newsletter\n".format(
                        email=email))
                pass


            # check if there any  entry for the current mobile no with resume file in
            # UnregisteredUserFileUpload table (if any unregistered user  uploaded resume with this mobile no)
            unregistered_user_file_upload_obj = UnregisteredUserFileUpload.objects.get(mobile=user.mobile)
            try:
                job_profile_file_upload_obj = JobProfileFileUpload.objects.get(user=user)
                job_profile_file_upload_obj.resume_src = unregistered_user_file_upload_obj.resume_src
                job_profile_file_upload_obj.save(update_fields=["resume_src", ])

            except JobProfileFileUpload.DoesNotExist as jfe:
                job_profile_file_upload_obj = JobProfileFileUpload.objects.create(user=user, resume_src=unregistered_user_file_upload_obj.resume_src)

            unregistered_user_file_upload_obj.delete()
        except User.DoesNotExist as udne:
            logger.exception(str(udne))
            raise ICFException(_("User does not exist with this email address"), status_code=status.HTTP_400_BAD_REQUEST)
        except UnregisteredUserFileUpload.DoesNotExist as ufde:
            pass

        redirect_url = self.get_redirect_url()
        if not redirect_url:
            ctx = self.get_context_data()
            return self.render_to_response(ctx)
        return redirect(redirect_url)

    @swagger_auto_schema(
        operation_summary="Return email confirmatioin"
    )
    def get_object(self, queryset=None):
        key = self.kwargs['key']
        email_confirmation = EmailConfirmationHMAC.from_key(key)
        if not email_confirmation:
            if queryset is None:
                queryset = self.get_queryset()
            try:
                email_confirmation = queryset.get(key=key.lower())
            except EmailConfirmation.DoesNotExist:
                raise EmailConfirmation.DoesNotExist
        return email_confirmation

    def get_queryset(self):
        qs = EmailConfirmation.objects.all_valid()
        qs = qs.select_related("email_address__user")
        return qs

    def get_redirect_url(self):
        return '/account/verified-email/'


class ICFResendVerificationEmail(APIView):

    def get_serializer(self, *args, **kwargs):
        return ICFEmailSerializer(*args, **kwargs)

    @swagger_auto_schema(
        operation_summary="RE-Send Email verification"
    )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        self.kwargs['email'] = email
        User = get_user_model()
        user = User.objects.get(email__iexact=email)

        send_email_confirmation(request, user)
        return Response({'detail': _('Your verification email has been resent')}, status=status.HTTP_200_OK)



# class ICFLoginView(LoginView):
#     serializer_class = ICFLoginSerializer


class CheckPassword(CreateAPIView):
    permission_classes = (IsAuthenticated, )

    def get_serializer(self, *args, **kwargs):
        return PasswordSerializer(*args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Check Password"
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['password']

        return Response(request.user.check_password(password))


class ExampleView(APIView):
    authentication_classes = (SessionAuthentication, TokenAuthentication)
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        content = {
            'user': request.user.username,  # `django.contrib.auth.User` instance.
            'auth': "{}".format(request.auth),  # None
        }
        # print("Congrats, you are authenticated")
        return Response(content)


class UserProfileAPIView(RetrieveUpdateAPIView):
    # parser_classes = (MultiPartParser, FormParser)
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileRetrieveUpdateSerializer
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_summary="User profile view"
    )
    def get_object(self):
        user = self.request.user
        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            logger.info("Creating profile for user {}".format(user.email))
            profile = UserProfile.objects.create(user=user)
        return profile

    @swagger_auto_schema(
        operation_summary="User profile Details"
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Update User profile"
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        email = instance.user.email
        preferred_language = int(request.data.get('language'))
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # code to register user email to newsletter done on user email verification
        # try:
        #     language = Language.objects.get(id=preferred_language)
        #     preferred_language_code = language.code
        #     icf_news_letter_manager = ICFNewsletterManager()
        #     icf_news_letter_manager.get_newsletter_service(email, preferred_language_code)  # Subscribe to Newsletter
        #     # Users_List
        # except Language.DoesNotExist as lne:
        #     logger.exception("Language code Not Exist cannot add the user with email {email} to the Newsletter\n".format(email=email))
        #     return Response({"detail": _("Language code not exist, cannot add the "
        #                                  "user with email {email} to the Newsletter")},
        #                     status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserProfileCreateAPIView(CreateAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileCreateSerializer

    permission_classes = (IsAuthenticated,)


class UserProfileDetailAPIView(RetrieveAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileRetrieveSerializer
    permission_classes = (IsAuthenticated, )

    lookup_field = "slug"


class UserProfileImageViewSet(viewsets.ModelViewSet):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = UserProfileImageSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserProfileImage.objects.all()

    def get_queryset(self):
        return UserProfileImage.objects.filter(user_profile__user=self.request.user)

    def get_serializer(self, *args, **kwargs):
        return UserProfileImageSerializer(*args, **kwargs)

    def get_object(self, queryset=None):
        instance = UserProfileImage.objects.filter(user_profile__user=self.request.user).first()
        return instance

    def create(self, request, *args, user=None, **kwargs):
        context = {'user': self.request.user}
        serializer = UserProfileImageSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
            logger.info("Profile image uploaded for user {}".format(request.user))

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist as e:
            logger.exception("Could not add profile image for user {}".format(request.user.email))

            return Response({"detail": _("Your profile image failed to upload, please try again")}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk = None,*args,**kwargs):
        obj = UserProfileImage.objects.filter(user_profile__user=self.request.user)
        serializer = self.get_serializer(obj, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, pk=None,*args,**kwargs):
        context = {'user': self.request.user}
        try:
            instance = UserProfileImage.objects.get(user_profile__user=self.request.user)
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            logger.exception("Could not update profile image for user {}".format(request.user))

            return Response({"detail": _("Your profile image failed to upload, please try again")}, status=status.HTTP_400_BAD_REQUEST)


class ICFLoginView(KnoxLoginView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Process User loging and return token"
    )
    def post(self, request, format=None):
        serializer = ICFLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        print('-------', request.method)
        login(request, user)

        token = AuthToken.objects.create(request.user)
        user_logged_in.send(sender=request.user.__class__, request=request, user=request.user)
        return Response({
            'user': ICFLoginResponseSerializer(request.user).data,
            'key': token,
        }, status=status.HTTP_200_OK)


class ICFRegisterView(CreateAPIView):
    serializer_class = ICFRegisterSerializer
    permission_classes = [AllowAny, ]
#    token_model = AuthToken

    def dispatch(self, *args, **kwargs):
        return super(ICFRegisterView, self).dispatch(*args, **kwargs)

    def get_response_data(self, user):
        email_status = allauth_settings.EMAIL_VERIFICATION
        if allauth_settings.EMAIL_VERIFICATION == allauth_settings.EmailVerificationMethod.MANDATORY:
            return {"detail": _("A verification email has been sent consult your email account.")}

        return {"detail": _("Congratulations! Your registration was completed successfully")}

    @swagger_auto_schema(
        operation_summary="Process User sign up"
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(self.get_response_data(user),
                        status=status.HTTP_201_CREATED,
                        headers=headers)

    def perform_create(self, serializer):
        user = serializer.save(self.request)

#        icf_create_token(self.token_model, user, serializer)

        complete_signup(self.request._request, user, allauth_settings.EMAIL_VERIFICATION, None)
        return user


class TempICFRegisterView(CreateAPIView):
    serializer_class = NewICFRegisterSerializer
    permission_classes = [AllowAny, ]
#    token_model = AuthToken

    def dispatch(self, *args, **kwargs):
        return super(TempICFRegisterView, self).dispatch(*args, **kwargs)

    def get_response_data(self, user):
        email_status = allauth_settings.EMAIL_VERIFICATION
        if allauth_settings.EMAIL_VERIFICATION == allauth_settings.EmailVerificationMethod.MANDATORY:
            return {"detail": _("A verification email has been sent consult your email account.")}

        return {"detail": _("Congratulations! Your registration was completed successfully")}

    @swagger_auto_schema(
        operation_summary="New user reg",
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(self.get_response_data(user),
                        status=status.HTTP_201_CREATED,
                        headers=headers)

    def perform_create(self, serializer):
        user = serializer.save(self.request)

#        icf_create_token(self.token_model, user, serializer)

        complete_signup(self.request._request, user, allauth_settings.EMAIL_VERIFICATION, None)
        return user


class NewICFRegisterView(CreateAPIView):
    serializer_class = NewICFRegisterSerializer
    permission_classes = [AllowAny, ]
#    token_model = AuthToken

    def dispatch(self, *args, **kwargs):
        return super(NewICFRegisterView, self).dispatch(*args, **kwargs)

    def get_response_data(self, user):
        email_status = allauth_settings.EMAIL_VERIFICATION
        if allauth_settings.EMAIL_VERIFICATION == allauth_settings.EmailVerificationMethod.MANDATORY:
            if user:
                registration_email_otp = RegistrationEmailOTP.objects.filter(email=user.email, mobile=user.mobile).latest('created')
                return {
                    'details': _('A verification email has been sent consult your email account.'),
                    'email': registration_email_otp.email,
                    'mobile': registration_email_otp.mobile,
                    'updated': registration_email_otp.updated,
                    'key': registration_email_otp.key
                }

        return {"detail": _("Congratulations! Your registration was completed successfully")}

    @swagger_auto_schema(
        operation_summary="Process initial User registration "
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(self.get_response_data(user),
                        status=status.HTTP_201_CREATED,
                        headers=headers)

    def perform_create(self, serializer):
        user = serializer.save(self.request)

#        icf_create_token(self.token_model, user, serializer)

        # complete_signup(self.request._request, user, allauth_settings.EMAIL_VERIFICATION, None)
        return user


class ResendEmailOTPView(APIView):
    def get_serializer(self, *args, **kwargs):
        return ResendEmailOTPSerializer(*args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Send Email OTP",
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.email = serializer.validated_data['email']
        serializer.mobile = serializer.validated_data['mobile']
        response_dict = serializer.save()
        if response_dict:
            email = response_dict.get("obj").email
            user = User.objects.get(email__iexact=email)
            adapter = ICFAccountAdapter()
            adapter.send_confirmation_mail_with_otp(request, response_dict.get("email_otp_response").get('message'), user, signup=True)

            return Response({
                'details': _('We sent you an email verification code, use the code to continue registration.'),
                'email': response_dict.get("obj").email,
                'mobile': response_dict.get("obj").mobile,
                'updated': response_dict.get("obj").updated,
                #       'otp': serializer.otp,
                'key': response_dict.get("obj").key
            }, status=status.HTTP_200_OK)
        else:
            logger.info("Could not send OTP to {}".format(serializer.email))
            return Response({'detail': _('Unable to send email Verification Code, please try again later')},
                            status=status.HTTP_400_BAD_REQUEST)


class CheckForExistingUserView(GenericAPIView):
    serializer_class = ICFLoginSerializer

    @swagger_auto_schema(
        operation_summary="Check for existing uaer",
    )
    def post(self, request, *args, **kwargs):
        try:
            user = User.objects.get(email=request.data.get('email'))
            user_last_login=user.last_login
            if user_last_login.date() == settings.LAST_LOGIN.date():
                return Response({'old_version_user': True, }, status=status.HTTP_200_OK)
            else:
                print('------', user)
                return Response({'old_version_user': False, }, status=status.HTTP_200_OK)
        except Exception:
            return Response({'old_version_user': False, }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(GenericAPIView):
    """
    Password reset e-mail link is confirmed, therefore
    this resets the user's password.

    Accepts the following POST parameters: token, uid,
        new_password1, new_password2
    Returns the success/fail message.
    """
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = (AllowAny,)

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(PasswordResetConfirmView, self).dispatch(*args, **kwargs)

    @swagger_auto_schema(
        operation_summary="reset user password",
        operation_description="Password reset e-mail link is confirmed, therefore  this resets the user's password."
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.user.email
        try:
            user = User.objects.get(email=email)
            user_last_login = user.last_login
            if user_last_login.date() == settings.LAST_LOGIN.date():
                serializer.user.last_login = datetime.now(pytz.utc)
                serializer.user.save(update_fields=['last_login', ])
        except Exception:
            pass

        serializer.save()

        return Response(
            {"detail": _("Your password has been reset.")}
        )


class PasswordResetView(GenericAPIView):
    """
    Calls Django Auth PasswordResetForm save method.

    Accepts the following POST parameters: email
    Returns the success/fail message.
    """
    serializer_class = ICFPasswordResetSerializer
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_summary="Send password reset email"
    )
    def post(self, request, *args, **kwargs):
        # Create a serializer with request.
        try:
            user = User.objects.get(email=request.data.get('email'))
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            serializer.save()
            # Return the success message with OK HTTP status
            return Response(

                {"detail": _("Password reset e-mail has been sent.")},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response({"detail": _("We could not find this email on the portal. "
                                         "Please check that you entered your email correctly.")},
                            status=status.HTTP_200_OK
            )


def get_browser_info(request):
    if request.method == 'GET':
        # # Let's assume that the visitor uses an iPhone...
        # request.user_agent.is_mobile # returns True
        # request.user_agent.is_tablet # returns False
        # request.user_agent.is_touch_capable # returns True
        # request.user_agent.is_pc # returns False
        # request.user_agent.is_bot # returns False
        #
        # # Accessing user agent's browser attributes
        # request.user_agent.browser  # returns Browser(family=u'Mobile Safari', version=(5, 1), version_string='5.1')
        # request.user_agent.browser.family  # returns 'Mobile Safari'
        # request.user_agent.browser.version  # returns (5, 1)
        # request.user_agent.browser.version_string   # returns '5.1'
        #
        # # Operating System properties
        # request.user_agent.os  # returns OperatingSystem(family=u'iOS', version=(5, 1), version_string='5.1')
        # request.user_agent.os.family  # returns 'iOS'
        # request.user_agent.os.version  # returns (5, 1)
        # request.user_agent.os.version_string  # returns '5.1'
        #
        # # Device properties
        # request.user_agent.device  # returns Device(family='iPhone')
        # request.user_agent.device.family  # returns 'iPhone'

        browser_info = {
            'is_mobile': request.user_agent.is_mobile,
            'is_tablet': request.user_agent.is_tablet,
            'is_touch_capable': request.user_agent.is_touch_capable,
            'is_pc': request.user_agent.is_pc,
            'is_bot': request.user_agent.is_bot,
            'browser': request.user_agent.browser,
            'os': request.user_agent.os,
            'device': request.user_agent.device}

        if request.user_agent.is_mobile:
            device_type = 'mobile'

        if request.user_agent.is_tablet:
            device_type = 'tablet'
        if request.user_agent.is_pc:
            device_type = 'pc'

        if request.user_agent.is_bot:
            device_type = 'bot'

        try:
            UserBrowserInfo.objects.create(user=request.user, os=request.user_agent.os, device_type=device_type,
                                           device_info=request.user_agent.device, browser=request.user_agent.browser)

        except Exception:
            raise

        return HttpResponse(repr(browser_info))


class CheckIsExistingUser(GenericAPIView):
    serializer_class = CheckIfExistingUserSerializer
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_summary="Check for existing user"
    )
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            mobile_no = serializer.validated_data.get('mobile_no')
            users = User.objects.filter(mobile=mobile_no)
            if users:
                return Response({"is_existing_user": True}, status=status.HTTP_200_OK)
            else:
                return Response({"is_existing_user": False}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.info('something went wrong reason '.format(str(e)))
            return Response({"is_existing_user": False}, status=status.HTTP_200_OK)


class CheckIsExistingEmailUser(GenericAPIView):
    serializer_class = CheckIfExistingEmailUserSerializer
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_summary="Checks if Email exists "
    )
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data.get('email')
            ret = verified_email_address_exists(email=email)  # returns a boolean value
            if ret:
                return Response({"is_existing_verified_user": True}, status=status.HTTP_200_OK)
            else:
                return Response({"is_existing_verified_user": False}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.info('something went wrong reason '.format(str(e)))
            return Response({"is_existing_user": False}, status=status.HTTP_200_OK)









