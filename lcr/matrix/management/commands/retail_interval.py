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
		f = open('/home/lcr/public_html/lcr/log/rt_interval', 'a')
		f.write(message)
		f.close()
		sys.stdout.write(message)
		sys.stdout.flush()

	def handle(self, *args, **options):
		# INPUTS
		asr = 33		# %
		acd = 70		# s
		response = 2	# %
		fuse = 0		# 1
		agents = len(LcrRetailAgent.objects.filter(status = 100))
		set_nlog(2001, agents)
		capacity = 40	# 1
		ato = 30		# s
		slog = '- A: %d' % (agents)
		interval_min = 1.0 * acd * asr / (100 * capacity)
		slog += ', INT(min): %d' % (int(interval_min * 100))
		if agents > fuse:
			# Enough Agents
			interval = 1.0 * acd * asr * response / (10000 * (agents - fuse))
			slog += ', C-INT: %d' % (int(interval * 100))
			if interval < interval_min:
				interval = interval_min
			if interval > ato:
				interval = ato
			slog += ', R-INT: %d' % (int(interval * 100))
		else:
			# Not Enough Agents, return ATO
			interval = ato
			slog += ', ATO-INT: %d' % (int(interval * 100))
		set_npar(1001, int(interval * 100))
		set_nlog(2002, int(interval * 100))
		slog += '\r\n'
		self.say(slog)
		
			
