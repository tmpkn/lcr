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
		conf_topic_dests = 3
		mvts_alerts = mvts_get_alert()
		alerts = []
		for m in mvts_alerts:
			if m['status'] == 'ALERT':
				alerts.append(m)
		td = ''
		i = 0
		for a in alerts:
			if i < conf_topic_dests:
				if i > 0:
					td += ', '
				td += a['check'].destination
			i += 1
		if len(alerts) > conf_topic_dests:
			td += ' and OTHERS!'
		c = 'This is an automated MVTS Traffic Alerts message.\r\n\r\nIn the last session there have been the following Alerts found:\r\n\r\n'
		for a in alerts:
			c += '* ' + a['check'].customer + ' / ' + a['check'].destination + ': Volume Change ' + str(a['change']) + '%\r\n'
		c += '\r\nMore information available at: http://lcr.tesserakt.eu/mvts/alert/\r\n-- \r\nMVTS Traffic Alerts'
		if len(alerts):
			send_mail('Alerts warning for ' + td, c, 'alerts-mvts@tesserakt.eu', ['dest@email.com'])
		self.say('Sent: ' + str(len(alerts)) + '\r\n') 	
