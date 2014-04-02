from django.core.management.base import BaseCommand, CommandError
import sys, os
from lcr.matrix.models import *
from lcr.matrix.views import *
from django.http import HttpResponse, HttpResponseRedirect
from django.template import Context, RequestContext, loader
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.core.mail import send_mail, EmailMessage
from django.db.models import Q
from django import forms
from types import ListType
from datetime import date, timedelta, datetime
from django.forms import ModelForm
import re
import base64
import datetime
import urllib
import Image
import os
import random
import string
import pprint
import time
import simplejson
import _mysql
import pycurl
import telnetlib
import ESL
from mmap import mmap,ACCESS_READ
from xlrd import open_workbook

class Command(BaseCommand):
	help = 'Get the Stats'

	def say(self, message):
		#f = open('/home/lcr/public_html/lcr/log/tg_calls', 'a')
		#f.write(message)
		#f.close()
		sys.stdout.write(message)
		sys.stdout.flush()

	def handle(self, *args, **options):
		e = ESL.ESLconnection('pbx.ip.1.2.3.4', '8099', 'pass')
		#robos = LcrRobo01.objects.all().filter(call_answered = 0).order_by('id')
		robos = LcrRetailData.objects.filter(placed = 0).order_by('id')[:35000]
		for robo in robos:
			if datetime.datetime.now().hour > 20:
				self.say('Goodnight!\r\n')
				break
			interval = get_npar(1001).pval
			robo.placed = 1
			robo.save()
			q = 'bgapi originate {ignore_early_media=true}sofia/external/34' + str(robo.phone_1) + '@pstn.ip 771' + str(robo.phone_1) + ' XML robo'
			e.sendRecv(q)
			self.say('- [%s] %s + INT(%d cs)\r\n' % (datetime.datetime.now().isoformat(), robo.phone_1, interval))
			time.sleep(interval / 100.0)
