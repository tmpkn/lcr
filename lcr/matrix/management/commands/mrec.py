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
import math
import psycopg2
from mmap import mmap,ACCESS_READ
from xlrd import open_workbook

class Command(BaseCommand):
	help = 'Synchro the switches'

	def say(self, message):
		sys.stdout.write(message)
		sys.stdout.flush()

	def handle(self, *args, **options):
		hident = 'Customer'
		adjsec = 3318
		delsec = 120
		deldur = 3
		customer_id = 2
		fr = open('./mrec.csv', 'r')
		fw = open('./mres.csv', 'w')
		matches = []
		strpath = '%Y-%m-%d %H:%M:%S'
		conn = psycopg2.connect("host=lcrdb dbname=lcr user=lcr password=pass")
		cur = conn.cursor()
		#
		for fl in fr:
			addstr = ',0,0,0\r\n'
			flx = fl.split(',')
			if flx[0] != hident:
				orig_dt = datetime.datetime.strptime(flx[2], '%d/%m/%Y %H:%M:%S')
				start_dt = orig_dt + timedelta(seconds=(adjsec - delsec))
				stop_dt = orig_dt + timedelta(seconds=(adjsec + delsec))
				q = 'SELECT * FROM rcdr cdr, matrix_lcrdeal deal WHERE deal.id = cdr.deal_id AND deal.buy_carrier_id = %d AND number_destination=\'%s\' AND dt_start >= \'%s\' AND dt_start <= \'%s\' AND billsec >= %d AND billsec <= %d' % (customer_id, flx[4], start_dt.strftime(strpath), stop_dt.strftime(strpath), int(flx[5]) - deldur, int(flx[5]) + deldur)
				cur.execute(q)
				try:
					res = cur.fetchone()
					db_billsec = int(res[15])
					diffsec = int(flx[5]) - db_billsec
					if int(res[0]) in matches:
						rcode = 4
						diffsec = int(flx[5])
						self.say('D')
					else:
						if abs(diffsec) > deldur:
							rcode = 2
							if db_billsec == 0:
								rcode = 3
								self.say('0')
							else:
								self.say('M')
						else:
							rcode = 1
							self.say('V')
					addstr = ',%d,%d,%d\r\n' % (res[0], rcode, diffsec)
				except:
					self.say('X')
					addstr= ',0,0,%d\r\n' % int(flx[5])
				fw.write('%s%s' % (fl.strip(), addstr))
			else:
				self.say('H')
		#
		fw.close()
		fr.close()