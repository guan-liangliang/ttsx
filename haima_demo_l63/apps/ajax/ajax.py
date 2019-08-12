from django.shortcuts import HttpResponse
from apps.hm_user.models import HaiMaUser
import json


#验证用户是否已经存在
def where_user(request):
    username = request.GET.get('username')
    try:
        HaiMaUser.objects.get(username=username)
        return HttpResponse(json.dumps({'res': "True"}))
    except HaiMaUser.DoesNotExist:   #报错说明用户不存在
        return HttpResponse(json.dumps({'res': "False"}))


