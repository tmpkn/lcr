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
from datetime import date, timedelta
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
from mmap import mmap,ACCESS_READ
from xlrd import open_workbook

class Command(BaseCommand):
	help = 'Monitor the Deals'

	def handle(self, *args, **options):
		monitors = LcrMonitor.objects.all()
		db = _mysql.connect('vs.monitor.1.2.3.4', 'root', 'pass', 'pass')
		for monitor in monitors:
			sys.stdout.write('Monitoring ' + unicode(monitor.deal) + '...\n')
			pass_asr = False
			pass_acd = False
			pass_vol = False
			pass_monitor = False
			str_ret = '- Checking ' + monitor.get_period_display() + ' statistics for Deal: ' + unicode(monitor.deal) + '\n\r'
			o = deal_delta(monitor.deal, monitor.get_period_display(), db)
			# ASR
			str_ret += '- - '
			if monitor.asr == 0:
				pass_asr = True
				str_ret += 'ASR Test Disabled : PASS'
			else:
				if float(o['asr']) >= float(monitor.asr):
					pass_asr = True
					str_ret += 'ASR Test: (STAT) ' + str(o['asr']) + ' % >= ' + str(monitor.asr) + ' % (MONITOR) : PASS'
				else:
					str_ret += 'ASR Test: (STAT) ' + str(o['asr']) + ' % < ' + str(monitor.asr) + ' % (MONITOR) : FAIL'
			str_ret += '\r\n'
			# ACD
			str_ret += '- - '
			if monitor.acd == 0:
				pass_asd = True
				str_ret += 'ACD Test Disabled : PASS'
			else:
				if float(o['ok'][0][2]) >= float(monitor.acd):
					pass_acd = True
					str_ret += 'ACD Test: (STAT) ' + str(o['ok'][0][2]) + ' sec >= ' + str(monitor.acd) + ' sec (MONITOR) : PASS'
				else:
					str_ret += 'ACD Test: (STAT) ' + str(o['ok'][0][2]) + ' sec < ' + str(monitor.acd) + ' sec (MONITOR) : FAIL'
			str_ret += '\r\n'
			# VOL
			str_ret += '- - '
			if monitor.vol == 0:
				pass_vol = True
				str_ret += 'VOLUME Test Disabled : PASS'
			else:
				if float(o['ok'][0][1]) >= float(monitor.vol):
					pass_vol = True
					str_ret += 'VOL Test: (STAT) ' + str(o['ok'][0][1]) + ' min >= ' + str(monitor.vol) + ' min (MONITOR) : PASS'
				else:
					str_ret += 'VOL Test: (STAT) ' + str(o['ok'][0][1]) + ' min < ' + str(monitor.vol) + ' min (MONITOR) : FAIL'
			str_ret += '\r\n'
			pass_monitor = pass_asr and pass_acd and pass_vol
			if pass_monitor:
				str_ret += '- Monitor Result : PASS'
			else:
				str_ret += '- Monitor Result : FAIL'
				if monitor.status == 1:
					str_mail = 'This is an automated message from LCR Quality Monitor Service.\r\n\r\nThere has been a problem detected in the VoIP traffic and your attention is required. Here are the Monitor Logs that triggered this alert:\r\n\r\n' + str_ret + '\r\n\r\nPlease note, that this Monitor will be marked as Trigerred and will *NOT* send you any further emails until you manually turn the alert off in the LCR Administration Panel.\r\n\r\n-- \r\nLCR Quality Monitor Service - lcr-qms@tesserakt.eu - http://lcr.tesserakt.eu'
					str_topic = '[LCR-QMS] Problem with Route: ' + unicode(monitor.deal)
					send_mail(str_topic, str_mail, 'lcr-qms@tesserakt.eu', ['dest@email.com'])
				monitor.status = 2
				monitor.save()
			str_ret += '\r\n'
			sys.stdout.write(str_ret)
		db.close()
