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
from mmap import mmap,ACCESS_READ
from xlrd import open_workbook

class Command(BaseCommand):
	help = 'Reconciliation Procedure'

	def say(self, message):
		sys.stdout.write(message)
		sys.stdout.flush()

	def handle(self, *args, **options):
		cdr_int_match = 10
		bill_prec = 1
		rec_buffer = 60
		# *** #
		f = '%Y-%m-%d %H:%M:%S'
		recs = LcrRecon.objects.filter(id = 17)
		for r in recs:
			self.say('*** PROCESSING RECONCILIATION #%d - %s***\n- Step 1: Populating CDR/EXT database: ' % (r.id, r.str_party()))
			i = 0
			j = 0
			cdr_ext = open(r.cdr.path)
			for cdr in cdr_ext:
				cx = cdr.split(';')
				if len(cx) == 3:
					i += 1
					j += 1
					c = LcrReconCDR(recon = r, party = 2)
					if re.search('/', cx[0]):
						c_dt = datetime.datetime(*(time.strptime(cx[0], '%m/%d/%Y %H:%M')[0:5]))
						c_dt += timedelta(seconds = 30)
					else:
						c_dt = datetime.datetime(*(time.strptime(cx[0], f)[0:6]))
					c.cdr_start = c_dt
					c.cdr_number = cx[1]
					c.cdr_duration = cx[2]
					c.save()
				if j == 1000:
					self.say('%d... ' % (i, ))
					j = 0
			r.cdr.close()
			self.say('%d entries found\n' % (i, ))
			self.say('- Step 2: Locking the time interval: [')
			dt_ex_first = LcrReconCDR.objects.filter(recon = r, party = 2).order_by('cdr_start')[0].cdr_start
			str_dt = ('call_start > "%s" - INTERVAL 24 HOUR AND call_start < "%s" + INTERVAL 24 HOUR' % (dt_ex_first.isoformat(), dt_ex_first.isoformat(), ))
			ivs = 0
			int_found = []
			db = LcrSwitch.objects.filter(ip_addr = 'vs.ip.1.2.3.4')[0].get_db()
			for c in LcrReconCDR.objects.filter(recon = r, party = 2).order_by('cdr_start'):
				str_duration = 'duration > %d AND duration < %d' % (c.cdr_duration - bill_prec, c.cdr_duration + bill_prec)
				if r.party_type == 20:
					d = r.get_party()
					q = 'SELECT call_start, called_number, duration FROM calls JOIN gateways WHERE calls.id_route = gateways.id_route AND duration > 0 AND gateways.description = "%s" AND %s AND %s AND called_number LIKE "%%%s%%" AND %s' % (d.switch_name(), str_dt, dest_sql_prefixes(d), c.cdr_number, str_duration)
					#self.say('\n\n%s\n\n' % (q, ))
					db.query(q)
					res = db.store_result()
                                        o = res.fetch_row(maxrows = 0)
					if len(o):
						os = o[0]
						self.say('+')
						dt_lcr = datetime.datetime(*(time.strptime(os[0], f)[0:6]))
						dt_ext = c.cdr_start
						if dt_lcr >= dt_ext:
							iv = (dt_lcr - dt_ext).seconds
							ivs += iv
						else:
							iv = (-1) * (dt_ext - dt_lcr).seconds
							ivs += iv
						int_found.append(iv)
					else:
						self.say('-')
				if len(int_found) >= cdr_int_match:
					break
			interval = ivs / len(int_found)
			self.say('] : %.2f seconds\n' % (interval, ))
			self.say('- Step 3: Adjusting LCR Time Span: ')
			ext_dt_begin = dt_ex_first
			ext_dt_end = LcrReconCDR.objects.filter(recon = r, party = 2).order_by('-cdr_start')[0].cdr_start
			lcr_dt_begin = ext_dt_begin + timedelta(seconds = interval)
			lcr_dt_end = ext_dt_end + timedelta(seconds = interval)
			self.say('%s <> %s\n' % (lcr_dt_begin.isoformat(), lcr_dt_end.isoformat()))
			self.say('- Step 4: Populating CDR/LCR database: ')
			if r.party_type == 20:
				d = r.get_party()
				str_dt = ('call_start >= "%s" AND call_start <= "%s"' % (lcr_dt_begin.isoformat(), lcr_dt_end.isoformat()))
				q = 'SELECT call_start, called_number, duration FROM calls JOIN gateways WHERE calls.id_route = gateways.id_route AND duration > 0 AND gateways.description = "%s" AND %s AND %s' % (d.switch_name(), str_dt, dest_sql_prefixes(d))
				#self.say('\n\n%s\n\n' % (q, ))
				db.query(q)
				res = db.store_result()
				o = res.fetch_row(maxrows = 0)
				i = 0
				j = 0
				for os in o:
					i += 1
					j += 1
					c = LcrReconCDR(recon = r, party = 1)
					c.cdr_start = datetime.datetime(*(time.strptime(os[0], f)[0:6]))
					c.cdr_number = os[1]
					c.cdr_duration = os[2]
					c.save()
					if j == 1000:
						self.say('%d ... ' % (i, ))
						j = 0
				self.say('%d entries found\n' % (i, ))
			db.close()
			self.say('- Step 5: Reconciliation - EXT + DIFF: [')
			ext_i_secs = {'g': 0}
			ext_i_unmatched = {'g': 0}
			ext_i_calls = {'g': 0}
			i_diffs = {'g': 0}
			arr_diffs = []
			lcr_i_secs = {'g': 0}
			lcr_i_unmatched = {'g': 0}
			lcr_i_calls = {'g': 0}
			i_dt = lcr_dt_begin - timedelta(hours = 1)
			while (i_dt - timedelta(hours = 1) <= lcr_dt_end):
				str_date = i_dt.date().isoformat()
				int_hour = int(i_dt.hour)
				if not str_date in ext_i_secs:
					ext_i_secs[str_date] = {}
				ext_i_secs[str_date][int_hour] = 0
				if not str_date in ext_i_unmatched:
					ext_i_unmatched[str_date] = {}
                                ext_i_unmatched[str_date][int_hour] = 0
				if not str_date in ext_i_calls:
					ext_i_calls[str_date] = {}
				ext_i_calls[str_date][int_hour] = 0
				if not str_date in i_diffs:
					i_diffs[str_date] = {}
                                i_diffs[str_date][int_hour] = 0
				if not str_date in lcr_i_secs:
					lcr_i_secs[str_date] = {}
                                lcr_i_secs[str_date][int_hour] = 0
				if not str_date in lcr_i_unmatched:
					lcr_i_unmatched[str_date] = {}
                                lcr_i_unmatched[str_date][int_hour] = 0
				if not str_date in lcr_i_calls:
					lcr_i_calls[str_date] = {}
				lcr_i_calls[str_date][int_hour] = 0
				i_dt += timedelta(hours = 1)
			for cdr in LcrReconCDR.objects.filter(recon = r, party = 2).order_by('cdr_start'):
				str_date = (cdr.cdr_start + timedelta(seconds = interval)).date().isoformat()
				int_hour = int((cdr.cdr_start + timedelta(seconds = interval)).hour)
				ext_i_secs[str_date][int_hour] += cdr.cdr_duration
				ext_i_secs['g'] += cdr.cdr_duration
				ext_i_calls[str_date][int_hour] += 1
				ext_i_calls['g'] += 1
				x_cdr = LcrReconCDR.objects.filter(recon = r, party = 1, cdr_start__gte = cdr.cdr_start - timedelta(seconds = rec_buffer) + timedelta(seconds = interval), cdr_start__lte = cdr.cdr_start + timedelta(seconds = rec_buffer) + timedelta(seconds = interval), cdr_duration__gte = cdr.cdr_duration - r.tolerance, cdr_duration__lte = cdr.cdr_duration + r.tolerance, cdr_number__contains = cdr.cdr_number)
				if len(x_cdr):
					self.say('+')
				else:
					x_cdr_diff = LcrReconCDR.objects.filter(recon = r, party = 1, cdr_start__gte = cdr.cdr_start - timedelta(seconds = rec_buffer) + timedelta(seconds = interval), cdr_start__lte = cdr.cdr_start + timedelta(seconds = rec_buffer) + timedelta(seconds = interval), cdr_number__contains = cdr.cdr_number)
					if len(x_cdr_diff):
						xcds = x_cdr_diff[0]
						dispute = LcrReconDispute(recon = r, type = 3)
						if xcds.cdr_duration > cdr.cdr_duration:
							dispute.type = 3
						elif xcds.cdr_duration <= cdr.cdr_duration:
							dispute.type = 4
						dispute.cdr_lcr = xcds
						dispute.cdr_ext = cdr
						dispute.save()
						i_diffs[str_date][int_hour] += 1
						i_diffs['g'] += 1
						self.say('d')
					else:
						dispute = LcrReconDispute(recon = r, type = 2)
						dispute.cdr_ext = cdr
						dispute.save()
						ext_i_unmatched[str_date][int_hour] += 1
						ext_i_unmatched['g'] += 1
						self.say('-')
			self.say(']\n')
			self.say('- Step 6: Reconciliation - LCR: [')
			prefixes = []
			if r.party_type == 20:
				for deal in LcrDeal.objects.filter(destination = r.get_party()):
					if len(deal.number_prefix()):
						prefixes.append(deal.number_prefix())
			elif r.party_type == 10:
				prefixes.append(r.get_party().number_prefix())		
			for cdr in LcrReconCDR.objects.filter(recon = r, party = 1).order_by('cdr_start'):
				lcr_i_secs[cdr.cdr_start.date().isoformat()][int(cdr.cdr_start.hour)] += cdr.cdr_duration
				lcr_i_secs['g'] += cdr.cdr_duration
				lcr_i_calls[cdr.cdr_start.date().isoformat()][int(cdr.cdr_start.hour)] += 1
				lcr_i_calls['g'] += 1
				dn = cdr.cdr_number
				for prefix in prefixes:
					if re.match(prefix, dn):
						dn = re.sub(prefix, '', dn, 1)
						break			
				x_cdr = LcrReconCDR.objects.filter(recon = r, party = 2, cdr_start__gte = cdr.cdr_start - timedelta(seconds = rec_buffer) - timedelta(seconds = interval), cdr_start__lte = cdr.cdr_start + timedelta(seconds = rec_buffer) - timedelta(seconds = interval), cdr_duration__gte = cdr.cdr_duration - r.tolerance, cdr_duration__lte = cdr.cdr_duration + r.tolerance, cdr_number__contains = dn)
				if len(x_cdr):
					self.say('+')
				else:
					dispute = LcrReconDispute(recon = r, type = 1)
					dispute.cdr_lcr = cdr
					dispute.save()
					lcr_i_unmatched[cdr.cdr_start.date().isoformat()][int(cdr.cdr_start.hour)] += 1
					lcr_i_unmatched['g'] += 1
					self.say('-')
			self.say(']\n')
			self.say('- Step 7: Calculating results\n')
			gr = LcrReconResultsGlobal(recon = r)
			gr.interval = interval
			gr.lcr_calls = lcr_i_calls['g']
			gr.ext_calls = ext_i_calls['g']
			gr.lcr_secs = lcr_i_secs['g']
			gr.ext_secs = ext_i_secs['g']
			gr.lcr_unmatched = lcr_i_unmatched['g']
			gr.ext_unmatched = ext_i_unmatched['g']
			gr.diff_calls = i_diffs['g']
			gr.save()
			i_dt = lcr_dt_begin
                        while (i_dt <= lcr_dt_end):
				str_date = i_dt.date().isoformat()
                                int_hour = int(i_dt.hour)
				hr = LcrReconResultsHour(recon = r)
				hr.date = i_dt.date()
				hr.hour = int_hour
				hr.lcr_calls = lcr_i_calls[str_date][int_hour]
				hr.ext_calls = ext_i_calls[str_date][int_hour]
				hr.lcr_secs = lcr_i_secs[str_date][int_hour]
				hr.ext_secs = ext_i_secs[str_date][int_hour]
				hr.lcr_unmatched = lcr_i_unmatched[str_date][int_hour]
				hr.ext_unmatched = ext_i_unmatched[str_date][int_hour]
				hr.diff_calls = i_diffs[str_date][int_hour]
				hr.save()
				i_dt += timedelta(hours = 1)
			self.say('- Step 8: Detecting Overlapped Calls in EXT CDR: [')
			for cdr in LcrReconCDR.objects.filter(recon = r, party = 2).order_by('cdr_start'):
				x_cdr = LcrReconCDR.objects.filter(recon = r, party = 2, cdr_number = cdr.cdr_number, cdr_start__gte = cdr.cdr_start, cdr_start__lt = cdr.cdr_start + timedelta(seconds = cdr.cdr_duration)).exclude(id = cdr.id)
				if len(x_cdr):
					over = LcrReconOverlap(recon = r)
					over.cdr_ext_1 = cdr
					over.cdr_ext_2 = x_cdr[0]
					over.save()
					self.say('+')
				else:
					self.say('-')
			self.say(']\n')
			self.say('- Step 9: Calculating ACD distribution: [')
			acd_distros = {}
			dur_max =  LcrReconCDR.objects.filter(recon = r, party = 2).order_by('-cdr_duration')[0].cdr_duration
			dur = 0
			while (dur - 10) < dur_max:
				acd_distros[dur] = 0
				dur += 10
			for cdr in LcrReconCDR.objects.filter(recon = r, party = 2).order_by('cdr_start'):
				acd_distros[int(math.floor(cdr.cdr_duration/10)) * 10] += 1
				self.say('.')
			dur = 0
			while (dur - 10) < dur_max:
				ad = LcrReconACDDistro(recon = r)
				ad.acd_length = dur
				ad.acd_number = acd_distros[dur]
				ad.save()
				dur += 10
				self.say('D')
			self.say(']\n')
			self.say('*** PROCESS COMPLETE ***\n')
		sys.stdout.write('Sleeping for 180 seconds ...\n')
		time.sleep(180)
