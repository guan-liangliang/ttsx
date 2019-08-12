from django.urls import path
from apps.hm_user import views

app_name = 'hm_user_app'
urlpatterns = [
    path("login/", views.LoginUser.as_view(), name='login'),
    path("register/", views.RegisterUser.as_view(), name='register'),
    path("index/", views.IndexHtml.as_view(), name='index'),
    path("active/<token>", views.ActiveView.as_view(), name="active"),   #邮箱激活账号

    path("sms_send/", views.sms_send, name='sms_send'),   #发送短信接口
    path("sms_check/", views.sms_check, name='sms_check'),  #短信验证接口
]