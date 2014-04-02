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
		f = open('/home/lcr/public_html/lcr/log/rt_agents', 'a')
		f.write(message)
		f.close()
		#sys.stdout.write(message)
		#sys.stdout.flush()

	def handle(self, *args, **options):
		LcrRetailAgent.objects.all().update(status = 1)
		stats = ragents_pbx_stats()
		for s in stats['queue']:
			self.say('.')
			astatus = 0
			if re.search('PAUSED', s['status']):
				astatus = 10
			if re.search('ACTIVE', s['status']) or re.search('RING', s['status']):
				astatus = 100
			if astatus != 0:
				self.say('!')
				s['agent'].status = astatus
				s['agent'].save()
		self.say('OK\r\n')
		
			
