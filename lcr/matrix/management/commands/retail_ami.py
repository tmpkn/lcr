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
		pat_login = 'Event: PeerStatus\r\nPrivilege: system,all\r\nChannelType: SIP\r\nPeer: SIP\/771(\d*?)\r\nPeerStatus: Registered\r\nAddress: (.*?)\r\n\r\n'
		pat_logout = 'Event: PeerStatus\r\nPrivilege: system,all\r\nChannelType: SIP\r\nPeer: SIP/771(\d*?)\r\nPeerStatus: Unregistered\r\nCause: (.*?)\r\n\r\n'
		acmPrompt = 'Asterisk Call Manager/1.1'
		tn = telnetlib.Telnet('pbx.ip.1.2.3.4', 6969)
		tn.read_until(acmPrompt)
		tn.write('Action: login\r\nUsername: lcr\r\nSecret: secret\r\nEvents: on\r\n\r\n')
		self.say('* Logged in...\r\n')
		while True:
			t = tn.read_until('\r\n\r\n')
			if re.search(pat_login, t):
				x = re.search(pat_login, t).groups()
				agent = '771' + x[0]
				ip = x[1]
				tn.write('Action: QueueAdd\r\nQueue: SSEN\r\nInterface: Local/%s@cont-tmp\r\nPenalty: 10\r\nPaused: false\r\n\r\n' % (agent, ))
				self.say('* Login Detected - Agent %s from %s - Added to Queue SSEN\r\n' % (agent, ip))
			if re.search(pat_logout, t):
				x = re.search(pat_logout, t).groups()
				agent = '771' + x[0]
				cause = x[1]
				tn.write('Action: QueueRemove\r\nQueue: SSEN\r\nInterface: Local/%s@cont-tmp\r\n\r\n' % (agent, ))
				self.say('* Logout Detected - Agent %s, Reason: %s - Removed from Queue SSEN\r\n' % (agent, cause))
		tn.write('Action: Logoff\r\n\r\n')
		self.say('* Montezuma!')