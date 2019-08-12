from django.shortcuts import render,redirect,reverse,HttpResponse
from django.views.generic import View
import re
from apps.hm_user.models import HaiMaUser
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from haima_demo import settings
from celery_tasks.tasks import send_register_active_email
from django.contrib.auth import authenticate, login
from apps.hm_user import aliyun
from django.core.cache import cache   #短信
import json
from apps.hm_user import restful



#用户注册
class RegisterUser(View):
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):

        user_name = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        if not all([user_name, password, email]):
            return render(request, 'register.html', {"error_msg": "信息不完整"})
        if not re.match(r"^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$", email):
            return render(request, 'register.html', {'error_msg': '邮箱格式不正确'})
        if allow != "yes":
            return render(request, 'register.html', {"error_msg": "请勾选同意"})

        try:
            user = HaiMaUser.objects.get(username=user_name)
        except HaiMaUser.DoesNotExist:
            #如果出现该异常说明用户不存在，则让user为空
            user = None
        if user:
            return render(request, 'register.html', {"error_msg": "用户名已经存在"})

        user = HaiMaUser.objects.create_user(username=user_name, password=password,
                                             email=email, is_active=0)

        #生成用户激活邮件中的token
        # serializer = Serializer(settings.SECRET_KEY, 3600)  # 有效期1小时
        # info = {"confirm": user.id}
        # token = serializer.dumps(info).decode()    #这里要转成decode()

        # subject = "海马生鲜欢迎你"  # 邮件标题
        # message = ''# 邮件正文
        # sender = settings.EMAIL_FROM# 发件人
        # receiver = [email]# 收件人
        # html_message = """           <h1>%s  恭喜您成为海马生鲜注册会员</h1><br/><h3>请您在1小时内点击以下链接进行账户激 活</h3><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a> """ %  (user_name, token, token)
        # send_mail(subject, message, sender, receiver, html_message=html_message)
        serializer = Serializer(settings.SECRET_KEY, 3600)  # 有效期1小时
        info = {"confirm": user.id}
        token = serializer.dumps(info).decode()  # 这里要转成decode()
        send_register_active_email.delay(email, user_name, token)
        
        return redirect(reverse('hm_user_app:index'))


#邮箱账户激活
class ActiveView(View):
    #账户激活
    def get(self, request, token):
        # 进行账户激活
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            #获取用户id
            user_id = info['confirm']
            #根据用户id获取该用户对象
            user = HaiMaUser.objects.get(id=user_id)
            #设置用户对象中的is_active字段值为1，激活
            user.is_active = 1
            user.save()
            #使用反向解析跳转到登陆界面
            return redirect(reverse('hm_user_app:login'))
        except SignatureExpired as e:    #需要导入
            return HttpResponse("激活链接过期")



#用户登陆
class LoginUser(View):
    def get(self, request):    #显示登陆界面
        # print(1/0)
        #判断是否记住了用户名
        if "username" in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = "checked"
        else:
            username = ""
            checked = ""
        return render(request, 'login.html', {"username": username, "checked": checked})

    # 登陆验证
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        if not all([username, password]):
            return render(request, 'login.html', {'error_msg': '信息不完整'})
        # 提供了用户认证功能，即验证用户名以及密码是否正确，一般需要username 、password两个关键字参数。
        # 如果认证成功（用户名和密码正确有效），便会返回一个User实例对象，否则返回None。
        user = authenticate(username=username, password=password)
        if user is not None:   #用户名密码正确
            if user.is_active:      #用户已经激活
                # 该函数接受一个HttpRequest对象，以及一个经过认证的User实例对象（也就是
                # authenticate方法返回的User对象)
                # 该函数实现一个用户登录的功能。会在后端为该用户生成相关session数据。
                # 通常login()与authenticate()一起配合使用
                login(request, user)
                #跳转到首页，response是一个HttpResponseRedirect对象
                response = redirect("hm_user_app:index")
                remember = request.POST.get("remember")
                if remember == 'on':
                    #on表示勾选了，将用户保存在cookie中
                    response.set_cookie("username", username, max_age=7*24*3600)   #设置过期时间为1周
                else:
                    #删除cookie
                    response.delete_cookie("username")
                #返回response
                return response
            else:
                #用户未激活
                return render(request, 'login.html', {"error_msg": "账号未激活"})
        else:
            return render(request, 'login.html', {"error_msg": "用户和密码不对"})







#首页
class IndexHtml(View):
    def get(self, request):
        return render(request, 'index.html')

    def post(self, request):
        pass



#发送短信接口
def sms_send(request):
    # 1.获取手机号
    phone = request.GET.get('phone')
    #生成6位验证码
    code = aliyun.get_code(6,True)
    #缓存到redis数据库
    cache.set(phone, code, 60)    #60秒有效期
    #判断缓存中是否有phone
    cache.has_key(phone)
    #获取redis验证码
    cache.get(phone)
    result = aliyun.send_sms(phone, code)
    return HttpResponse(result)

#短信验证码验证接口
def sms_check(request):
    # 1.获取电话和手动输入的验证码
    phone = request.GET.get('phone')
    code = request.GET.get('code')
    cache_code = "1"   #要先定义一个假的
    #2.获取redis中保持的code
    if cache. has_key(phone):
        # 获取redis验证码
        cache_code = cache.get('phone')

    # 3.判断返回数据
    if code == cache_code:
        # return HttpResponse(json.dumps({"result": 'True'}))
        return restful.ok("ok", data=None)
    else:
        # return HttpResponse(json.dumps({"result": 'False'}))
        return restful.params_error("验证码错误", data=None)
