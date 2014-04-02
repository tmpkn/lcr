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
		acmPrompt = 'Asterisk Call Manager/1.1'
		tn = telnetlib.Telnet('pbx.ip.1.2.3.4', 5069)
		tn.read_until(acmPrompt)
		tn.write('Action: login\r\nUsername: lcr\r\nSecret: pass\r\nEvents: off\r\n\r\n')
		robos = LcrRobo01.objects.all().filter(call_answered = 0).order_by('-id')
		for robo in robos:	
			tn.write('Action: Originate\r\nChannel: SIP/trunk_robo/' + str(robo.phone) + '\r\nContext: cont_robo01\r\nExten: ' + str(robo.phone) + '\r\nPriority: 1\r\nTimeout: 25000\r\nCallerid: ' + str(robo.phone) + '\r\nAsync: 1\r\n\r\n')
			self.say('R')
			time.sleep(0.66)
