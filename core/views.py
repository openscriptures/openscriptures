from django.shortcuts import render_to_response
from models import *
import datetime
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse


from django.http import HttpResponse

def index(request):
    now = datetime.datetime.now()
    return HttpResponse("Hello, world. This is the index. %s" % now)

def hello(request, name):
    #datetime.timedelta(hours=params['name'])
    #return HttpResponse("Hello %s" % params['name'])
    meta_values = request.META.items()
    meta_values.sort()
    
    #t = get_template('hello.html')
    #html = t.render(Context(params))
    #return HttpResponse(html)
    return render_to_response('hello.html', locals())

