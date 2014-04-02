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
import sys
import telnetlib
from mmap import mmap,ACCESS_READ
from xlrd import open_workbook
import pjsua as pj

class RetCode:
        lastCode = 0

class MyCallCallback(pj.CallCallback):
    def __init__(self, retCode, call=None):
        pj.CallCallback.__init__(self, call)
        self.retCode = retCode

    def on_state(self):
        print "Call is ", self.call.info().state_text,
        print "last code =", self.call.info().last_code,
        print "(" + self.call.info().last_reason + ")"
        self.retCode.lastCode = self.call.info().last_code

    def on_media_state(self):
        global lib
        if self.call.info().media_state == pj.MediaState.ACTIVE:
            call_slot = self.call.info().conf_slot
            lib.conf_connect(call_slot, 0)
            lib.conf_connect(0, call_slot)
            print "Hello world, I can talk!"

class Command(BaseCommand):
	help = 'Monitor the Server'

	def handle(self, *args, **options):
		tnPrompt = 'C:\Users\Administrator>'
		lib = pj.Lib()
    		lib.init(log_cfg = pj.LogConfig(level=3))
    		transport = lib.create_transport(pj.TransportType.UDP)
    		lib.start()
    		acc = lib.create_account_for_transport(transport)
		strLog = '--- STARTING NEW PROCESS\r\n'
		lc = RetCode()
		call = acc.make_call('sip:000@vs.ip.1.2.3.4:5060', MyCallCallback(lc))
		time.sleep(2)
		i = 0
		while i < 10 and not lc.lastCode:
			strLog += '- Test Call in progress, waiting for 10 seconds...\r\n'
			time.sleep(10)
			i += 1
		strLog += '- Test Call Code: ' + str(lc.lastCode) + '\r\n'
		tn = telnetlib.Telnet('vs.ip.1.2.3.4')
		tn.read_until('login: ')
		tn.write('Administrator\r\n')
		tn.read_until('password: ')
		tn.write('vs.123\r\n')
		tn.read_until(tnPrompt)
		if lc.lastCode == 404:
			strLog += '- VS process is operational!\r\n'
		else:
			strLog += '- Malfunctioning VS process, terminating...\r\n'
			tn.write('taskkill /F /IM VoipSwitch_384.exe\r\n')
			time.sleep(5)
			tn.read_until(tnPrompt)
		tn.write('tasklist\r\n')
		strProcessList = tn.read_until(tnPrompt)
		rx = re.search('VoipSwitch_384.exe(\s*?)(\d*?)(\s*?)Console', strProcessList)
		if rx:
			strVSPID = rx.groups()[1]
			strLog += '- Found VS PID: ' + strVSPID + '\r\n'
		else:
			strLog += '- VS PID Not Found! Launching new process...\r\n'
			tn.write('c:\\ps\\psexec -i \\\\localhost -u Administrator -p vs.123 -d "c:\\Program Files (x86)\\VoipSwitch\\VoipSwitch 2.0\\VoipSwitch_384.exe"\r\n')
			time.sleep(5)
			strPE = tn.read_until(tnPrompt)
			rxPE = re.search('with process ID (\d*?)\.', strPE)
			if rxPE:
				strNVSPID = rxPE.groups()[0]
				strLog += '- Success! New VS PID: ' + strNVSPID + '\r\n'
			else:
				sys.stdout.write(strPE)
				strLog += '- ERROR: Cannot launch VS!\r\n'
		strLog += '--- PROCESS OVER. SLEEPING FOR 30 SECONDS\r\n'
		tn.write('exit\r\n')
		sys.stdout.write(strLog)
		ssm = LcrStatServerMonitor()
		ssm.host = 'vs.ip.1.2.3.4'
		ssm.call_code = str(lc.lastCode)
		ssm.log = strLog
		ssm.save()	
		lib.destroy()
		lib = None		
