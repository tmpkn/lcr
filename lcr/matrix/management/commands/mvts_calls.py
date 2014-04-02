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
		while True:
			jc = LcrMVTSCalls(mvts_id = 1)
			jc.json_calls = commands.getoutput('/home/lcr/public_html/lcr/matrix/scripts/s_mcalls.php') 
			jc.save()
			time.sleep(1)
			self.say('.')	 
