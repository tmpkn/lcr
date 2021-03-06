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
import psycopg2
from psycopg2.extensions import adapt
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

	def st(self, t):
		return t.decode('iso-8859-1')

	def handle(self, *args, **options):
		LcrRetailDSL.objects.all().delete()
		f = open('./dsl.txt', 'r')
		for d in f:
			dx = d.split(';')
			if dx[4].isdigit() and dx[5].isdigit():
				dsl = LcrRetailDSL()
				dsl.number_from = int(dx[4])
				dsl.number_to = int(dx[5])
				dsl.techs = dx[7].strip()
				dsl.save()
				self.say('- <%d; %d> : %s\r\n' % (dsl.number_from, dsl.number_to, dsl.techs))
		f.close()
