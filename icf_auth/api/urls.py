from django.urls import path, include, re_path
from rest_auth.views import PasswordResetConfirmView, PasswordChangeView
from knox.views import LogoutView as KnoxLogoutView
from knox.views import LogoutAllView as KnoxLogoutAllView

from icf_auth.api.views import ICFVerifyEmailView, django_rest_auth_null, ICFResendVerificationEmail, SendMobileOTP, \
    VerifyMobileOTP, ExampleView, UserProfileAPIView, UserProfileImageViewSet, CheckPassword, ICFLoginView, \
    ICFRegisterView, PasswordResetConfirmView, CheckForExistingUserView, PasswordResetView, get_browser_info, \
    CheckIsExistingUser, SendEmailOTP, VerifyEmailOTP, NewICFRegisterView, TempICFRegisterView, \
    CheckIsExistingEmailUser, ResendEmailOTPView
from rest_framework.routers import DefaultRouter

from icf_integrations import views

router = DefaultRouter()
router.register(r'', UserProfileImageViewSet, basename='profile-image')

urlpatterns = [
    re_path(r'^mobile-register/$', SendMobileOTP.as_view(), name='mobile-register'),
    re_path(r'^mobile-verify/$', VerifyMobileOTP.as_view(), name='mobile-verify'),
    re_path(r'^email-register/$', SendEmailOTP.as_view(), name='email-register'),
    re_path(r'^email-verify/$', VerifyEmailOTP.as_view(), name='email-verify'),
    re_path(r'^signup/$', ICFRegisterView.as_view(), name='signup'),
    re_path(r'^temp-signup/$', TempICFRegisterView.as_view(), name='signup'),
    re_path(r'^new-signup/$', NewICFRegisterView.as_view(), name='signup'),
    re_path(r'^resend-email-otp/$', ResendEmailOTPView.as_view(), name='resend-email-otp'),
    re_path(r'^verify-email/(?P<key>[-:\w]+)/$', ICFVerifyEmailView.as_view(), name='icf-verify-email'),
    re_path(r'^resend-verification-email/$', ICFResendVerificationEmail.as_view(),
        name='resend-verification-email'),
    re_path(r'^email-verification-sent/$', django_rest_auth_null, name='account_email_verification_sent'),

    #re_path(r'^login/$', LoginView.as_view(), name='icf-login'),
    re_path(r'^login/$', ICFLoginView.as_view(), name='icf-login'),
    re_path(r'^login-check/$', ExampleView.as_view(), name='icf-login-check'),
    re_path(r'^password-check/$', CheckPassword.as_view(), name='icf-password-check'),

    re_path(r'^password-reset/$', PasswordResetView.as_view(),  name='icf-password-reset'),
    re_path(r'^check-for-existing-user/$', CheckForExistingUserView.as_view(), name='check-for-existing-user'),
    re_path(r'^password-reset-confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        PasswordResetConfirmView.as_view(), name='password_reset_confirm'),


    # URLs that require a user to be logged in with a valid session / token.
    #re_path(r'^logout/$', LogoutView.as_view(), name='knox_logout'),
    re_path(r'^logout/$', KnoxLogoutView.as_view(), name='knox_logout'),
    # Used to logout the user from all sessions
    re_path('r^logoutall/$', KnoxLogoutAllView.as_view(), name='icf-logoutall'),

    re_path(r'^change-password/$', PasswordChangeView.as_view(), name='icf-change-password'),
    re_path(r'^user-profile/$', UserProfileAPIView.as_view(), name="user-profile"),
    re_path(r'^user-profile-image/', include(router.urls)),
    re_path(r'^get-browser-info/', get_browser_info, name="get-browser-info"),
    re_path(r'^is-existing-user/$', CheckIsExistingUser.as_view(), name='is-user-exists-with-mobile-no'),
    re_path(r'^is-existing-email-user/$', CheckIsExistingEmailUser.as_view(), name='is-user-exists-with-email'),

]

# re_path('password-reset-confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', django_rest_auth_null, name='password_reset_confirm'),
# re_path(r'^user/$', UserDetailsView.as_view(), name='rest_user_details'),
# re_path(r'^password-reset-confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
#      PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
