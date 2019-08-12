from django.urls import path
from apps.ajax import ajax

app_name = 'ajax'
urlpatterns = [
    path('username/', ajax.where_user, name='ajax_username'), #验证用户是否存在
]