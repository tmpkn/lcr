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
	help = 'Synchro the switches'

	def say(self, message):
		f = open('/home/lcr/public_html/lcr/log/switches', 'a')
		f.write(message)
		f.close()
		sys.stdout.write(message)
		sys.stdout.flush()

	def handle(self, *args, **options):
		if get_cron_status(1) == 1:
			#return False
			pass 
		set_cron_status(1, 1)
		i_glob = 1
		while i_glob < 2:
			################
			# 1) CUSTOMERS #
			################
			#customers = LcrCustomer.objects.filter(id = 11)
			customers = LcrCustomer.objects.all()
			for customer in customers:
				# >>> VOIPSWITCH
				if customer.switch.type == 1 and customer.switch.id == 1:
					db = customer.switch.get_db()
					self.say('Syncing CUSTOMER ' + unicode(customer) + ':\r\n')
					q = "SELECT * FROM clientsip WHERE login = '%s'" % (customer.switch_name(), )
					db.query(q)
	                                r = db.store_result()
	                                o = r.fetch_row(maxrows = 0)
					if len(o):
					 	# Found
						cid = str(o[0][0])
						self.say('- Customer found! ID: ' + cid + '\r\n')
					else:
						# Not Found
						if customer.tech_prefix:
							tp = 'DP:%s->527%07d;TP:%s->;CP:' % (customer.tech_prefix, customer.id, customer.tech_prefix)
						else:
							tp = 'DP:527%07d;TP:;CP:' % (customer.id, )
						# VS - NEW
						#q = "INSERT INTO clientsip (login, password, type, id_tariff, tech_prefix, id_reseller, id_intrastate_tariff, id_currency, codecs, primary_codec, account_state) VALUES ('%s', '%s', %d, %d, '%s', %d, %d, %d, %d, %d, '0.0')" % (customer.switch_name(), customer.switch_name(), 515, 4, tp, -1, -1, 1, 264, 4)
						# VS - OLD
						q = "INSERT INTO clientsip (login, password, type, id_tariff, tech_prefix, id_reseller, id_intrastate_tariff, id_currency, account_state) VALUES ('%s', '%s', %d, %d, '%s', %d, %d, %d, '0.0')" % (customer.switch_name(), customer.switch_name(), 2228243, 1, tp, -1, -1, 1)
						db.query(q)
						cid = str(db.insert_id())
						self.say('- Customer NOT found and created with the NEW ID: ' + cid + '\r\n')
					ips = LcrCustomerIp.objects.filter(customer = customer)
					for ip in ips:
						q = "SELECT * FROM ipnumbers WHERE ip_number = '%s' AND id_client = %s" % (ip.ip_addr, cid)
						db.query(q)
						r = db.store_result()
						o = r.fetch_row(maxrows = 0)
						if len(o):
							# Found
							self.say('- IP ' + ip.ip_addr + ' found!\r\n')
						else:
							# Not Found
							q = "INSERT INTO ipnumbers (ip_number, id_client) VALUES ('%s', %s)" % (ip.ip_addr, cid)
							db.query(q)
							self.say('- IP ' + ip.ip_addr + ' NOT found and added!\r\n')
					db.close()

			###########################################
			# 2) TARIFFS + 3) DIALPLANS + 4) GATEWAYS #
			###########################################
			deals = LcrDeal.objects.filter(is_active = 1)
			for deal in deals:
				self.say('Syncing DEAL ' + unicode(deal) + ':\r\n')
				# >>> VOIPSWITCH
				# TODO: ToD TARRIF
				if deal.buy_carrier.switch.type == 1 and deal.buy_carrier.switch.id == 1:
					# *** TOD SWITCH PERIODS ***
					tod_sps = []
					tod = False
					if deal.tod.id != 1:
						tod = True
						tod_ps = deal.tod.lcrtodperiod_set.all()
						iv = deal.buy_carrier.switch.tod_interval
						for p in tod_ps:
							dt_ref = datetime.datetime(2011, 03, 13, 0, 0, 0)
							dt_A = datetime.datetime(2011, 03, (13 + p.from_day), p.from_hour, 0, 0)
							dt_B = datetime.datetime(2011, 03, (13 + p.to_day), p.to_hour, 59, 59)
							dt_Ax = dt_A + timedelta(hours = iv)
							dt_Bx = dt_B + timedelta(hours = iv)
							if dt_Ax.date() == dt_Bx.date():
								sp = {
									'from_day': get_dow(dt_Ax.isoweekday()),
									'to_day': get_dow(dt_Bx.isoweekday()),
									'from_hour': dt_Ax.hour * 100,
									'to_hour': dt_Bx.hour * 100 + 59
								}
								tod_sps.append(sp)
							else:
								sp = {
									'from_day': get_dow(dt_Ax.isoweekday()),
									'to_day': get_dow(dt_Ax.isoweekday()),
									'from_hour': dt_Ax.hour * 100,
									'to_hour': 2359
								}
								tod_sps.append(sp)
								sp = {
									'from_day': get_dow(dt_Bx.isoweekday()),
									'to_day': get_dow(dt_Bx.isoweekday()),
									'from_hour': 0,
									'to_hour': dt_Bx.hour * 100 + 59
								}
								tod_sps.append(sp)
					# *** SELL RATE ***
					db = deal.buy_carrier.switch.get_db()
					# 2A + 2C
					q = "SELECT * FROM tariffsnames WHERE description = 'lcr-S-%s'" % (deal.buy_carrier.switch_name(), )
					db.query(q)
					r = db.store_result()
					o = r.fetch_row(maxrows = 0)
					if len(o):
						# Found
						tid = str(o[0][0])
						self.say('- Tariff found! ID: ' + tid + '\r\n')
					else:
						# Not Found
						# VS - NEW
						# q = "INSERT INTO tariffsnames (description, minimal_time, resolution, surcharge_time, surcharge_amount, type, rate_multiplier, rate_addition, id_currency, base_tariff_id) VALUES ('lcr-S-%s', 1, 1, 0, '0.0', 0, -1, -1, 1, -1)" % (deal.buy_carrier.switch_name(), )
						# VS - OLD
						q = "INSERT INTO tariffsnames (description, minimal_time, resolution, surcharge_time, surcharge_amount, type, rate_multiplier, rate_addition) VALUES ('lcr-S-%s', 1, 1, 0, '0.0', 0, -1, -1)" % (deal.buy_carrier.switch_name(), )
						db.query(q)
						tid = str(db.insert_id())
						self.say('- Tariff NOT found and created with the NEW ID: ' + tid + '\r\n')
					codes = LcrDestinationE164.objects.filter(destination = deal.destination)
					for code in codes:
						str_code = code.code
						if deal.tech_prefix:
							str_code = deal.tech_prefix + code.code
						tod_q = ''
						if tod:
							tod_q = ' AND from_day = %d AND to_day = %d AND from_hour = %d AND to_hour = %d'
						# NO TOD
						if not tod:
							q = "SELECT * FROM tariffs WHERE id_tariff = %s AND prefix = '%s'" % (tid, str_code)
							db.query(q)
							r = db.store_result()
							o = r.fetch_row(maxrows = 0)
							if len(o):
								# Found
								self.say('- Found prefix %s (Prefix ID: %s) in Tariff ID %s!\r\n' % (str_code, str(o[0][0]), tid))
							else:
								# Not Found
								# VS - NEW
								# q = "INSERT INTO tariffs (id_tariff, prefix, description, voice_rate, from_day, to_day, from_hour, to_hour, grace_period, minimal_time, resolution, rate_multiplier, rate_addition, surcharge_time, surcharge_amount) VALUES (%s, '%s', '%s', %s, 0, 6, 0, 2400, 0, -1, -1, -1, -1, -1, -1)" % (tid, str_code, '#LCR# ' + deal.destination.name, str(deal.buy_price))
								# VS - OLD
								q = "INSERT INTO tariffs (id_tariff, prefix, description, voice_rate, from_day, to_day, from_hour, to_hour, grace_period, minimal_time, resolution, rate_multiplier, rate_addition) VALUES (%s, '%s', '%s', %s, 0, 6, 0, 2400, 0, 0, 0, -1, -1)" % (tid, str_code, '#LCR# ' + deal.destination.name, str(deal.buy_price))
								db.query(q)
								stid = str(db.insert_id())
								self.say('- Prefix %s NOT FOUND in Tariff ID %s! Added with Prefix ID: %s\r\n' % (str_code, tid, stid))
						# TOD
						else:
							for sp in tod_sps:
								q = "SELECT * FROM tariffs WHERE id_tariff = %s AND prefix = '%s' AND from_day = %d AND to_day = %d AND from_hour = %d AND to_hour = %d" % (tid, str_code, sp['from_day'], sp['to_day'], sp['from_hour'], sp['to_hour'])
								db.query(q)
								r = db.store_result()
								o = r.fetch_row(maxrows = 0)
								if len(o):
									# Found
									self.say('- (ToD! - %s) Found prefix %s (Prefix ID: %s) in Tariff ID %s!\r\n' % (unicode(deal.tod), str_code, str(o[0][0]), tid))
								else:
									# Not Found
									q = "INSERT INTO tariffs (id_tariff, prefix, description, voice_rate, from_day, to_day, from_hour, to_hour, grace_period, minimal_time, resolution, rate_multiplier, rate_addition, surcharge_time, surcharge_amount) VALUES (%s, '%s', '%s', %s, %d, %d, %d, %d, 0, 0, 0, -1, -1, -1, -1)" % (tid, str_code, '#LCR# ' + deal.destination.name, str(deal.buy_price), sp['from_day'], sp['to_day'], sp['from_hour'], sp['to_hour'])
									db.query(q)
									stid = str(db.insert_id())
									self.say('- (ToD! - %s) Prefix %s NOT FOUND in Tariff ID %s! Added with Prefix ID: %s\r\n' % (unicode(deal.tod), str_code, tid, stid))
					q = "UPDATE clientsip SET id_tariff = %s WHERE login = '%s'" % (tid, deal.buy_carrier.switch_name())
					db.query(q)
					self.say('- Made sure the customer uses Tariff ID %s\r\n' % (tid, ))
					db.close()
				# 4* - GATEWAYS
				# >>> VOIPSWITCH
				if deal.buy_carrier.switch.type == 1 and deal.buy_carrier.switch.id == 1:
					if deal.buy_carrier.switch.is_slave():
						# *** MASTER + SLAVE ***
						db_slave = deal.buy_carrier.switch.get_db()
						q = "SELECT * FROM gateways WHERE description = '%s'" % (deal.buy_carrier.switch.master_switch_sw_name, )
						db_slave.query(q)
						r = db_slave.store_result()
						o = r.fetch_row(maxrows = 0)
						if len(o):
							# Found
							mid = str(o[0][0])
							self.say('- Found master switch gateway ID %s on slave switch!\r\n' % mid)
						else:
							# Not Found
							mid = '0'
							self.say('- ERROR!!! Master switch gateway ID NOT FOUND on slave!\r\n')
						db_slave.close()
						db = deal.buy_carrier.switch.master_switch.get_db()
						str_switch = unicode(deal.buy_carrier.switch.master_switch)
					else:
						# *** MASTER ONLY ***
						db = deal.buy_carrier.switch.get_db()
						str_switch = unicode(deal.buy_carrier.switch)
					q = "SELECT * FROM gateways WHERE description = '%s'" % (deal.destination.switch_name())
					db.query(q)
					r = db.store_result()
					o = r.fetch_row(maxrows = 0)
					if len(o):
						# Found
						gid = str(o[0][0])
						self.say('- Found %s gateway on %s with ID: %s!\r\n' % (deal.destination.switch_name(), str_switch, gid))
						if deal.destination.ip_addr + ':5060' == o[0][2]:
							self.say('- Gateway ID %s has a matching IP! (%s)\r\n' % (gid, deal.destination.ip_addr))
						else:
							q = "UPDATE gateways SET ip_number = '%s:5060' WHERE id_route = %s" % (deal.destination.ip_addr, gid)
							db.query(q)
							self.say('- Changed the IP addres of Gateway ID %s to %s\r\n' % (gid, deal.destination.ip_addr))
					else:
						# Not Found
						# VS - NEW
						# q = "INSERT INTO gateways (description, ip_number, h323_id, type, call_limit, id_tariff, tech_prefix, codecs, video_codecs, fax_codecs) VALUES ('%s', '%s:5060', '@', 64, 0, -1, 'DN:;TP:', 264, 0, 0)" % (deal.destination.switch_name(), deal.destination.ip_addr)
						# VS - OLD
						q = "INSERT INTO gateways (description, ip_number, h323_id, type, call_limit, id_tariff) VALUES ('%s', '%s:5060', '@', 2097216, 0, -1)" % (deal.destination.switch_name(), deal.destination.ip_addr)
						db.query(q)
						gid = str(db.insert_id())
						self.say('- Gateway %s NOT FOUND on %s! Added with ID %s\r\n' % (deal.destination.switch_name(), str_switch, gid))
					db.close()
				# >>> VOIPSWITCH
				if deal.buy_carrier.switch.type == 1 and deal.buy_carrier.switch.id == 1:
					# 3* - DIALPLANS *** TODO: PRIORITIES !!! ***
					codes = LcrDestinationE164.objects.filter(destination = deal.destination)
					if deal.buy_carrier.switch.is_slave():
						# *** MASTER + SLAVE ***
						db_slave = deal.buy_carrier.switch.get_db()
						str_switch = unicode(deal.buy_carrier.switch)
						for code in codes:
							str_code = code.code
							if deal.tech_prefix:
								str_code = deal.tech_prefix + code.code
							cust_code = '527%07d%s' % (deal.buy_carrier.id, str_code)
							cust_prefix = ''
							q = "SELECT * FROM dialingplan WHERE telephone_number = '%s' AND priority = %d" % (cust_code, deal.priority)
							db_slave.query(q)
							r = db_slave.store_result()
							o = r.fetch_row(maxrows = 0)
							if len(o):
								# Found
		                                                did = str(o[0][0])
		                                                self.say('- Found dialplan entry for %s (priority %d) on %s, ID: %s! (gw check disabled)\r\n' % (cust_code, deal.priority, str_switch, did))
							else:
								# VS - NEW
								# q = "INSERT INTO dialingplan (telephone_number, priority, route_type, tech_prefix, id_route, call_type, type, from_day, to_day, from_hour, to_hour, balance_share, fields, call_limit) VALUES ('%s', %d, 0, '%s', %s, 1342177301, 0, 0, 6, 0, 2359, 0, '-1', 0)" % (cust_code, deal.priority, cust_prefix, mid)
								# VS - OLD
								q = "INSERT INTO dialingplan (telephone_number, priority, route_type, tech_prefix, id_route, call_type, type, from_day, to_day, from_hour, to_hour, balance_share, fields, call_limit) VALUES ('%s', %d, 0, '%s', %s, 1342177301, 0, 0, 6, 0, 2359, 0, '-1', 0)" % (cust_code, deal.priority, cust_prefix, mid)
		                                                db_slave.query(q)
		                                                did = str(db_slave.insert_id())
		                                                self.say('- Dialplan entry for %s NOT FOUND on %s! Added with ID %s, priority %d\r\n' % (cust_code, str_switch, did, deal.priority))
						db_slave.close()
						db = deal.buy_carrier.switch.master_switch.get_db()
						str_switch = unicode(deal.buy_carrier.switch.master_switch)
					else:
						# *** MASTER ONLY ***
	                                        db = deal.buy_carrier.switch.get_db()
	                                        str_switch = unicode(deal.buy_carrier.switch)
					# NO TOD
					if not tod:
		                                for code in codes:
							str_code = code.code
							if deal.tech_prefix:
								str_code = deal.tech_prefix + code.code
							cust_code = '527%07d%s' % (deal.buy_carrier.id, str_code)
							cust_prefix = 'DN:527%07d%s->%s' % (deal.buy_carrier.id, deal.tech_prefix, deal.destination.tech_prefix) 
							q = "SELECT * FROM dialingplan WHERE telephone_number = '%s' AND priority = %d" % (cust_code, deal.priority)
							db.query(q)
							r = db.store_result()
							o = r.fetch_row(maxrows = 0)
							if len(o):
								# Found
								did = str(o[0][0])
								self.say('- Found dialplan entry for %s (priority %d) on %s, ID: %s! (gw check disabled)\r\n' % (cust_code, deal.priority, str_switch, did))
							else:
								# VS - NEW
								# q = "INSERT INTO dialingplan (telephone_number, priority, route_type, tech_prefix, id_route, call_type, type, from_day, to_day, from_hour, to_hour, balance_share, fields, call_limit) VALUES ('%s', %d, 0, '%s', %s, 1342177301, 0, 0, 6, 0, 2359, 0, '-1', 0)" % (cust_code, deal.priority, cust_prefix, gid)
								# VS - OLD
								q = "INSERT INTO dialingplan (telephone_number, priority, route_type, tech_prefix, id_route, call_type, type, from_day, to_day, from_hour, to_hour, balance_share) VALUES ('%s', %d, 0, '%s', %s, 20, 0, 0, 6, 0, 2400, 100)" % (cust_code, deal.priority, cust_prefix, gid)
								db.query(q)
								did = str(db.insert_id())
								self.say('- Dialplan entry for %s NOT FOUND on %s! Added with ID %s, priority %d\r\n' % (cust_code, str_switch, did, deal.priority))	
					# TOD
					else:
						for sp in tod_sps:
							for code in codes:
								str_code = code.code
								if deal.tech_prefix:
									str_code = deal.tech_prefix + code.code
								cust_code = '527%07d%s' % (deal.buy_carrier.id, str_code)
								cust_prefix = 'DN:527%07d%s->%s' % (deal.buy_carrier.id, deal.tech_prefix, deal.destination.tech_prefix) 
								q = "SELECT * FROM dialingplan WHERE telephone_number = '%s' AND priority = %d  AND from_day = %d AND to_day = %d AND from_hour = %d AND to_hour = %d" % (cust_code, deal.priority, sp['from_day'], sp['to_day'], sp['from_hour'], sp['to_hour'])
								db.query(q)
								r = db.store_result()
								o = r.fetch_row(maxrows = 0)
								if len(o):
									# Found
									did = str(o[0][0])
									self.say('- (ToD! - %s) Found dialplan entry for %s (priority %d) on %s, ID: %s! (gw check disabled)\r\n' % (unicode(deal.tod), cust_code, deal.priority, str_switch, did))
								else:
									q = "INSERT INTO dialingplan (telephone_number, priority, route_type, tech_prefix, id_route, call_type, type, from_day, to_day, from_hour, to_hour, balance_share, fields, call_limit) VALUES ('%s', %d, 0, '%s', %s, 1342177301, 0, %d, %d, %d, %d, 0, '-1', 0)" % (cust_code, deal.priority, cust_prefix, gid, sp['from_day'], sp['to_day'], sp['from_hour'], sp['to_hour'])
									db.query(q)
									did = str(db.insert_id())
									self.say('- (ToD! - %s) Dialplan entry for %s NOT FOUND on %s! Added with ID %s, priority %d\r\n' % (unicode(deal.tod), cust_code, str_switch, did, deal.priority))	
					db.close()

			############
			# 5) BANKS #
			############

			# Removed for security

			############
			# 6) FUNDS #
			############
			points = LcrPoint.objects.filter(party = 1)
			for point in points:
				# >>> VOIPSWITCH
				if point.deal.buy_carrier.switch.type == 1 and point.deal.buy_carrier.switch.id == 1:
					db = point.deal.buy_carrier.switch.get_db()
					ident = '#LCR#pid%09d#' % point.id + point.ident
					q = "SELECT * FROM payments WHERE description = '%s'" % (ident, )
					db.query(q)
					r = db.store_result()
					o = r.fetch_row(maxrows = 0)
					if len(o):
						pid = str(o[0][0])
						self.say('- Found switch payment ID %s for funds point ID %d!\r\n' % (pid, point.id))
					else:
						self.say('- Switch payment for funds point ID %d NOT FOUND!! Proceeding...\r\n' % (point.id))
						q = "SELECT * FROM clientsip WHERE login = '%s'" % (point.deal.buy_carrier.switch_name(), )
						db.query(q)
						r = db.store_result()
						o = r.fetch_row(maxrows = 0)
						if len(o):
							cid = str(o[0][0])
							state = str(o[0][5])
							self.say('- Found client ID %s with account state: %s\r\n' % (cid, state))
							q = "INSERT INTO payments (id_client, client_type, money, data, type, description, invoice_id, actual_value, id_plan) VALUES (%s, 0, %s, NOW(), 1, '%s', 0, %s, -1)" % (cid, str(point.amount), ident, state)
							db.query(q)
							pid = str(db.insert_id())
							self.say('- Added switch payment with ID %s\r\n' % (pid, ))
							q = "UPDATE clientsip SET account_state = account_state + %s WHERE id_client = %s" % (str(point.amount), cid)
							db.query(q)
							self.say('- Increased account state of client ID %s by amount: %s\r\n' % (cid, str(point.amount)))
						else:
							# TODO!!
							pass
					db.close()
			
			# *** OVER! ***
			self.say('Sleeping for 1800 seconds ...\n')
			time.sleep(1800)
			i_glob += 1
		set_cron_status(1, 0)
