from django.urls import path, include, re_path
from icf_messages.api.views import ComposeApiView, UserInboxApiView, EntityInboxApiView, EntitySentApiView, \
    UserSentApiView, EntityArchiveApiView, UserArchiveApiView, EntityTrashApiView, UserTrashApiView, UserReplyApiView, \
    EntityReplyApiView, EntityConversationApiView, UserConversationApiView, SetUserArchiveApiView, \
    SetEntityArchiveApiView, SetUserDeleteApiView, SetEntityDeleteApiView, SetUserRestoreArchivedApiView, \
    SetEntityRestoreArchivedApiView, SetUserRestoreDeletedApiView, SetEntityRestoreDeletedApiView, \
    InboxUnreadCount, EntityInboxUnreadCount, IcfNotificationList, NotificationListCount, NotificationDeleteApiView, \
    SetNotificationDeleteApiView, EntityInboxCountApiView, ComposeMessageAndEmailApiView

urlpatterns = [

    re_path(r'^(?P<entity_slug>[\w-]+)/compose/$', ComposeApiView.as_view(), name='compose message'),
    re_path(r'^(?P<entity_slug>[\w-]+)/compose_email/$', ComposeMessageAndEmailApiView.as_view(), name='compose-message-and-email'),
    re_path(r'^(?P<entity_slug>[\w-]+)/inbox/$', EntityInboxApiView.as_view(), name='entity inbox'),
    re_path(r'^(?P<entity_slug>[\w-]+)/inbox-count/$', EntityInboxCountApiView.as_view(), name='entity-inbox-count'),
    re_path(r'^inbox/$', UserInboxApiView.as_view(), name='user inbox'),
    re_path(r'^(?P<entity_slug>[\w-]+)/sent/$', EntitySentApiView.as_view(), name='entity sent items'),
    re_path(r'^sent/$', UserSentApiView.as_view(), name='user sent items'),
    re_path(r'^(?P<entity_slug>[\w-]+)/archives/$', EntityArchiveApiView.as_view(), name='entity arhived items'),
    re_path(r'^archives/$', UserArchiveApiView.as_view(), name='user archived items'),
    re_path(r'^(?P<entity_slug>[\w-]+)/archive/(?P<thread_id>[\d]+)/$', SetEntityArchiveApiView.as_view(), name='entity archive'),
    re_path(r'^archive/(?P<thread_id>[\d]+)/$', SetUserArchiveApiView.as_view(), name='user archive'),
    re_path(r'^(?P<entity_slug>[\w-]+)/trash/$', EntityTrashApiView.as_view(), name='entity deleted ite ms'),
    re_path(r'^trash/$', UserTrashApiView.as_view(), name='user deleted items'),
    re_path(r'^(?P<entity_slug>[\w-]+)/delete/(?P<thread_id>[\d]+)/$', SetEntityDeleteApiView.as_view(), name='entity delete'),
    re_path(r'^delete/(?P<thread_id>[\d]+)/$', SetUserDeleteApiView.as_view(), name='user delete'),
    re_path(r'^(?P<entity_slug>[\w-]+)/reply/(?P<message_id>[\d]+)/$', EntityReplyApiView.as_view(), name='entity reply'),
    re_path(r'^reply/(?P<message_id>[\d]+)/$', UserReplyApiView.as_view(), name='user reply'),
    re_path(r'^(?P<entity_slug>[\w-]+)/view/(?P<thread_id>[\d]+)/$', EntityConversationApiView.as_view(), name='view_conversation'),
    re_path(r'^view/(?P<thread_id>[\d]+)/$', UserConversationApiView.as_view(), name='view_conversation'),
    re_path(r'^(?P<entity_slug>[\w-]+)/restore-archive/(?P<thread_id>[\d]+)/$', SetEntityRestoreArchivedApiView.as_view(), name='entity restore from archive'),
    re_path(r'^restore-archive/(?P<thread_id>[\d]+)/$', SetUserRestoreArchivedApiView.as_view(), name='user restore from archive'),
    re_path(r'^(?P<entity_slug>[\w-]+)/restore-delete/(?P<thread_id>[\d]+)/$', SetEntityRestoreDeletedApiView.as_view(), name='entity restore from delete'),
    re_path(r'^restore-delete/(?P<thread_id>[\d]+)/$', SetUserRestoreDeletedApiView.as_view(), name='user restore from delete'),
    re_path(r'^inbox-unread-count/$', InboxUnreadCount.as_view(), name='user unread message count'),
    re_path(r'^(?P<entity_slug>[\w-]+)/inbox-unread-count/$', EntityInboxUnreadCount.as_view(), name='entity unread message count'),
    re_path(r'^user-notification-list/$', IcfNotificationList.as_view(), name='user notification list'),
    re_path(r'^notification-list-count/$', NotificationListCount.as_view(), name='notification list count'),
    re_path(r'^delete/notification/$', NotificationDeleteApiView.as_view(), name='notification delete list'),
    re_path(r'^delete/notification/(?P<id>[\d]+)/$', SetNotificationDeleteApiView.as_view(), name='set notification delete'),



]