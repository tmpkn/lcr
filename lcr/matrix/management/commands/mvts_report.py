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
		dt_begin = datetime.date.today() - datetime.timedelta(days = 1)
		db = _mysql.connect('mvts.db.1.2.3.4', 'mvts', 'mvts', 'pass')
		while dt_begin < datetime.date.today():
			tabname = '%d%02d' % (dt_begin.year, dt_begin.month)
			q = 'SELECT in_zone, dp_name, SUM(elapsed_time)/1000, SUM(elapsed_time > 0), SUM(elapsed_time IS NULL) FROM mvts_cdr_%s WHERE cdr_date >= "%s 00:00:00" AND cdr_date <= "%s 23:59:59" GROUP BY in_zone, dp_name' % (tabname, dt_begin.isoformat(), dt_begin.isoformat())
			self.say('%s\r\n' % q)
			db.query(q)
			r = db.store_result()
			o = r.fetch_row(maxrows = 0)
			for os in o:
				if os[2]:
					rep = LcrMVTSReport(mvts_id = 1)
					rep.dt_day = dt_begin
					rep.seconds = int(float(os[2]))
					rep.customer = os[0]
					rep.destination = os[1]
					if os[3]:
						rep.calls = os[3]
					else:
						rep.calls = 0
					if os[4]:
						rep.failed = os[4]
					else:
						rep.failed = 0
					if rep.customer and rep.destination:
						rep.save()	
			dt_begin += datetime.timedelta(days = 1) 
		db.close()
