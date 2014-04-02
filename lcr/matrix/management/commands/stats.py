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
from mmap import mmap,ACCESS_READ
from xlrd import open_workbook

def stat_get_period(deal, dt_from, dt_to):
	ret = {'calls_ok': 0, 'calls_fail': 0, 'seconds': 0}
	switch = deal.buy_carrier.switch
	db = switch.get_stat_db()
	# VOIPSWITCH
	if switch.type == 1:
		q_ok = """SELECT COUNT(*) AS calls, SUM(duration) AS duration FROM calls 
		LEFT JOIN clientsip ON calls.id_client = clientsip.id_client
		LEFT JOIN gateways ON calls.id_route = gateways.id_route
		WHERE True
		AND clientsip.login = '%s'
		AND gateways.description = '%s'
		AND calls.call_start >= '%s'
		AND calls.call_start >= '%s'
		AND calls.call_start < '%s'""" % (deal.buy_carrier.s_name, deal.destination.s_name, deal.dt_updated.isoformat(), dt_from.isoformat(), dt_to.isoformat())
		q_fail = """SELECT COUNT(*) AS fail FROM callsfailed
		LEFT JOIN clientsip ON callsfailed.id_client = clientsip.id_client
		LEFT JOIN gateways ON callsfailed.id_route = gateways.id_route
		WHERE True
		AND clientsip.login = '%s'
		AND gateways.description = '%s'
		AND callsfailed.call_start >= '%s'
		AND callsfailed.call_start >= '%s'
		AND callsfailed.call_start < '%s'""" % (deal.buy_carrier.s_name, deal.destination.s_name, deal.dt_updated.isoformat(), dt_from.isoformat(), dt_to.isoformat())
	# LCR
	if switch.type == 2:
		q_ok = """SELECT COUNT(*) AS calls, SUM(duration) AS duration FROM lcr_cdr_%d%02d
		WHERE duration > 0
		AND deal_id = %d
		AND dt_begin >= '%s'
		AND dt_begin >= '%s'
		AND dt_begin < '%s'""" % (dt_from.year, dt_from.month, deal.id, deal.dt_updated.isoformat(), dt_from.isoformat(), dt_to.isoformat())
		q_fail = """SELECT COUNT(*) AS fail FROM lcr_cdr_%d%02d
		WHERE duration = 0
		AND deal_id = %d
		AND dt_begin >= '%s'
		AND dt_begin >= '%s'
		AND dt_begin < '%s'""" % (dt_from.year, dt_from.month, deal.id, deal.dt_updated.isoformat(), dt_from.isoformat(), dt_to.isoformat())
	db.query(q_ok)
	r_ok = db.store_result()
	o_ok = r_ok.fetch_row(maxrows = 0)
	if len(o_ok):
		if o_ok[0][0]:
			ret['calls_ok'] = int(o_ok[0][0])
		if o_ok[0][1]:
			ret['seconds'] = int(o_ok[0][1])
	db.query(q_fail)
	r_fail = db.store_result()
	o_fail = r_fail.fetch_row(maxrows = 0)
	if len(o_fail):
		if o_fail[0][0]:
			ret['calls_fail'] = int(o_fail[0][0])
	db.close()
	#f = open('/home/lcr/public_html/lcr/log/stats.sql', 'a')
	#if deal.id == 945:
	#	sys.stdout.write('S')
	#	f.write(q_ok + '\r\n')
	#f.close()
	return ret

class Command(BaseCommand):
	help = 'Get the Stats'

	def say(self, message):
		f = open('/home/lcr/public_html/lcr/log/stats', 'a')
		f.write(message)
		f.close()
		sys.stdout.write(str(message))
		sys.stdout.flush()

	def handle(self, *args, **options):
		if get_cron_status(2) == 1:
			pass
		set_cron_status(2, 1)
		
		for deal in LcrDeal.objects.filter(is_active = True):
			self.say('* PROCESSING DEAL %s\r\n' % deal)
			self.say('- [')
			dt_pf = datetime.datetime.now() - timedelta(days = 2)
			dt_p = datetime.datetime(dt_pf.year, dt_pf.month, dt_pf.day, dt_pf.hour, 0, 0)
			while dt_p <= datetime.datetime.now() - timedelta(hours = 1):
				statcheck = LcrStatH.objects.filter(deal = deal, dt_when = dt_p)
				if len(statcheck):
					self.say('+')
				else:
					getstat = stat_get_period(deal, dt_p, dt_p + timedelta(hours = 1))
					stat = LcrStatH(deal = deal, dt_when = dt_p)
					stat.calls_ok = getstat['calls_ok']
					stat.calls_fail = getstat['calls_fail']
					stat.seconds = getstat['seconds']
					stat.ppm = deal.buy_price
					stat.save()
					if stat.seconds:
						self.say('H')
					else:
						self.say('h')
				dt_p += timedelta(hours = 1)
			self.say(']\r\n')		
		ss = LcrStatSessionStat()
		ss.save() 
		set_cron_status(2, 0)
		return 0
