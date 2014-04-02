# -*- coding: utf-8 -*-

from lcr.matrix.models import *
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.template import Context, RequestContext, loader
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
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
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.lib.colors import Color
from django.contrib.localflavor.es.es_provinces import PROVINCE_CHOICES
from dateutil.relativedelta import relativedelta
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle, Paragraph, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.graphics.barcode import code39
from cStringIO import StringIO
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
import operator
import commands
import telnetlib
from _mysql import OperationalError
from mmap import mmap,ACCESS_READ
from xlrd import open_workbook
from urllib import unquote
from xmlrpclib import ServerProxy

os.environ['HOME'] = '/home/lcr/public_html/lcr'
CONF_BASEDIR = os.environ['HOME']
CONF_BASEPDF = CONF_BASEDIR + '/invoices'

partners = {
    99: {
        'id':		99,
        'name':		'LCR Mat(r)ix!',
        'logo':		'tess.png',
        'header':	'header_0.html',
    },
    98: {
        'id':		98,
        'name':		'TIVR - Tesserakt IVR Platform',
        'logo':		'tess.png',
        'header':	'header_98.html',
    },
    1: {
        'id':		1,
        'name':		'YOUR COMPANY LTD',
        'logo':		'logo.png',
        'header':	'header_1.html',
    },
}

# Reverse Lookups
aliases = {
    'lcr.tesserakt.eu': 99,
    'customer.your-company-website.com': 1,
}

lcr_uid = 1

def get_npar(key):
    p = LcrNumParameter.objects.get(pkey = key)
    return p

def set_npar(key, val):
    p = get_npar(key)
    p.pval = val
    p.save()
    return True

def set_nlog(key, val):
    l = LcrNumLog(pkey = key)
    l.pval = val
    l.save()
    return True

def get_pid(request):
    return partners[aliases[request.META['HTTP_HOST']]]

# Cheap DOW hack (;
def get_dow(iwd):
    if iwd == 7:
        return 0
    else:
        return iwd

# Template Renderer
def wrender(t_name, t_params, request):
    p = get_pid(request)
    # You can quickly block a partner in an emergency by doing this:
    #if p['id'] == 999:
    #	return HttpResponse('')
    t_params['p'] = p
    ss = LcrStatSessionStat.objects.order_by('-id')[0]
    t_params['ss'] = ss
    t_params['ss_delta'] = (datetime.datetime.now() - ss.dt_when).seconds

    # Partners with access to Customer Websites
    web_partners = [1, 99]

    # Partners with access to IVR Websites
    ivr_partners = [1, 99]
    if p['id'] in web_partners:
        return render_to_response(t_name, t_params, context_instance = RequestContext(request))
    else:
        return HttpResponse('')

def get_cron_status(job_id):
    cs = LcrCronStatus.objects.get(job = job_id)
    return cs.status

def set_cron_status(job_id, status_id):
    cs = LcrCronStatus.objects.get(job = job_id)
    cs.status = status_id
    cs.save()

def home(request):
    p = get_pid(request)
    # Wholesale Index
    if p['id'] != 666:
        return wrender('index_' + str(p['id']) + '.html', {}, request)
    # Retail Operations Index - Agent Signup / Login
    else:
        if request.user.is_authenticated():
            leads_web = LcrRetailCandidateWC.objects.filter(operator_id = request.user.id)
            leads_pan = LcrRetailCandidate.objects.filter(operator = request.user, status = 98)
            return wrender('index_666.html', {'web': len(leads_web), 'pan': len(leads_pan)}, request)
        else:
            if request.method == 'POST':
                f = ReconForm(request.POST, request.FILES)
                bf = RetailBasicForm(request.POST, prefix = 'bf')
                af = RetailAgentForm(request.POST, prefix = 'af')
                if af.is_valid() and bf.is_valid():
                    r_user = 'ag_' + User.objects.make_random_password()
                    r_pass = User.objects.make_random_password()
                    u = User.objects.create_user(r_user, bf.cleaned_data['email'], r_pass)
                    u.first_name = bf.cleaned_data['first_name']
                    u.last_name = bf.cleaned_data['last_name']
                    u.save()
                    p = LcrProfile(user = u)
                    p.save()
                    a = af.save(commit = False)
                    a.user = u
                    a.campaign = LcrRetailAgentCampaign.objects.get(id = 1)
                    a.save()
                    sip_name = str(77100000 + u.id)
                    ara = LcrRetailARASipFriend(agent = a, name = sip_name, secret = r_pass)
                    ara.context = 'cont-tmp'
                    ara.save()
                    t = 'Welcome Email'
                    send_mail('New Account Created!', t, 'admin@campaign-website.com', (bf.cleaned_data['email'], ), True, 'admin@campaign-website.com', 'password')
                    return wrender('agent_signup_ok.html', {}, request)
            else:
                bf = RetailBasicForm(prefix = 'bf')
                af = RetailAgentForm(prefix = 'af')
            return wrender('agent_signup.html', {'bf': bf, 'af': af}, request)

def free_cdrgen(request):
    cf = CDRGenForm()
    return wrender('cdrgen.html', {'cf': cf}, request)

def ivr_live(request):
    s = ServerProxy('http://IVR-FS:8080')
    lcs = []
    o = s.freeswitch.api("show", "channels")
    for os in o.split("\n"):
        osx = os.split(',')
        if len(osx) > 24:
            if osx[1] == 'inbound' and osx[24] == 'ACTIVE':
                lcs.append(osx)
    rs = ''
    for lc in lcs:
        rs += "'%s', '%s', '%s', '%s', '%s'\r\n" % (lc[28], lc[2], lc[9], lc[6], lc[14])
    return HttpResponse(rs)
    return wrender('raw.html', {'o': o}, request)

def ivr_cdr(request, ts_from, ts_to = 0):
    ts_from = int(ts_from)
    ts_to = int(ts_to)
    if ts_from >= 0 and ts_from <= (time.time() + 12000) and ts_to >= 0 and ts_to <= (time.time() + 12000):
        dt_from = datetime.datetime.fromtimestamp(ts_from)
        if ts_to:
            dt_to = datetime.datetime.fromtimestamp(ts_to)
        else:
            dt_to = datetime.datetime.today() + timedelta(days = 1)
        db = LcrSwitch.objects.filter(ip_addr = 'ivr.vs.ip.1.2.3.4')[0].get_db()
        q = "SELECT * FROM lcr_cdr WHERE switch_ip = 'ivr.vs.ip.1.2.3.4' AND dt_begin > '%s' AND dt_end < '%s' ORDER BY id DESC" % (dt_from.strftime('%Y-%m-%d %H:%M:%S'), dt_to.strftime('%Y-%m-%d %H:%M:%S'))
        db.query(q)
        r = db.store_result()
                o = r.fetch_row(maxrows = 0)
        rs = ''
        for os in o:
            rs += "%s,'%s','%s','%s','%s','%s','%s','%s','%s',%s\r\n" % (os[0], os[2], os[3], os[4], os[5], os[9], os[11], os[12], os[13], os[14])
        db.close()
        return HttpResponse(rs)
    else:
        return HttpResponse('WRONG TIMESTAMP')

def ivr_cdr_lastday(request):
    return ivr_cdr(request, int(time.time()) - 60*60*24, 0)

# Old-school, replaced by PGBouncer-based SQL Interfaces
def fs_dialplan(request):
    switch_ip = request.REQUEST['FreeSWITCH-IPv4']
    source_ip = request.REQUEST['Caller-Network-Addr']
    dialed_num = request.REQUEST['Caller-Destination-Number']
    # 1. Locate a Switch
    # TEST CHECK
    if source_ip == 'test.fs.ip.1.2.3.4':
        if re.match('^111(\d{5})', dialed_num):
            test_override = True
            test_dest = LcrDestination.objects.get(id = int(re.match('^111(\d{5})(\d*)', dialed_num).groups()[0]))
            test_dn = re.match('^111(\d{5})(\d*)', dialed_num).groups()[1]
            sip_data = 'sofia/external/%s%s@%s' % (test_dest.tech_prefix, test_dn, test_dest.ip_addr)
            e164 = LcrDestinationE164(code = '111')
            # REPLACE 666 WITH TEST DEAL ID
            return wrender('fs_dialplan.xml', {'e164': e164, 'sip_data': sip_data, 'deal_prefix': '', 'deal_id': 666}, request)
    switches = LcrSwitch.objects.filter(ip_addr = switch_ip)
    if len(switches):
        switch = switches[0]
        # 2. Locate a Customer
        customer_ips = LcrCustomerIp.objects.filter(ip_addr = source_ip, customer__switch = switch)
        if len(customer_ips):
            customer_ip = customer_ips[0]
            # 3. Locate a Deal
            deals = LcrDeal.objects.filter(buy_carrier = customer_ip.customer, is_active = 1)
            # TODO - INTERNAL PREFIX (DEAL)
            e164s = []
            e164_found = False
            test_override = False
            e164_deal_prefix = ''
            e164_deal_id = 0
            for deal in deals:
                for e164 in deal.destination.lcrdestinatione164_set.all():
                    e164s.append(e164)
            for i in range(len(dialed_num)):
                if (not e164_found) and (i != len(dialed_num)):
                    strip = len(dialed_num) - i
                    anal_e164 = dialed_num[0:strip]
                    for e164 in e164s:
                        deal_prefix = ''
                        deals = LcrDeal.objects.filter(buy_carrier = customer_ip.customer, destination = e164.destination)
                        if len(deals) == 1:
                            deal_id = deals[0].id
                            deal_prefix = deals[0].tech_prefix
                        if anal_e164 == deal_prefix + e164.code:
                            e164_found = True
                            e164_match = e164
                            e164_deal_prefix = deal_prefix
                            e164_deal_id = deal_id
            if e164_found:
                if e164_deal_prefix != '':
                    dialed_num = re.sub(e164_deal_prefix, '', dialed_num, 1)
                sip_data = 'sofia/external/%s%s@%s' % (e164_match.destination.tech_prefix, dialed_num, e164_match.destination.ip_addr)
                return wrender('fs_dialplan.xml', {'e164': e164_match, 'sip_data': sip_data, 'deal_prefix': e164_deal_prefix, 'deal_id': e164_deal_id}, request)
    return HttpResponse('404 NOT FOUND')

def register(request):
    if request.method == 'POST':
        f = LcrRegistrationForm(request.POST)
        if f.is_valid():
            reg = f.save(commit = False)
            reg.token = User.objects.make_random_password(length = 30)
            reg.save()
            return wrender('reg_sign.html', {'reg': reg}, request)
    else:
        f = LcrRegistrationForm()
    return wrender('reg_index.html', {'f': f}, request)

def register_sign(request):
    if request.method == 'POST':
        if request.POST['lrs_token']:
            token = request.POST['lrs_token']
            regs = LcrRegistration.objects.filter(token = token)
            if len(regs):
                reg = regs[0]
                if request.POST['lrs_sign']:
                    sign = request.POST['lrs_sign']
                else:
                    sign = ''
                if request.POST['lrs_yn']:
                    yn = int(request.POST['lrs_yn'])
                else:
                    yn = 0
                reg.sign_name = sign
                reg.sign_yn = yn
                reg.sign_agent = request.META['HTTP_USER_AGENT']
                reg.reg_ip = request.META['REMOTE_ADDR']
                reg.save()
                return wrender('reg_sign_ok.html', {'reg': reg}, request)
            else:
                return HttpResponseRedirect('/register/')
    else:
        return HttpResponseRedirect('/register/')

def register_check(request, str_token):
    regs = LcrRegistration.objects.filter(token = str_token)
    if len(regs):
        reg = regs[0]
        return wrender('reg_sign_status.html', {'reg': reg}, request)
    else:
        return HttpResponseRedirect('/register/')

def get_xml_val(str_key, str_xml):
    p = '<' + str_key + '>(.*?)<\/' + str_key + '>'
    rx = re.search(p, str_xml)
    if rx:
        return unquote(rx.groups()[0])
    else:
        return ''

# Replaced by direct SQL streams
def process_cdr(str_cdr):
    cdr = str_cdr
    direction = ''
    rx = re.search('<direction>(\w*?)<\/direction>', cdr)
    if rx:
            direction = rx.groups()[0]
    if direction != 'inbound' and get_xml_val('sip_local_network_addr', cdr) != 'inbound.fs.ip.1.2.3.4':
        return HttpResponse('NOT INBOUND - IGNORE')
    else:
        switch_ip = get_xml_val('sip_local_network_addr', cdr)
        source_ip = get_xml_val('sip_network_ip', cdr)
        source_dn = get_xml_val('sip_req_user', cdr)
        source_ani = get_xml_val('sip_from_user', cdr)
        source_codec = get_xml_val('sip_use_codec_name', cdr)
        rx = re.search('<application app_name="bridge" app_data="sofia\/external\/(\d*?)@(.*?)" app_stamp', cdr)
        if rx:
            dest_ip = rx.groups()[1]
            dest_dn = rx.groups()[0]
        else:
            dest_ip = ''
            dest_dn = ''
        dest_codec = source_codec
        hang_pcause = get_xml_val('proto_specific_hangup_cause', cdr)
        hang_scause = get_xml_val('hangup_cause', cdr)
        dt_begin = get_xml_val('start_stamp', cdr)
        dt_answer = get_xml_val('answer_stamp', cdr)
        dt_end = get_xml_val('end_stamp', cdr)
        if dt_answer == '':
            dt_answer = dt_begin
        if dt_end == '':
            dt_end = dt_begin
        duration = get_xml_val('billsec', cdr)
        deal_id = '0'
        rx = re.search('app_data="did=(\d*?)"', cdr)
        if rx:
            deal_id = rx.groups()[0]
        # ROBO-CALLER
        if deal_id == '0' and switch_ip == 'robo.agent.ip.1.2.3.4':
            rx = re.search('<channel_name>sofia\/external\/(\d*?)%40(.*?)<', cdr)
            if rx:
                dest_ip = rx.groups()[1]
                dest_dn = rx.groups()[0]
            # Replace 666 with Robo Deal ID
            deal_id = '666'
        if duration == '':
            duration = 0
        call_uuid = get_xml_val('call_uuid', cdr)
        db = LcrSwitch.objects.filter(ip_addr = 'db.ip.1.2.3.4')[0].get_db()
        q = "INSERT INTO lcr_cdr_%s%s (switch_ip, source_ip, source_dn, source_ani, source_codec, dest_ip, dest_dn, dest_codec, hang_pcause, hang_scause, dt_begin, dt_answer, dt_end, duration, deal_id, call_uuid) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', %s, %s, '%s')" % (dt_begin[0:4], dt_begin[5:7], switch_ip, source_ip, source_dn, source_ani, source_codec, dest_ip, dest_dn, dest_codec, hang_pcause, hang_scause, dt_begin, dt_answer, dt_end, duration, deal_id, call_uuid)
        try:
            db.query(q)
        except OperationalError:
            return HttpResponseNotFound('NO: ' + q)
        db.close()
        return HttpResponse('OK')

def test_cdr(request):
    return wrender('cdr_test.html', {}, request)

def fs_cdr(request):
    return process_cdr(request.REQUEST['cdr'])

def add_recon(request):
    if request.method == 'POST':
        f = ReconForm(request.POST, request.FILES)
        if f.is_valid():
            r = f.save(commit = False)
            r.author = request.user
            r.save()
            r.set_status(0)
    else:
        f = ReconForm()
    recons = LcrRecon.objects.filter(author = request.user).order_by('-id')
    return wrender('add_recon.html', {'f': f, 'recons': recons}, request)

def res_recon(request, rid):
    rid = int(rid)
    r = LcrRecon.objects.get(id = rid)
    cdrs_diff = LcrReconDispute.objects.filter(recon = r, type__gte = 3, type__lte =4).order_by('cdr_lcr__cdr_start')
    cdrs_miss_lcr = LcrReconDispute.objects.filter(recon = r, type = 1).order_by('cdr_lcr__cdr_start')
    cdrs_miss_ext = LcrReconDispute.objects.filter(recon = r, type = 2).order_by('cdr_ext__cdr_start')
    dt_lcr_begin = LcrReconCDR.objects.filter(recon = r, party = 1).order_by('cdr_start')[0].cdr_start
    dt_ext_begin = LcrReconCDR.objects.filter(recon = r, party = 2).order_by('cdr_start')[0].cdr_start
    dt_lcr_end = LcrReconCDR.objects.filter(recon = r, party = 1).order_by('-cdr_start')[0].cdr_start
    dt_ext_end = LcrReconCDR.objects.filter(recon = r, party = 2).order_by('-cdr_start')[0].cdr_start
    cdrs_over = LcrReconOverlap.objects.filter(recon = r).order_by('cdr_ext_1__cdr_start')
    mlcr = 0
    mext = 0
    for cdr in cdrs_miss_lcr:
        mlcr += cdr.cdr_lcr.cdr_duration
    for cdr in cdrs_miss_ext:
        mext += cdr.cdr_ext.cdr_duration
    return wrender('res_recon.html', {'r': r, 'cdrs_diff': cdrs_diff, 'cdrs_miss_lcr': cdrs_miss_lcr, 'cdrs_miss_ext': cdrs_miss_ext, 'mlcr': mlcr, 'mext': mext, 'dt_lcr_begin': dt_lcr_begin, 'dt_ext_begin': dt_ext_begin, 'dt_lcr_end': dt_lcr_end, 'dt_ext_end': dt_ext_end, 'cdrs_over': cdrs_over, 'len_overmacs': len(r.get_overmacs())}, request)

def rr_csv(request, rid, type):
    r = LcrRecon.objects.get(id = int(rid))
    ret = ''
    c = ';'
    if type == 'disputed':
        ret += 'lcr_cdr_id%sext_cdr_id%slcr_datetime%sext_datetime%slcr_number%slcr_duration%sext_duration%sext_number%sdispute\r\n' % (c, c, c, c, c, c, c, c)
        for d in LcrReconDispute.objects.filter(recon = r, type__gte = 3, type__lte = 4):
            ret += '%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s\r\n' % (str(d.cdr_lcr.id), c, str(d.cdr_ext.id), c, d.cdr_lcr.cdr_start.isoformat(), c, d.cdr_ext.cdr_start.isoformat(), c, d.cdr_lcr.cdr_number, c, str(d.cdr_lcr.cdr_duration), c, str(d.cdr_ext.cdr_duration), c, d.cdr_ext.cdr_number, c, d.get_type_display())
    elif type == 'misslcr':
        ret += 'lcr_cdr_id%slcr_datetime%slcr_number%slcr_duration%sdispute\r\n' % (c, c, c, c)
        for d in LcrReconDispute.objects.filter(recon = r, type = 1):
            ret += '%s%s%s%s%s%s%s%s%s\r\n' % (str(d.cdr_lcr.id), c, d.cdr_lcr.cdr_start.isoformat(), c, d.cdr_lcr.cdr_number, c, str(d.cdr_lcr.cdr_duration), c, d.get_type_display())
    elif type == 'missext':
        ret += 'ext_cdr_id%sext_datetime%sext_number%sext_duration%sdispute\r\n' % (c, c, c, c)
        for d in LcrReconDispute.objects.filter(recon = r, type = 2):
            ret += '%s%s%s%s%s%s%s%s%s\r\n' % (str(d.cdr_ext.id), c, d.cdr_ext.cdr_start.isoformat(), c, d.cdr_ext.cdr_number, c, str(d.cdr_ext.cdr_duration), c, d.get_type_display())
    elif type == 'overlap':
        ret += 'a_cdr_id%sa_datetime%sa_number%sa_duration%sb_cdr_id%sb_datetime%sb_number%sb_duration%sdispute\r\n' % (c, c, c, c, c, c, c, c)
        for d in LcrReconOverlap.objects.filter(recon = r):
            ret += '%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%sOverlapped Call\r\n' % (str(d.cdr_ext_1.id), c, d.cdr_ext_1.cdr_start.isoformat(), c, d.cdr_ext_1.cdr_number, c, str(d.cdr_ext_1.cdr_duration), c, str(d.cdr_ext_2.id), c, d.cdr_ext_2.cdr_start.isoformat(), c, d.cdr_ext_2.cdr_number, c, str(d.cdr_ext_2.cdr_duration), c)
    elif type == 'overbill':
        ret += 'ext_cdr_id%sext_datetime%sext_duration%sext_number%sdispute\r\n' % (c, c, c, c)
        for d in r.get_overmacs():
            ret += '%s%s%s%s%s%s%s%sCall Overbilled\r\n' % (str(d.id), c, d.cdr_start.isoformat(), c, int(d.cdr_duration), c, d.cdr_number, c)
    return HttpResponse(ret, 'text/csv')

def chart_rr(request, rid, ctype):
    rid = int(rid)
    ctype = int(ctype)
    r = LcrRecon.objects.get(id = rid)
    chart = Drawing(width = 200, height = 25)
    chart.add(VerticalBarChart(), name = 'chart')
    ch_data = []
    ch_names = []
    hss = LcrReconResultsHour.objects.filter(recon = r).order_by('date', 'hour')
    for hs in hss:
        if ctype == 10:
            ch_data.append(hs.lcr_calls)
        if ctype == 11:
            ch_data.append(hs.lcr_secs)
        if ctype == 12:
            ch_data.append(hs.lcr_unmatched)
        if ctype == 20:
            ch_data.append(hs.ext_calls)
        if ctype == 21:
            ch_data.append(hs.ext_secs)
        if ctype == 22:
            ch_data.append(hs.ext_unmatched)
        if ctype == 30:
            ch_data.append(hs.diff_calls)
    chart.chart.data = [ch_data]
    chart.chart.x = 0
    chart.chart.y = 0
    chart.chart.width = chart.width
    chart.chart.height = chart.height
    chart.chart.bars[0].fillColor = Color(0.98, 0.42, 0.0)
    bret = chart.asString('gif')
    return HttpResponse(bret, 'image/gif')

def chart_mac(request, rid):
    rid = int(rid)
    r = LcrRecon.objects.get(id = rid)
    distros = LcrReconACDDistro.objects.filter(recon = r, acd_length__lte = r.get_mac()).order_by('acd_length')
    chart = Drawing(width = 200, height = 25)
    chart.add(VerticalBarChart(), name = 'chart')
    ch_data = []
    ch_names = []
    for distro in distros:
        ch_data.append(distro.acd_number)
    chart.chart.data = [ch_data]
    chart.chart.x = 0
    chart.chart.y = 0
    chart.chart.width = chart.width
    chart.chart.height = chart.height
    chart.chart.bars[0].fillColor = Color(0.98, 0.42, 0.0)
    bret = chart.asString('gif')
    return HttpResponse(bret, 'image/gif')


def chart_switch(request, str_sid):
    sid = int(str_sid)
    switch = LcrSwitch.objects.get(id = sid)
    hours = LcrStatSwitchHour.objects.filter(switch = switch).order_by('date', 'hour')
    chart = Drawing(width = 570, height = 100)
    chart.add(VerticalBarChart(), name = 'chart')
    chart.add(String(200, 180, ''), name = 'title')
    chart.title.fontName = 'Helvetica'
    ch_data = []
    ch_names = []
    for hour in hours:
        ch_data.append(hour.seconds)
        ch_names.append(hour.date.isoformat())
    ch_data.reverse()
    ch_names.reverse()
    chart.chart.data = [ch_data]
    chart.chart.x = 30
    chart.chart.y = 20
    chart.chart.width = chart.width - 40
    chart.chart.height = chart.height - 20
    chart.chart.categoryAxis.categoryNames = ch_names
    chart.chart.valueAxis.valueMin = 0
    chart.chart.bars[0].fillColor = Color(0, 0.4, 0.6)
    bret = chart.asString('gif')
    return HttpResponse(bret, 'image/gif')

def chart_acd(request, str_did):
    did = int(str_did)
    deal = LcrDeal.objects.get(id = did)
    stats = LcrStatDailyUpdate.objects.filter(deal = deal).order_by('-date')[:7]
    chart = Drawing(width = 570, height = 100)
    chart.add(VerticalBarChart(), name = 'chart')
    chart.add(String(200, 180, ''), name = 'title')
    chart.title.fontName = 'Helvetica'
    ch_data = []
    ch_names = []
    for stat in stats:
        ch_data.append(stat.acd)
        ch_names.append(stat.date.isoformat())
    ch_data.reverse()
    ch_names.reverse()
    chart.chart.data = [ch_data]
    chart.chart.x = 30
    chart.chart.y = 20
    chart.chart.width = chart.width - 40
    chart.chart.height = chart.height - 20
    chart.chart.categoryAxis.categoryNames = ch_names
    chart.chart.valueAxis.valueMin = 0
    chart.chart.bars[0].fillColor = Color(0, 0.4, 0.6)
    bret = chart.asString('gif')
    return HttpResponse(bret, 'image/gif')

def chart_asr(request, str_did):
    did = int(str_did)
    deal = LcrDeal.objects.get(id = did)
    stats = LcrStatDailyUpdate.objects.filter(deal = deal).order_by('-date')[:7]
    chart = Drawing(width = 570, height = 100)
    chart.add(VerticalBarChart(), name = 'chart')
    chart.add(String(200, 180, ''), name = 'title')
    chart.title.fontName = 'Helvetica'
    ch_data = []
    ch_names = []
    for stat in stats:
        ch_data.append(stat.asr())
        ch_names.append(stat.date.isoformat())
    ch_data.reverse()
    ch_names.reverse()
    chart.chart.data = [ch_data]
    chart.chart.x = 30
    chart.chart.y = 20
    chart.chart.width = chart.width - 40
    chart.chart.height = chart.height - 20
    chart.chart.categoryAxis.categoryNames = ch_names
    chart.chart.valueAxis.valueMin = 0
    chart.chart.bars[0].fillColor = Color(0.7, 0, 0)
    bret = chart.asString('gif')
    return HttpResponse(bret, 'image/gif')

def chart_min(request, str_did):
    did = int(str_did)
    deal = LcrDeal.objects.get(id = did)
    stats = LcrStatDailyUpdate.objects.filter(deal = deal).order_by('-date')[:7]
    chart = Drawing(width = 570, height = 100)
    chart.add(VerticalBarChart(), name = 'chart')
    chart.add(String(200, 180, ''), name = 'title')
    chart.title.fontName = 'Helvetica'
    ch_data = []
    ch_names = []
    for stat in stats:
        ch_data.append(stat.minutes())
        ch_names.append(stat.date.isoformat())
    ch_data.reverse()
    ch_names.reverse()
    chart.chart.data = [ch_data]
    chart.chart.x = 30
    chart.chart.y = 20
    chart.chart.width = chart.width - 40
    chart.chart.height = chart.height - 20
    chart.chart.categoryAxis.categoryNames = ch_names
    chart.chart.valueAxis.valueMin = 0
    chart.chart.bars[0].fillColor = Color(0.15, 0.48, 0)
    bret = chart.asString('gif')
    return HttpResponse(bret, 'image/gif')

def chart_stat(request, str_type, str_did):
    did = int(str_did)
    deal = LcrDeal.objects.get(id = did)
    stats = LcrStatH.objects.filter(deal = deal).order_by('-dt_when')[:(24*30)]
    chart = Drawing(width = 700, height = 120)
    chart.add(VerticalBarChart(), name = 'chart')
    chart.add(String(200, 180, ''), name = 'title')
    chart.title.fontName = 'Helvetica'
    ch_data = []
    ch_names = []
    i = 0
    for stat in stats:
        if str_type == 'asr':
            ch_data.append(stat.asr())
        elif str_type == 'acd':
            ch_data.append(stat.acd())
        elif str_type == 'chans':
            ch_data.append(stat.chans())
        elif str_type == 'vol':
            ch_data.append(stat.minutes())
        else:
            ch_data.append(0)
        if not (i % (7 * 24)):
            ch_names.append('%02d-%02d' % (stat.dt_when.month, stat.dt_when.day))
        else:
            ch_names.append('')
        i += 1
    ch_data.reverse()
    ch_names.reverse()
    chart.chart.data = [ch_data]
    chart.chart.x = 30
    chart.chart.y = 20
    chart.chart.width = chart.width - 50
    chart.chart.height = chart.height - 30
    chart.chart.categoryAxis.categoryNames = ch_names
    chart.chart.categoryAxis.visibleTicks = 0
    chart.chart.valueAxis.valueMin = 0
    chart.chart.bars.fillColor = Color(0, 0.4, 0.6)
    bret = chart.asString('gif')
    return HttpResponse(bret, 'image/gif')

@login_required
def json_switch(request, str_sid, str_points):
    sid = int(str_sid)
    points = int(str_points)
    switch = LcrSwitch.objects.get(id = sid)
    hour_objs = LcrStatSwitchHour.objects.filter(switch = switch).order_by('-date', '-hour')[:points]
    for hour in hour_objs:
        hour.channels = round(hour.seconds / 3600)
    hour_arr = []
    for hour in hour_objs:
        hour_arr.append(hour)
    hour_arr.reverse()
    hour_arr.pop()
    l_step = round(points / 2)
    step = round(points / 6)
    return wrender('switch.json', {'hours': hour_arr, 'switch': switch, 'step': step, 'l_step': l_step}, request)

def genStatTotal(deal):
    st = LcrStatTotalUpdate(deal = deal)
    st.calls_ok = 0
    st.calls_fail = 0
    st.seconds = 0
    st.acd = 0
    #
    dailies = LcrStatDailyUpdate.objects.filter(deal = deal)
    if len(dailies):
        for daily in dailies:
            st.seconds += daily.seconds
            st.calls_ok += daily.calls_ok
            st.calls_fail += daily.calls_fail
    #
    dds = LcrStatDailyDelta.objects.filter(deal = deal).order_by('-id')
    if len(dds):
        dd = dds[0]
        st.seconds += dd.seconds
        st.calls_ok += dd.calls_ok
    #
    return st

@login_required
@staff_member_required
def invoice_add(request, str_cid):
    if len(LcrCarrier.objects.filter(partner = request.user.get_profile().get_partner().partner, id = int(str_cid))):
        carrier = LcrCarrier.objects.get(partner = request.user.get_profile().get_partner().partner, id = int(str_cid))
        if request.method == 'POST':
            form = LcrInvoiceForm(request.POST)
            if form.is_valid():
                inv = form.save(commit = False)
                inv.carrier = carrier
                inv.partner = request.user.get_profile().get_partner().partner
                inv.status = 1
                inv.direction = 1
                inv.save()
                return HttpResponseRedirect('/invoice/edit/%d/' % inv.id)
        form = LcrInvoiceForm()
        return wrender('invoice_add.html', {'carrier': carrier, 'form': form}, request)
    else:
        return HttpResponseRedirect('/')

def invoice_check_own(request, str_iid):
    if len(LcrInvoice.objects.filter(partner = request.user.get_profile().get_partner().partner, id = int(str_iid))):
        return LcrInvoice.objects.get(partner = request.user.get_profile().get_partner().partner, id = int(str_iid))
    else:
        return False

def invoice_get_deal_stats(invoice, deal):
    ret = {}
    sum_seconds = 0
    sum_cost = 0.0
    for stat in LcrStatH.objects.filter(deal = deal, dt_when__gte = invoice.dt_from, dt_when__lte = invoice.dt_to):
        sum_seconds += stat.seconds
        sum_cost += 1.0 * (stat.seconds / 60) * float(stat.ppm)
    ret['sum_cost'] = sum_cost
    ret['sum_seconds'] = sum_seconds
    ret['sum_minutes'] = 1.0 * sum_seconds / 60
    if ret['sum_minutes']:
        ret['ppm'] = sum_cost / ret['sum_minutes']
    else:
        ret['ppm'] = '0.000'
    return ret

def invoice_available_deals(request, invoice):
    inv_deals = []
    partner = request.user.get_profile().get_partner().partner
    deals = LcrDeal.objects.filter(is_active = 1, partner = partner, buy_carrier__carrier = invoice.carrier)
    for deal in deals:
        addme = True
        if len(LcrInvoicePosition.objects.filter(invoice = invoice, deal = deal)):
            addme = False
        if len(LcrInvoicePosition.objects.filter(deal = deal, invoice__dt_from__lte = invoice.dt_from, invoice__dt_to__gte = invoice.dt_from)):
            addme = False
        if len(LcrInvoicePosition.objects.filter(deal = deal, invoice__dt_from__lte = invoice.dt_to, invoice__dt_to__gte = invoice.dt_to)):
            addme = False
        if len(LcrInvoicePosition.objects.filter(deal = deal, invoice__dt_from__gte = invoice.dt_from, invoice__dt_to__lte = invoice.dt_to)):
            addme = False
        if addme:
            inv_deals.append(deal)
    return inv_deals

@login_required
@staff_member_required
def ajx_invoice_available_deals(request, str_iid):
    if invoice_check_own(request, str_iid):
        invoice = invoice_check_own(request, str_iid)
        inv_deals = invoice_available_deals(request, invoice)
        for deal in inv_deals:
            deal.stats = invoice_get_deal_stats(invoice, deal)
        return wrender('ajx_invoice_available_deals.html', {'deals': inv_deals}, request)
    else:
        return HttpResponse('ERR404')

@login_required
@staff_member_required
def ajx_invoice_add_deal(request, str_iid, str_did):
    if invoice_check_own(request, str_iid) and len(LcrDeal.objects.filter(id = int(str_did), partner = request.user.get_profile().get_partner().partner)):
        partner = request.user.get_profile().get_partner().partner
        invoice = invoice_check_own(request, str_iid)
        deal = LcrDeal.objects.get(id = int(str_did))
        if deal in invoice_available_deals(request, invoice):
            stats = invoice_get_deal_stats(invoice, deal)
            pos = LcrInvoicePosition(invoice = invoice, deal = deal)
            pos.ppm = '%.4f' % float(stats['ppm'])
            pos.save()
            return HttpResponse('OK')
        else:
            return HttpResponse('ERREXISTS')
    else:
        return HttpResponse('ERR404')

@login_required
@staff_member_required
def ajx_invoice_details(request, str_iid):
    if invoice_check_own(request, str_iid):
        ret = {}
        invoice = invoice_check_own(request, str_iid)
        positions = LcrInvoicePosition.objects.filter(invoice = invoice)
        return wrender('ajx_invoice_details.html', {'positions': positions, 'invoice': invoice}, request)
    else:
        return HttpResponse('ERR404')

def invoices_partner_period(partner, dt_begin, dt_end):
    return LcrInvoice.objects.filter((Q(dt_from__lte = dt_begin, dt_to__gte = dt_begin) | Q(dt_from__lte = dt_end, dt_to__gte = dt_end) | Q(dt_from__gte = dt_begin, dt_to__lte = dt_end)), partner = partner)

@login_required
@staff_member_required
def ajx_invoices_month(request, str_year, str_month):	# dt_end INCLUSIVE!!!
    dt_begin = datetime.datetime(int(str_year), int(str_month), 1, 0, 0, 0)
    dt_end = dt_begin + relativedelta(months = 1) - timedelta(seconds = 1)
    invs = invoices_partner_period(request.user.get_profile().get_partner().partner, dt_begin, dt_end)
    deals = LcrDeal.objects.filter(partner = request.user.get_profile().get_partner().partner, is_active = 1)
    poss = []
    for inv in invs:
        for pos in inv.lcrinvoiceposition_set.all():
            poss.append(pos)
    return wrender('ajx_invoices_month.html', {'positions': poss, 'invoices': invs, 'deals': deals}, request)

@login_required
@staff_member_required
def invoice_edit(request, str_iid):
    if len(LcrInvoice.objects.filter(partner = request.user.get_profile().get_partner().partner, id = int(str_iid))):
        invoice = LcrInvoice.objects.get(partner = request.user.get_profile().get_partner().partner, id = int(str_iid))
        return wrender('invoice_edit.html', {'invoice': invoice, 'partner': request.user.get_profile().get_partner().partner}, request)
    else:
        return HttpResponseRedirect('/')

@login_required
@staff_member_required
def invoice_pdf(request, str_iid):
    if len(LcrInvoice.objects.filter(partner = request.user.get_profile().get_partner().partner, id = int(str_iid))):
        invoice = LcrInvoice.objects.get(partner = request.user.get_profile().get_partner().partner, id = int(str_iid))
        positions = LcrInvoicePosition.objects.filter(invoice = invoice)
        pdfmetrics.registerFont(TTFont('qpn', CONF_BASEDIR + '/ttf/qp_normal.ttf'))
        pdfmetrics.registerFont(TTFont('qpb', CONF_BASEDIR + '/ttf/qp_bold.ttf'))
        buffer = StringIO()
        stylesheet = getSampleStyleSheet()
        stn = stylesheet['Normal']
        stn.fontSize = 10
        stn.fontName = 'qpn'
        stn.leftIndent = 30
        stn.rightIndent = 30
        p = canvas.Canvas(buffer)
        #
        #p.setStrokeColor(Color(0.8, 0.8, 0.8))
        p.setFont('qpn', 7)
        path = p.beginPath()
        path.moveTo(30, 740)
        path.lineTo(560, 740)
        path.close()
        p.line(30, 40, 560, 40)
        p.drawString(160, 32, 'Document generated using Tesserakt LCR - v2.018b - http://www.tesserakt.eu/lcr')
        p.setFont('qpn', 10)
        p.drawPath(path)
        py = 810
        px = 50
        par = Paragraph('<para align="right">' + invoice.partner.details.replace('\n', '<br/>') + '</para>', stn)
        w, h = par.wrap(300, 50)
        par.drawOn(p, 285, py - h)
        py = 720
        if invoice.partner.logo:
            p.drawImage(CONF_BASEDIR + '/logos/' + invoice.partner.logo, 30, 750)
        p.drawString(480, py, 'Date: ' + invoice.dt_when.strftime('%Y-%m-%d'))
        par = Paragraph('<u>Customer:</u><br/><br/>' + invoice.carrier.name + '<br/>' + invoice.carrier.address.replace('\n', '<br/>'), stn)
        w, h = par.wrap(300, 80)
        par.drawOn(p, 0, py - h)
        p.setFont('qpb', 18)
        py = 690
        p.drawString(280, py, 'Invoice No.')
        py -= 25
        p.drawString(280, py, invoice.number())
        p.setFont('qpn', 10)
        py -= 25
        p.drawString(280, py, 'Period: ' + invoice.dt_from.strftime('%Y-%m-%d') + ' - ' + invoice.dt_to.strftime('%Y-%m-%d'))
        py -= 35
        bc = code39.Extended39(invoice.number(), barWidth = .5, barHeight = 10)
        bc.drawOn(p, 265, py)
        py = 550
        p.drawString(40, py, 'DEAL')
        p.drawString(80, py, 'DESTINATION')
        p.drawString(320, py, 'PRICE')
        p.drawString(400, py, 'MINUTES')
        p.drawString(490, py, 'VALUE')
        py -= 5
        p.setLineWidth(.3)
        p.line(30, py, 550, py)
        p.setStrokeColor(Color(0.8, 0.8, 0.8))
        for pos in positions:
            py -= 13
            p.drawString(40, py, str(pos.deal.id))
            p.drawString(80, py, pos.deal.destination.name)
            p.drawString(320, py, '$%.4f' % pos.ppm)
            par = Paragraph('<para align="right">' + str(int(pos.sum_minutes())) + '</para>', stn)
            w, h = par.wrap(70, 15)
            par.drawOn(p, 400, py - 5)
            par = Paragraph('<para align="right">$%.2f</para>' % pos.sum_cost(), stn)
            w, h = par.wrap(140, 15)
            par.drawOn(p, 430, py - 5)
            py -= 7
            p.line(30, py, 550, py)
        py -= 13
        p.drawString(400, py, 'Sub Total:')
        par = Paragraph('<para align="right">$%.2f</para>' % invoice.sum_cost(), stn)
        w, h = par.wrap(140, 15)
        par.drawOn(p, 430, py - 5)
        py -= 20
        p.drawString(400, py, 'Tax:')
        par = Paragraph('<para align="right">%d %%</para>' % invoice.tax, stn)
        w, h = par.wrap(140, 15)
        par.drawOn(p, 430, py - 5)
        py -= 20
        p.setFont('qpb', 12)
        p.drawString(400, py, 'Total:')
        stn.fontSize = 12
        stn.fontName = 'qpb'
        par = Paragraph('<para align="right">$%.2f</para>' % invoice.total(), stn)
        w, h = par.wrap(140, 15)
        par.drawOn(p, 430, py - 3)
        stn.fontSize = 10
        stn.fontName = 'qpn'
        p.setFont('qpn', 10)
        p.drawString(80, py, 'Due Date: ' + invoice.due_date().strftime('%Y-%m-%d'))
        if invoice.carrier.address.find('United Kingdom') and invoice.partner.details.find('United Kingdom'):
            # Hook up your favorite forex here
            EXR = 1.6
            vat_gbp = ((1.00 * invoice.tax / 100) * invoice.sum_cost()) / EXR
            py -= 50
            p.drawString (120, py, 'Note: The value of VAT = GBP %.2f, exchange rate: 1 GBP = %.2f USD' % (vat_gbp, EXR))
        p.showPage()
        p.save()
        pdf = buffer.getvalue()
        buffer.close()
        if os.path.isfile(CONF_BASEPDF + '/inv_' + str(invoice.id) + '.pdf'):
             os.unlink(CONF_BASEPDF + '/inv_' + str(invoice.id) + '.pdf')
        f = open(CONF_BASEPDF + '/inv_' + str(invoice.id) + '.pdf', 'w')
        f.write(pdf)
        f.close()
        res = HttpResponse(pdf, 'application/pdf')
        res['Content-Disposition'] = 'attachment; filename=inv_%d.pdf' % invoice.id
        return res
    else:
        return HttpResponseRedirect('/')

@login_required
@staff_member_required
def invoice_delete(request, str_iid):
    if len(LcrInvoice.objects.filter(partner = request.user.get_profile().get_partner().partner, id = int(str_iid))):
        invoice = LcrInvoice.objects.get(partner = request.user.get_profile().get_partner().partner, id = int(str_iid))
        invoice.delete()
        return HttpResponseRedirect('/bill/month/')
    else:
        return HttpResponseRedirect('/')

@login_required
@staff_member_required
def ajx_invoice_rem_pos(request, str_pid):
    if len(LcrInvoicePosition.objects.filter(invoice__partner = request.user.get_profile().get_partner().partner, id = int(str_pid))):
        pos = LcrInvoicePosition.objects.get(id = int(str_pid))
        pos.delete()
        return HttpResponse('OK')
    else:
        return HttpResponse('ERR404')

@login_required
@staff_member_required
def ajx_invoice_edit_pos(request, str_pid, str_ppm):
    if len(LcrInvoicePosition.objects.filter(invoice__partner = request.user.get_profile().get_partner().partner, id = int(str_pid))):
        pos = LcrInvoicePosition.objects.get(id = int(str_pid))
        pos.ppm = str(float(int(str_ppm) * 1.0 / 10000))
        pos.save()
        return HttpResponse('OK')
    else:
        return HttpResponse('ERR404')

@login_required
@staff_member_required
def ajx_invoice_edit_tax(request, str_iid, str_tax):
    if len(LcrInvoice.objects.filter(partner = request.user.get_profile().get_partner().partner, id = int(str_iid))):
        invoice = LcrInvoice.objects.get(partner = request.user.get_profile().get_partner().partner, id = int(str_iid))
        invoice.tax = int(str_tax)
        invoice.save()
        return HttpResponse('OK')
    else:
        return HttpResponse('ERR404')

@login_required
@staff_member_required
def bill_month(request):
    carriers = LcrCarrier.objects.filter(partner = request.user.get_profile().get_partner().partner)
    return wrender('bill_month.html', {'carriers': carriers}, request)

@login_required
@staff_member_required
def retail_services(request):
    services = LcrRetailService.objects.filter(partner = request.user.get_profile().get_partner().partner)
    return wrender('retail_services.html', {'services': services}, request)

@login_required
@staff_member_required
def retail_edit_service(request, sid):
    sid = int(sid)
    services = LcrRetailService.objects.filter(partner = request.user.get_profile().get_partner().partner, id = sid)
    mform = RetailServiceModDestinationForm()
    if len(services):
        service = services[0]
    else:
        return HttpResponseRedirect('/retail/services/')
    if request.method == 'POST':
        sform = RetailServiceForm(request.POST, instance = service, prefix = 'sf')
        if service.type == 1:
            spform = RetailSPLandlineForm(request.POST, instance = service.get_profile(), prefix = 'spf')
        if sform.is_valid() and spform.is_valid():
            sform.save()
            spform.save()
            return wrender('retail_edit_service.html', {'service': service, 'sform': sform, 'spform': spform, 'mform': mform}, request)
    sform = RetailServiceForm(instance = service, prefix = 'sf')
    if service.type == 1:
        spform = RetailSPLandlineForm(instance = service.get_profile(), prefix = 'spf')
    return wrender('retail_edit_service.html', {'service': service, 'sform': sform, 'spform': spform, 'mform': mform}, request)

@login_required
@staff_member_required
def retail_add_service(request, tid):
    tid = int(tid)
    if request.method == 'POST':
        sform = RetailServiceForm(request.POST, prefix = 'sf')
        if tid == 1:
            spform = RetailSPLandlineForm(request.POST, prefix = 'spf')
        if sform.is_valid() and spform.is_valid():
            service = sform.save(commit = False)
            service.partner = request.user.get_profile().get_partner().partner
            service.type = tid
            service.save()
            service_profile = spform.save(commit = False)
            service_profile.service = service
            service_profile.save()
            return HttpResponseRedirect('/retail/services/')
    sform = RetailServiceForm(prefix = 'sf')
    if tid == 1:
        spform = RetailSPLandlineForm(prefix = 'spf')
    return wrender('retail_add_service.html', {'tid': tid, 'sform': sform, 'spform': spform}, request)

@login_required
@staff_member_required
def retail_tariffs(request):
    tariffs = LcrRetailTariffPhone.objects.filter(partner = request.user.get_profile().get_partner().partner)
    return wrender('retail_tariffs.html', {'tariffs': tariffs}, request)

@login_required
@staff_member_required
def retail_edit_tariff(request, tid):
    tid = int(tid)
    tariffs = LcrRetailTariffPhone.objects.filter(partner = request.user.get_profile().get_partner().partner, id = tid)
    if len(tariffs):
        tariff = tariffs[0]
    else:
        return HttpResponseRedirect('/retail/tariffs/')
    rates = tariff.lcrretailratephone_set.all()
    rform = RetailRatePhoneForm(prefix = 'rf')
    if request.method == 'POST':
        tform = RetailTariffPhoneForm(request.POST, instance = tariff, prefix = 'tf')
        if tform.is_valid():
            tform.save()
            return wrender('retail_edit_tariff.html', {'tariff': tariff, 'rates': rates, 'rform': rform, 'tform': tform}, request)
    tform = RetailTariffPhoneForm(instance = tariff, prefix = 'tf')
    return wrender('retail_edit_tariff.html', {'tariff': tariff, 'rates': rates, 'rform': rform, 'tform': tform}, request)

@login_required
@staff_member_required
def retail_add_tariff(request):
    if request.method == 'POST':
        tform = RetailTariffPhoneForm(request.POST)
        if tform.is_valid():
            tariff = tform.save(commit = False)
            tariff.partner = request.user.get_profile().get_partner().partner
            tariff.save()
            return HttpResponseRedirect('/retail/edit_tariff/' + str(tariff.id) + '/')
    tform = RetailTariffPhoneForm()
    return wrender('retail_add_tariff.html', {'tform': tform}, request)

@login_required
@staff_member_required
def retail_add_rate(request, tid):
    tid = int(tid)
    tariffs = LcrRetailTariffPhone.objects.filter(partner = request.user.get_profile().get_partner().partner, id = tid)
    if len(tariffs):
        tariff = tariffs[0]
    else:
        return HttpResponseRedirect('/retail/tariffs/')
    if request.method == 'POST':
        rform = RetailRatePhoneForm(request.POST, prefix = 'rf')
        if rform.is_valid():
            rate = rform.save(commit = False)
            rate.tariff = tariff
            rate.save()
    return HttpResponseRedirect('/retail/edit_tariff/' + str(tariff.id) + '/')

@login_required
@staff_member_required
def retail_del_rate(request, rid):
    rid = int(rid)
    rates = LcrRetailRatePhone.objects.filter(tariff__partner = request.user.get_profile().get_partner().partner, id = rid)
    if len(rates):
        rate = rates[0]
    else:
        return HttpResponseRedirect('/retail/tariffs/')
    tariff = rate.tariff
    rate.delete()
    return HttpResponseRedirect('/retail/edit_tariff/' + str(tariff.id) + '/')

@login_required
@staff_member_required
def retail_destinations(request):
    destinations = LcrRetailDestination.objects.filter(partner = request.user.get_profile().get_partner().partner)
    return wrender('retail_destinations.html', {'destinations': destinations}, request)

@login_required
@staff_member_required
def retail_edit_destination(request, did):
    did = int(did)
    destinations = LcrRetailDestination.objects.filter(partner = request.user.get_profile().get_partner().partner, id = did)
    if len(destinations):
        destination = destinations[0]
    else:
        return HttpResponseRedirect('/retail/destinations/')
    if request.method == 'POST':
        dform = RetailDestinationForm(request.POST, instance = destination)
        if dform.is_valid():
            dform.save()
            return wrender('retail_edit_destination.html', {'destination': destination, 'dform': dform}, request)
    dform = RetailDestinationForm(instance = destination)
    return wrender('retail_edit_destination.html', {'destination': destination, 'dform': dform}, request)

@login_required
@staff_member_required
def retail_add_destination(request):
    if request.method == 'POST':
        dform = RetailDestinationForm(request.POST)
        if dform.is_valid():
            destination = dform.save(commit = False)
            destination.partner = request.user.get_profile().get_partner().partner
            destination.save()
            return HttpResponseRedirect('/retail/destinations/')
    dform = RetailDestinationForm()
    return wrender('retail_add_destination.html', {'dform': dform}, request)

@login_required
@staff_member_required
def retail_add_destination_e164(request, strdid):
    did = int(strdid)
    ds = LcrRetailDestination.objects.filter(id = did, partner = request.user.get_profile().get_partner().partner)
    if len(ds):
        d = ds[0]
    else:
        return HttpResponseRedirect('/retail/destinations/')
    codes = re.findall('(\d*)', request.POST['f_codes'])
    for code in codes:
        if len(code):
            e164 = LcrRetailDestinationPrefix(destination = d)
            e164.prefix = code
            e164.save()
    return HttpResponseRedirect('/retail/edit_destination/' + str(d.id) + '/')

@login_required
@staff_member_required
def retail_delete_destination_e164(request, streid):
    eid = int(streid)
    e164s = LcrRetailDestinationPrefix.objects.filter(id = eid, destination__partner = request.user.get_profile().get_partner().partner)
    if len(e164s):
        e164 = e164s[0]
    else:
        return HttpResponseRedirect('/retail/destinations/')
    did = e164.destination.id
    e164.delete()
    return HttpResponseRedirect('/retail/edit_destination/' + str(did) + '/')

@login_required
@staff_member_required
def retail_add_service_mod_destination(request, strsid, strmid):
    sid = int(strsid)
    mid = int(strmid)
    services = LcrRetailService.objects.filter(partner = request.user.get_profile().get_partner().partner, id = sid)
    if len(services):
        service = services[0]
    else:
        return HttpResponseRedirect('/retail/services/')
    if request.method == 'POST':
        dform = RetailServiceModDestinationForm(request.POST)
        if dform.is_valid():
            link = dform.save(commit = False)
            link.service = service
            link.mod_type = mid
            link.save()
            return HttpResponseRedirect('/retail/edit_service/' + strsid + '/')
    return HttpResponseRedirect('/retail/services/')

@login_required
@staff_member_required
def retail_del_service_mod_destination(request, strlid):
    lid = int(strlid)
    links = LcrRetailServiceModDestination.objects.filter(id = lid, service__partner = request.user.get_profile().get_partner().partner)
    if len(links):
        link = links[0]
    else:
        return HttpResponseRedirect('/retail/services/')
    service = link.service
    link.delete()
    return HttpResponseRedirect('/retail/edit_service/' + str(service.id) + '/')

@login_required
@staff_member_required
def retail_customers(request):
    return wrender('retail_customers.html', {}, request)

@login_required
@staff_member_required
def retail_add_customer(request):
    if request.method == 'POST':
        cform = RetailCustomerForm(request.POST)
        if cform.is_valid():
            customer = cform.save(commit = False)
            customer.partner = request.user.get_profile().get_partner().partner
            customer.save()
            return HttpResponseRedirect('/retail/edit_customer/' + str(customer.id) + '/')
    cform = RetailCustomerForm()
    return wrender('retail_add_customer.html', {'cform': cform}, request)

@login_required
@staff_member_required
def retail_edit_customer(request, cid):
    cid = int(cid)
    customers = LcrRetailCustomer.objects.filter(partner = request.user.get_profile().get_partner().partner, id = cid)
    if len(customers):
        customer = customers[0]
    else:
        return HttpResponseRedirect('/retail/customers/')
    cform = RetailCustomerForm(instance = customer, prefix = 'cf')
    sform = RetailCustomerServiceForm(prefix = 'sf')
    return wrender('retail_edit_customer.html', {'customer': customer, 'cform': cform, 'sform': sform}, request)

@login_required
@staff_member_required
def retail_add_cservice_number(request, cid):
    cid = int(cid)
    cservices = LcrRetailCustomerService.objects.filter(customer__partner = request.user.get_profile().get_partner().partner, id = cid)
    if len(cservices):
        cservice = cservices[0]
    else:
        return HttpResponseRedirect('/retail/customers/')
    strnum = request.POST['csnum']
    if re.match("\d", strnum):
        number = LcrRetailCustomerNumber(cservice = cservice, number = strnum)
        number.save()
    return HttpResponseRedirect('/retail/edit_customer/' + str(cservice.customer.id) + '/')

@login_required
@staff_member_required
def retail_add_cservice(request, cid):
    cid = int(cid)
    customers = LcrRetailCustomer.objects.filter(partner = request.user.get_profile().get_partner().partner, id = cid)
    if len(customers):
        customer = customers[0]
    else:
        return HttpResponseRedirect('/retail/customers/')
    if request.method == 'POST':
        sform = RetailCustomerServiceForm(request.POST, prefix = 'sf')
        cservice = sform.save(commit = False)
        cservice.customer = customer
        cservice.switch = 1
        cservice.d_when = datetime.datetime.now().date()
        cservice.save()
    return HttpResponseRedirect('/retail/edit_customer/' + str(customer.id) + '/')

@login_required
@staff_member_required
def retail_del_cservice_number(request, nid):
    nid = str(nid)
    numbers = LcrRetailCustomerNumber.objects.filter(cservice__customer__partner = request.user.get_profile().get_partner().partner, id = nid)
    if numbers:
        number = numbers[0]
    else:
        return HttpResponseRedirect('/retail/customers/')
    customer = number.cservice.customer
    number.delete()
    return HttpResponseRedirect('/retail/edit_customer/' + str(customer.id) + '/')

@login_required
@staff_member_required
def ver_stats(request):
    if request.user.get_profile().get_partner().partner.id != 1:
                return wrender('no_feature.html', {}, request)
    dt_begin = date.today() - timedelta(days = 8)
    dt_end = date.today() - timedelta(days = 1)
    switch = LcrSwitch.objects.filter(ip_addr = 'vs.ip.1.2.3.4')[0]
    deals = LcrDeal.objects.filter(Q(buy_carrier__switch = switch) | Q(buy_carrier__switch__master_switch = switch))
    #
    vs = []
    dt_cur = dt_begin
    while dt_cur <= dt_end:
        stat = {'date': dt_cur, 's_switch': 0, 's_deals': 0}
        sw_us = LcrStatSwitchHour.objects.filter(date = dt_cur, switch = switch)
        if len(sw_us):
            for sw_u in sw_us:
                if sw_u.hour != 0:
                    stat['s_switch'] += sw_u.seconds
        sw_us = LcrStatSwitchHour.objects.filter(date = dt_cur + timedelta(days = 1), hour = 0)
        if len(sw_us):
            stat['s_switch'] += sw_us[0].seconds
        for deal in deals:
            dus = LcrStatDailyUpdate.objects.filter(deal = deal, date = dt_cur)
            if len(dus):
                stat['s_deals'] += dus[0].seconds
        stat['m_switch'] = round(stat['s_switch'] / 60)
        stat['m_deals'] = round(stat['s_deals'] / 60)
        stat['match'] = stat['s_deals'] * 100 / stat['s_switch']
        vs.append(stat)
        dt_cur += timedelta(days = 1)
    return wrender('ver_stats.html', {'vs': vs}, request)

@login_required
@staff_member_required
def edit_escalation(request, eid):
    eid = int(eid)
    e = LcrEscalation.objects.get(id = eid)
    if request.method  == 'POST':
        f = EscalationResponseForm(request.POST)
        if f.is_valid():
            er = f.save(commit = False)
            er.escalation = e
            er.author = request.user
            er.save()
            e.status = er.status
            e.save()
    else:
        f = EscalationResponseForm()
    rs = LcrEscalationResponse.objects.filter(escalation = e).order_by('id')
    return wrender('edit_escalation.html', {'e': e, 'f': f, 'rs': rs}, request)

@login_required
@staff_member_required
def dashboard(request):
    if request.user.get_profile().is_god():
        deals = LcrDeal.objects.filter(is_active = 1)
    else:
        deals = LcrDeal.objects.filter(is_active = 1, partner = request.user.get_profile().get_partner().partner)
    for deal in deals:
        deal.lh = deal.lasth()
    return wrender('dashboard.html', {'deals': deals}, request)

@login_required
@staff_member_required
def dax(request):
    if request.user.get_profile().is_god():
        deals = LcrDeal.objects.filter(is_active = 1)
    else:
        deals = LcrDeal.objects.filter(is_active = 1, partner = request.user.get_profile().get_partner().partner)
    for deal in deals:
        deal.lh = deal.lasth()
    return wrender('dax.html', {'deals': deals}, request)

@login_required
@staff_member_required
def ajx_dax_stats(request, str_did, str_curweek):
    if request.user.get_profile().is_god():
        deals = LcrDeal.objects.filter(id = int(str_did))
    else:
        deals = LcrDeal.objects.filter(id = int(str_did), partner = request.user.get_profile().get_partner().partner)
    if not len(deals):
        return HttpResponse('{}')
    deal = deals[0]
    ret = {}
    dt_cw = datetime.datetime.fromtimestamp(int(str_curweek))
    for day in range(0, 7):
        dt_cur = dt_cw + timedelta(days = day)
        darr = {}
        for stat in LcrStatH.objects.filter(deal = deal, dt_when__gte = dt_cur, dt_when__lt = dt_cur + timedelta(days = 1)):
            darr[stat.dt_when.hour] = {
                'calls_ok': 	stat.calls_ok,
                'calls_fail':	stat.calls_fail,
                'seconds':		stat.seconds,
                'asr':			int(stat.asr()),
                'acd':			int(stat.acd())
            }
        ret[int(time.mktime(dt_cur.timetuple()))] = darr
    return HttpResponse(simplejson.dumps(ret))

@login_required
@staff_member_required
def ajx_deal(request, str_did):
    if request.user.get_profile().is_god():
        deals = LcrDeal.objects.filter(id = int(str_did))
    else:
        deals = LcrDeal.objects.filter(id = int(str_did), partner = request.user.get_profile().get_partner().partner)
    if not len(deals):
        return HttpResponse('{}')
    deal = deals[0]
    return wrender('ajx_deal.html', {'deal': deal}, request)

@login_required
@staff_member_required
def old_dashboard(request):
    if request.user.get_profile().is_god():
        deals = LcrDeal.objects.filter(is_active = 1)
    else:
        deals = LcrDeal.objects.filter(is_active = 1, partner = request.user.get_profile().get_partner().partner)
    customers = []
    suppliers = []
    deals_arr = []
    dp = {}
    db = LcrSwitch.objects.filter(ip_addr = 'vs.ip.1.2.3.4')[0].get_db()
    q = "SELECT telephone_number, priority, dialingplan.tech_prefix, dialingplan.id_route, description, ip_number FROM dialingplan LEFT JOIN gateways ON dialingplan.id_route = gateways.id_route WHERE telephone_number LIKE '527%'"
    db.query(q)
    r = db.store_result()
    o = r.fetch_row(maxrows = 0)
    for os in o:
        dp[os[0]] = {}
        dp[os[0]][os[1]] = {
            'tech_prefix':	os[2],
            'description':	os[4],
            'ip_addr': os[5]
        }
    db.close()
    for deal in deals:
        addme = True
        # Cust / Supp
        if addme and not deal.buy_carrier.carrier in customers:
            customers.append(deal.buy_carrier.carrier)
        if addme and not deal.destination.supplier.carrier in suppliers:
            suppliers.append(deal.destination.supplier.carrier)
        if addme:
            tl = {'CT': 0, 'MS': 0, 'SS': 9, 'ST': 0, 'ATT': 2}
            if len(LcrStatPeriodUpdate.objects.filter(deal = deal, period = 2, seconds__gt = 0, dt_when__gte = datetime.datetime.now() - timedelta(hours = 1))):
                tl['CT'] = 2
                tl['ST'] = 2
            deal.tl = tl
            dp_match = True
            # >>> VOIPSWITCH
            if deal.buy_carrier.switch.type == 1:
                for code in deal.destination.lcrdestinatione164_set.all():
                    match_code = '527%07d%s%s' % (deal.buy_carrier.id, deal.tech_prefix, code.code)
                    try:
                        match_dp = dp[match_code][str(deal.priority)]
                    except KeyError:
                        dp_match = False
                    if dp_match:
                        if match_dp['description'] == deal.destination.switch_name() and match_dp['ip_addr'] == deal.destination.ip_addr + ':5060':
                            pass
                        else:
                            dp_match = False
            if dp_match:
                tl['MS'] = 2
                if deal.buy_carrier.switch.is_slave():
                    tl['SS'] = 2
            if tl['CT'] == 0 or tl['MS'] == 0 or tl['SS'] == 0 or tl['ST'] == 0:
                tl['ATT'] = 0
            deals_arr.append(deal)
    return wrender('dashboard.html', {'deals': deals_arr, 'customers': customers, 'suppliers': suppliers}, request)

def agent_status(request):
    return wrender('agent_status.html', {}, request)

def agent_pbx_send_message(m):
    acmPrompt = 'Asterisk Call Manager/1.1'
    tn = telnetlib.Telnet('pbx.ip.1.2.3.4', 6969)
    tn.read_until(acmPrompt)
    tn.write('Action: login\r\nUsername: lcr\r\nSecret: pbx_password\r\nEvents: off\r\n\r\n')
    tn.write(m)
    tn.write('Action: logoff\r\n\r\n')

# Queue name: SSEN
# Context name: cont-tmp
# Queue DN: 771nnnnn
# PSTN DN: 349nnnnnn

def agent_pause(request):
    agent = request.user.get_profile().get_agent()
    name = request.user.get_profile().get_agent_ara().name
    m = 'Action: QueuePause\r\nQueue: SSEN\r\nInterface: Local/%s@cont-tmp\r\nPaused: true\r\n\r\n' % (name, )
    agent_pbx_send_message(str(m))
    agent.status = 10
    agent.save()
    return HttpResponse('OK')

def agent_unpause(request):
    agent = request.user.get_profile().get_agent()
    name = request.user.get_profile().get_agent_ara().name
    m = 'Action: QueuePause\r\nQueue: SSEN\r\nInterface: Local/%s@cont-tmp\r\nPaused: false\r\n\r\n' % (name, )
    agent_pbx_send_message(str(m))
    agent.status = 100
    agent.save()
    return HttpResponse('OK')

def ragents_pbx_stats():
    queue = []
    calls = []
    meetmes = []
    counts = {
        'paused':	0,
        'active':	0,
        'call':		0
    }
    acmPrompt = 'Asterisk Call Manager/1.1'
    tn = telnetlib.Telnet('pbx.ip.1.2.3.4', 6969)
    tn.read_until(acmPrompt)
    tn.write('Action: login\r\nUsername: lcr\r\nSecret: pbx_password\r\nEvents: off\r\n\r\n')
    tn.write('Action: QueueStatus\r\n\r\n')
    t = tn.read_until('QueueStatusComplete')
    p_agent = 'Event: QueueMember\r\nQueue: SSEN\r\nName: Local\/771(\d{5})@cont-tmp\r\nLocation: Local\/771(\d{5})@cont-tmp\r\nMembership: dynamic\r\nPenalty: 10\r\nCallsTaken: (\d*)\r\nLastCall: (\d*)\r\nStatus: (\d*)\r\nPaused: (\d*)\r\n'
    ams = re.findall(p_agent, t)
    for am in ams:
        ara = LcrRetailARASipFriend.objects.get(name = '771' + am[0])
        a_status = am[4]
        a_paused = am[5]
        if a_status == '1' and a_paused == '1':
            status = 'PAUSED'
            counts['paused'] += 1
        elif a_status == '1' and a_paused != '1':
            status = 'ACTIVE (' + a_status + ')'
            counts['active'] += 1
        elif a_status != '1':
            status = 'RING (' + a_status + ')'
            counts['call'] += 1
        queue.append({
            'agent':		ara.agent,
            'last_call':	datetime.datetime.fromtimestamp(int(am[3])),
            'status':		status
        })
    p_call = 'Event: QueueEntry\r\nQueue: SSEN\r\nPosition: (\d*)\r\nChannel: Local\/(\d*)@cont-agents-queue-(.*?);(\d*)\r\nUniqueid: (\d*).(\d*)\r\nCallerIDNum: (\d*)\r\nCallerIDName: Outbound Call\r\nConnectedLineNum: (\d*)\r\nConnectedLineName: unknown\r\nWait: (\d*)\r\n'
    acs = re.findall(p_call, t)
    for ac in acs:
        calls.append({
            'number':	ac[1],
            'wait':		ac[8]
        })
    tn.write('Action: Command\r\nCommand: meetme list\r\n\r\n')
    t = tn.read_until('--END')
    p_meetme = '349(\d{8})    000(\d)\t      N\/A        (\d{2}):(\d{2}):(\d{2})  Dynamic   No    \n'
    mms = re.findall(p_meetme, t)
    for mm in mms:
        meetmes.append({
            'exten':	'349' + mm[0],
            'parties':	mm[1],
            'd_h':		mm[2],
            'd_m':		mm[3],
            'd_s':		mm[4],
            'seconds':	60 * 60 * int(mm[2]) + 60 * int(mm[3]) + int(mm[4])
        })
    tn.write('Action: Logoff\r\n\r\n')
    return {'queue': queue, 'calls': calls, 'counts': counts, 'meetmes': meetmes}

@login_required
@staff_member_required
def ragents_candidate(request, cid):
    cid = int(cid)
    if cid == 0:
        candidates = LcrRetailCandidate.objects.all().order_by('-dt_input')
        return wrender('ragents_candidate_index.html', {'candidates': candidates}, request)
    else:
        candidate = LcrRetailCandidate.objects.get(id = cid)
        return wrender('ragents_candidate.html', {'c': candidate}, request)

@login_required
@staff_member_required
def ragents_list(request):
    agents = LcrRetailAgent.objects.all()
    return wrender('ragents_list.html', {'agents': agents}, request)

@login_required
@staff_member_required	
def ragents_queue(request):
    reqs = LcrRetailRoboRequest.objects.order_by('-id')[:100]
    return wrender('ragents_queue.html', {'stats': ragents_pbx_stats(), 'reqs': reqs}, request)

@login_required
@staff_member_required
def ajax_dd(request, strdid):
    did = int(strdid)
    deal = LcrDeal.objects.get(id = did)
    stat_total = deal.get_stat_total()
    deal.s_total = stat_total
    deal.o_tspent = float(deal.s_total.seconds / 60) * float(deal.sell_price)
    deal.o_tearned = float(deal.s_total.seconds / 60) * float(deal.buy_price)
    deal.o_tprofit = deal.o_tearned - deal.o_tspent
    deal.o_tspointed = deal.pointed_sum(2)
    deal.o_tsleft = deal.o_tspointed - deal.o_tspent
    deal.o_msleft = 0
    if deal.o_tsleft > 0:
        deal.o_msleft = deal.o_tsleft / float(deal.sell_price)
    deal.o_tbpointed = deal.pointed_sum(1)
    deal.o_tbleft = deal.o_tbpointed - deal.o_tearned
    deal.o_mbleft = 0
    if deal.o_tbleft > 0:
            deal.o_mbleft = deal.o_tbleft / float(deal.buy_price)
    # Time Periods
    deal.l15min = LcrStatPeriodUpdate.objects.filter(deal = deal, period = 1).order_by('-id')[0]
    deal.l60min = LcrStatPeriodUpdate.objects.filter(deal = deal, period = 2).order_by('-id')[0]
    deal.l12h = LcrStatPeriodUpdate.objects.filter(deal = deal, period = 3).order_by('-id')[0]
    deal.l24h = LcrStatPeriodUpdate.objects.filter(deal = deal, period = 4).order_by('-id')[0]
    # Daily Breakdown
    deal.s_daily = LcrStatDailyUpdate.objects.filter(deal = deal).order_by('-date')[:7]
    return wrender('ajax_dd.html', {'deal': deal}, request)

@login_required
@staff_member_required
def view_billing(request):
    if request.method == 'POST':
        str_begin = request.POST['d_from']
        str_end = request.POST['d_to']
    else:
        delta = timedelta(days = 8)
        str_begin = (date.today() - delta).isoformat()
        str_end = date.today().isoformat()
    bx = str_begin.split('-')
    ex = str_end.split('-')
    date_begin = datetime.date(int(bx[0]), int(bx[1]), int(bx[2]))
    date_end = datetime.date(int(ex[0]), int(ex[1]), int(ex[2]))
    if request.user.get_profile().is_god():
        customers = LcrCustomer.objects.all()
        suppliers = LcrSupplier.objects.all()
    else:
        customers = LcrCustomer.objects.filter(carrier__partner = request.user.get_profile().get_partner().partner)
        suppliers = LcrSupplier.objects.filter(carrier__partner = request.user.get_profile().get_partner().partner)
    billing = []
    for customer in customers:
        add_cust = False
        b_cust = {'customer': customer, 'deals': []}
        c_deals = LcrDeal.objects.filter(buy_carrier = customer)
        tot_dur = 0
        tot_cost = 0
        for deal in c_deals:
            d_stats = LcrStatDailyUpdate.objects.filter(deal = deal, date__gte = date_begin, date__lte = date_end)
            if len(d_stats):
                d_seconds = 0
                for stat in d_stats:
                    d_seconds += stat.seconds
                b_deal = {'deal': deal, 'd_minutes': int(round(d_seconds / 60)), 'd_cost': int(round(d_seconds / 60)) * deal.buy_price}
                b_cust['deals'].append(b_deal)
                add_cust = True
                tot_dur += b_deal['d_minutes']
                tot_cost += b_deal['d_cost']
        b_cust['tot_dur'] = tot_dur
        b_cust['tot_cost'] = tot_cost
        if add_cust:
            billing.append(b_cust)
    terming = []
    for supplier in suppliers:
        add_supp = False
        t_supp = {'supplier': supplier, 'deals': []}
        s_deals = LcrDeal.objects.filter(destination__supplier = supplier)
        tot_dur = 0
        tot_cost = 0
        for deal in s_deals:
            d_stats = LcrStatDailyUpdate.objects.filter(deal = deal, date__gte = date_begin, date__lte = date_end)
            if len(d_stats):
                d_seconds = 0
                for stat in d_stats:
                    d_seconds += stat.seconds
                s_deal = {'deal': deal, 'd_minutes': int(round(d_seconds / 60)), 'd_cost': int(round(d_seconds / 60)) * deal.buy_price}
                t_supp['deals'].append(s_deal)
                add_supp = True
                tot_dur += s_deal['d_minutes']
                tot_cost += s_deal['d_cost']
        t_supp['tot_dur'] = tot_dur
        t_supp['tot_cost'] = tot_cost
        if add_supp:
            terming.append(t_supp)
    return wrender('view_billing.html', {'b': billing, 't': terming, 'd': str_begin, 'de': str_end}, request)

@login_required
@staff_member_required
def list_carriers(request):
    if request.user.get_profile().is_god():
        partners = LcrPartner.objects.all()
    else:
        partners = LcrPartner.objects.filter(id = request.user.get_profile().get_partner().partner.id)
    for partner in partners:
        partner.carriers = LcrCarrier.objects.filter(partner = partner)
    return wrender('list_carriers.html', {'partners': partners}, request)

@login_required
@staff_member_required
def edit_carrier(request, str_cid):
    cid = int(str_cid)
    carrier = LcrCarrier.objects.get(id = cid)
    cform = CarrierForm(instance = carrier)
    return wrender('edit_carrier.html', {'carrier': carrier, 'cform': cform}, request)

@login_required
@staff_member_required
def edit_customer(request, str_cid):
    cid = int(str_cid)
    customer = LcrCustomer.objects.get(id = cid)
    ipform = CustomerIpForm()
    return wrender('edit_customer.html', {'customer': customer, 'ipform': ipform}, request)

@login_required
@staff_member_required
def purge_customer(request, str_cid):
    cid = int(str_cid)
    customer = LcrCustomer.objects.get(id = cid)
    if customer.switch.is_slave():
        switch = customer.switch.master_switch
    else:
        switch = customer.switch
    if switch.type == 1:
        db = switch.get_db()
        q = 'DELETE FROM dialingplan WHERE telephone_number LIKE "527%07d%%"' % customer.id
        db.query(q)
        db.close()
    return HttpResponseRedirect('/edit_customer/%d/' % (customer.id, ))

@login_required
@staff_member_required
def server_monitor(request):
    ssms = LcrStatServerMonitor.objects.order_by('-dt_when')[:10]
    return wrender('server_monitor.html', {'ssms': ssms}, request)

@login_required
@staff_member_required
def add_customer_ip(request, strcid):
    cid = int(strcid)
    c = LcrCustomer.objects.get(id = cid)
    f = CustomerIpForm(request.POST)
    if f.is_valid():
        customer_ip = f.save(commit = False)
        customer_ip.customer = c
        customer_ip.save()
    return HttpResponseRedirect('/edit_customer/' + str(c.id) + '/')

@login_required
@staff_member_required
def del_customer_ip(request, striid):
    iid = int(striid)
    customer_ip = LcrCustomerIp.objects.get(id = iid)
    cid = customer_ip.customer.id
    customer_ip.delete()
    return HttpResponseRedirect('/edit_customer/' + str(cid) + '/')

@login_required
@staff_member_required
def add_carrier_customer(request, str_cid):
    cid = int(str_cid)
    carrier = LcrCarrier.objects.get(id = cid)
    if request.method == 'POST':
        cform = CustomerForm(request.POST)
        if cform.is_valid():
            customer = cform.save(commit = False)
            customer.carrier = carrier
            customer.save()
            return HttpResponseRedirect('/edit_customer/' + str(customer.id) + '/')
    else:
        cform = CustomerForm()
        if not request.user.get_profile().is_god():
            cform.fields['switch'].queryset = LcrSwitch.objects.filter(partner = request.user.get_profile().get_partner().partner)
    return wrender('add_carrier_customer.html', {'carrier': carrier, 'cform': cform}, request)

@login_required
@staff_member_required
def add_carrier_supplier(request, str_cid):
    cid = int(str_cid)
    carrier = LcrCarrier.objects.get(id = cid)
    if request.method == 'POST':
        sform = SupplierForm(request.POST)
        if sform.is_valid():
            supplier = sform.save(commit = False)
            supplier.carrier = carrier
            supplier.save()
            return HttpResponseRedirect('/edit_carrier/' + str(carrier.id) + '/')
    else:
        sform = SupplierForm()
    return wrender('add_carrier_supplier.html', {'carrier': carrier, 'sform': sform}, request)

@login_required
@staff_member_required
def dest_add(request):
    if request.method == 'POST':
        dform = DestinationForm(request.POST)
        if dform.is_valid():
            dest = dform.save()
            return HttpResponseRedirect('/dest_details/' + str(dest.id) + '/')
    else:
        dform = DestinationForm()
        if not request.user.get_profile().is_god():
            dform.fields['supplier'].queryset = LcrSupplier.objects.filter(carrier__partner = request.user.get_profile().get_partner().partner)
    return wrender('dest_add.html', {'dform': dform}, request)

def carrier_register(request):
    p = get_pid(request)
    c_data = {1:
        {
            'c_name':	'Your Company',
            'c_fa':		"Your Company\r\n123 Street Address\r\n456 ZIP Code\r\nCountry",
            'c_phone':	'+44 123 123 123',
            'c_website':	'http://www.your-company.com',
            'c_email':	'email@your-company.com',
            #
            'b_name':	'Business Contact',
            'b_phone':	'+44 123 123 123',
            'b_msn':	'business@msn',
            'b_email':	'business@your-company.com',
            'b_hours':	'09:00 - 17:00 GMT',
            #
            'n_name':	'NOC Contact',
            'n_phone':	'+44 123 123 123',
            'n_msn':	'noc@msn',
            'n_email':	'noc@your-company.com',
            'n_hours':	'09:00 - 17:00 GMT',
            #
            'i_city':	'London, UK',
            'i_provider':	'1&1',
            'i_as':		'AS12345',
            'i_dedicated':	'No',
            'i_band':	'1 Gbps',
            #
            'p_signal':	'1.2.3.4/32',
            'p_port':	'udp/5060',
            'p_sother':	'Yes - TBA',
            'p_media':	'5.6.7.8/27',
            'p_mother':	'No',
            'p_iptype':	'Internet / OpenVPN / LAN',
            #
            'v_manufact':	'Tesserakt / VoipSwitch / Digium',
            'v_model':	'VS / LCR / TTS / FS SBC',
            'v_version':	'VS 2.986.0.343, FS 1.06, TTS 1.02',
            'v_protocol':	'SIP / UDP',
            'v_numsess':	'N/A',
            'v_cps':	'N/A',
            'v_role':	'Both',
            'v_codec':	'G.729',
            'v_payload':	'20 ms',
            'v_sss':	'No',
            'v_rfc':	'Yes'
        },

    }
    if request.method == 'POST':
        form = CarrierForm(request.POST, request.FILES)
        if form.is_valid():
            partner = LcrPartner.objects.get(id = p['id'])
            carrier = form.save(commit = False)
            carrier.partner = partner
            carrier.info_ip = request.META['REMOTE_ADDR']
            carrier.save()
            return wrender('carrier_thankyou.html', {}, request)
    else:
        form = CarrierForm()
    return wrender('carrier_register.html', {'form': form, 'cdata': c_data[p['id']]}, request)

def carrier_escalation(request):
    p = get_pid(request)
    if request.method == 'POST':
        form = EscalationForm(request.POST, request.FILES)
        if form.is_valid():
            partner = LcrPartner.objects.get(id = p['id'])
            escalation = form.save(commit = False)
            escalation.partner = partner
            escalation.carrier = request.user.lcrwebaccount.carrier
            escalation.info_ip = request.META['REMOTE_ADDR']
            escalation.save()
            return wrender('carrier_thankyou.html', {}, request)
    else:
        form = EscalationForm()
    return wrender('carrier_escalation.html', {'form': form}, request)

def carrier_contact(request):
    p = get_pid(request)
    return wrender('contact_' + str(p['id']) + '.html', {}, request)

@login_required
def carrier_deals(request):
    carrier = request.user.lcrwebaccount.carrier
    deals_buyer = LcrDeal.objects.filter(buy_carrier__carrier = carrier)
    deals_seller = LcrDeal.objects.filter(destination__supplier__carrier = carrier)
    return wrender('carrier_deals.html', {'deals_buyer': deals_buyer, 'deals_seller': deals_seller}, request)

@login_required
def home_az(request):
    azs = request.user.lcraz_set.all()
    return wrender('home.html', {'azs': azs}, request)

@login_required
def delete_az(request, strAid):
    aid = int(strAid)
    az = LcrAZ.objects.get(id = aid)
    az.delete()
    return HttpResponseRedirect('/az/')

@login_required
def download_az(request, strAid):
    aid = int(strAid)
    az = LcrAZ.objects.get(id = aid)
    faz = az.file
    response = HttpResponse(faz.read(), mimetype = 'application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=' + faz.name
    return response

@login_required
def supplier(request):
    if request.method == 'POST':
                form = SupplierForm(request.POST)
        if form.is_valid():
            s = form.save()
        return HttpResponseRedirect('/')
    else:
        form = SupplierForm()
    return wrender('supplier.html', {'form': form}, request)

@login_required
def usupplier(request):
    if request.method == 'POST':
        form = USupplierForm(request.POST, request.FILES)
        if form.is_valid():
            xls = request.FILES['svform'].read()
            x = open_workbook(file_contents = xls)
            sheet = x.sheet_by_index(0)
            supp = LcrSupplier()
            supp.name = sheet.cell(13, 4).value
            supp.address = sheet.cell(15, 4).value
            supp.phone = sheet.cell(21, 4).value
            supp.bill_name = sheet.cell(23, 4).value
            supp.bill_phone	= sheet.cell(25, 4).value
            supp.bill_msn = sheet.cell(27, 4).value
            supp.bill_email = sheet.cell(27, 4).value
            supp.noc_name = sheet.cell(137, 4).value
            supp.noc_phone	= sheet.cell(139, 4).value
            supp.noc_msn = sheet.cell(143, 4).value
            supp.noc_email = sheet.cell(141, 4).value
            supp.prov_gw_brand = sheet.cell(37, 4).value
            supp.prov_gw_model = sheet.cell(39, 4).value
            supp.prov_gw_soft = sheet.cell(41, 4).value
            supp.prov_ip_signal = sheet.cell(46, 4).value
            supp.prov_ip_media = sheet.cell(49, 4).value
            supp.save()
        return wrender('usupplier_complete.html', {'supp': supp}, request)
    else:
        form = USupplierForm()
        return wrender('usupplier.html', {'form': form}, request)

@login_required
def test_routes(request):
    if request.user.get_profile().get_partner().partner.id != 1:
                return wrender('no_feature.html', {}, request)
    q = 'SELECT CONCAT("934", dialingplan.telephone_number) AS prefix, gateways.description AS route, gateways.ip_number AS ip FROM dialingplan LEFT JOIN gateways ON dialingplan.id_route = gateways.id_route WHERE dialingplan.telephone_number LIKE "99%"'
    db = _mysql.connect('test.vs.1.2.3.4', 'root', 'pass', 'pass')
    db.query(q)
    r = db.store_result()
    o = r.fetch_row(maxrows = 0)
    db.close()
    return wrender('test_routes.html', {'o': o}, request)

@login_required
def add_route(request):
    if request.user.get_profile().get_partner().partner.id != 1:
                return wrender('no_feature.html', {}, request)
    if request.method == 'POST':
        form = AddTRForm(request.POST)
        if form.is_valid():
            db = _mysql.connect('vs.add.1.2.3.4', 'root', 'pass', 'pass')
            q = 'INSERT INTO gateways (description, ip_number, h323_id, type, call_limit, id_tariff, tech_prefix, codecs) VALUES ("%s test", "%s:5060", "sip@sip", 64, 0, -1, "DN:;TP:", 264)' % (form.cleaned_data['name'], form.cleaned_data['ip_num'], )
            db.query(q)
            gid = db.insert_id()
            q = 'SELECT telephone_number FROM dialingplan WHERE telephone_number LIKE "99%" ORDER BY telephone_number DESC LIMIT 1'
            db.query(q)
            r = db.store_result()
            o = r.fetch_row(maxrows = 0)
            pix = str(int(o[0][0]) + 1)
            q = 'INSERT INTO dialingplan (telephone_number, priority, route_type, tech_prefix, dial_as, id_route, call_type, type, from_day, to_day, from_hour, to_hour, balance_share, fields, call_limit) VALUES ("%s", 0, 0, "DN:%s->", "", %d, 1207959572, 0, 0, 6, 0, 2359, 0, "", 0)' % (pix, pix, gid, )
            db.query(q)
            db.close()
            return HttpResponseRedirect('/test_routes/')
    else:
        form = AddTRForm()
    return wrender('add_route.html', {'form': form}, request)

@login_required
def add_point(request):
    if request.method == 'POST':
        f = PointForm(request.POST)
        if f.is_valid():
            point = f.save()
            return HttpResponse('OK!')
    else:
        f = PointForm()
        if not request.user.get_profile().is_god():
            f.fields['deal'].queryset = LcrDeal.objects.filter(partner = request.user.get_profile().get_partner().partner)
    return wrender('add_point.html', {'f': f}, request)

@login_required
def add_deal(request):
    if request.method == 'POST':
        f = DealForm(request.POST)
        if f.is_valid():
            deal = f.save()
            return HttpResponse('OK!')
    else:
        f = DealForm()
        if not request.user.get_profile().is_god():
            f.fields['partner'].queryset = LcrPartner.objects.filter(id = request.user.get_profile().get_partner().partner.id)
            f.fields['buy_carrier'].queryset = LcrCustomer.objects.filter(carrier__partner = request.user.get_profile().get_partner().partner)
            f.fields['destination'].queryset = LcrDestination.objects.filter(supplier__carrier__partner = request.user.get_profile().get_partner().partner)
    return wrender('add_deal.html', {'f': f}, request)

def deal_sql_prefixes(deal, return_array = False):
    #codes = LcrCode.objects.filter(deal = deal)
    codes = LcrDestinationE164.objects.filter(destination = deal.destination)
    ret_arr = []
    ret = '('
    i = 0
    slave_prefix = ''
    if deal.buy_carrier.switch.is_slave():
        slave_prefix = '527%07d' % (deal.buy_carrier.id, )
    if len(codes):
        for code in codes:
            str_code = code.code
            if deal.buy_carrier.tech_prefix and not deal.buy_carrier.switch.is_slave():
                str_code = deal.buy_carrier.tech_prefix + code.code
            if deal.tech_prefix:
                str_code = deal.tech_prefix + str_code
            if i != 0:
                ret += ' OR '
            i += 1
            ret += 'called_number LIKE "%s%s%%"' % (slave_prefix, str_code, )
            ret_arr.append('%s%s' % (slave_prefix, str_code))
    else:
        ret += '0 = 1'
    ret += ')'
    if return_array:
        return ret_arr
    else:
        return ret

def dest_sql_prefixes(dest):
    deals = LcrDeal.objects.filter(destination = dest)
    ret = '('
    i = 0
    if len(deals):
        for deal in deals:
            if i != 0:
                ret += ' OR '
            i+= 1
            ret += deal_sql_prefixes(deal)
    else:
        ret += '0 = 1'
    ret += ')'
    return ret

def deal_delta(deal, delta, db):
    ret = {}
    if deal.buy_carrier.switch.type == 1:
        q = 'SELECT COUNT(*) AS "Calls", ROUND(SUM(duration)/60,0) AS "Minutes", ROUND(SUM(duration) / COUNT(*), 2) AS "ACD", SUM(duration) AS "Seconds" FROM calls JOIN clientsip JOIN gateways WHERE calls.id_client=clientsip.id_client AND calls.id_route=gateways.id_route AND duration>0 AND duration<35940 AND Login = "%s" AND gateways.description = "%s" AND %s AND call_start > NOW() - INTERVAL %s' % (deal.customer_switch_name(), deal.destination.switch_name(), deal_sql_prefixes(deal), delta)
    elif deal.buy_carrier.switch.type == 2:
        q = 'SELECT COUNT(*) AS "Calls", ROUND(SUM(duration)/60,0) AS "Minutes", ROUND(SUM(duration) / COUNT(*), 2) AS "ACD", SUM(duration) AS "Seconds" FROM lcr_cdr WHERE hang_pcause = "sip:200" AND deal_id = %d AND dt_begin > NOW() - INTERVAL %s' % (deal.id, delta)
    #sys.stdout.write("\r\n" + q + "\r\n")
    db.query(q)
    r = db.store_result()
    o = r.fetch_row()
    ret['ok'] = [[]]
    for i in range(4):
        if not o[0][i]:
            ret['ok'][0].append(0)
        else:
            ret['ok'][0].append(o[0][i])
    if deal.buy_carrier.switch.type == 1:
        q = 'SELECT COUNT(*) AS "Failed Calls" FROM callsfailed JOIN clientsip JOIN gateways WHERE callsfailed.id_client=clientsip.id_client AND callsfailed.id_route=gateways.id_route AND Login = "%s" AND gateways.description = "%s" AND %s AND call_start > NOW() - INTERVAL %s' % (deal.customer_switch_name(), deal.destination.switch_name(), deal_sql_prefixes(deal), delta)
    elif deal.buy_carrier.switch.type == 2:
        q = 'SELECT COUNT(*) AS "Failed Calls" FROM lcr_cdr WHERE hang_pcause != "sip:200" AND deal_id = %d AND dt_begin > NOW() - INTERVAL %s' % (deal.id, delta)
        db.query(q)
        r = db.store_result()
        o = r.fetch_row()
        ret['fail'] = [[]]
    if not o[0][0]:
        ret['fail'][0].append(0)
    else:
        ret['fail'][0].append(o[0][0])
    if float(ret['ok'][0][0]) > 0:
        ret['asr'] = float(ret['ok'][0][0]) / (float(ret['ok'][0][0]) + float(ret['fail'][0][0])) * 100
    else:
        ret['asr'] = 0
    return ret

def deal_daily_delta(deal, db):
    ret = {}
    str_today = date.today().isoformat()
    if deal.buy_carrier.switch.type == 1:
        q = 'SELECT COUNT(*) AS "Calls", ROUND(SUM(duration)/60,0) AS "Minutes", ROUND(SUM(duration) / COUNT(*), 2) AS "ACD", SUM(duration) AS "Seconds" FROM calls JOIN clientsip JOIN gateways WHERE calls.id_client=clientsip.id_client AND calls.id_route=gateways.id_route AND duration>0 AND duration<35940 AND Login = "%s" AND gateways.description = "%s" AND %s AND call_start > "%s 00:00:00" + INTERVAL 1 HOUR' % (deal.customer_switch_name(), deal.destination.switch_name(), deal_sql_prefixes(deal), str_today)
    elif deal.buy_carrier.switch.type == 2:
        q = 'SELECT COUNT(*) AS "Calls", ROUND(SUM(duration)/60,0) AS "Minutes", ROUND(SUM(duration) / COUNT(*), 2) AS "ACD", SUM(duration) AS "Seconds" FROM lcr_cdr WHERE hang_pcause = "sip:200" AND deal_id = %d AND dt_begin > "%s 00:00:00" + INTERVAL 1 HOUR' % (deal.id, str_today)
    db.query(q)
    r = db.store_result()
    o = r.fetch_row()
    ret['ok'] = [[]]
        for i in range(4):
                if not o[0][i]:
                        ret['ok'][0].append(0)
                else:
                        ret['ok'][0].append(o[0][i])
    return ret

@login_required
def dest_list(request):
    if request.user.get_profile().is_god():
        suppliers = LcrSupplier.objects.all()
    else:
        suppliers = LcrSupplier.objects.filter(carrier__partner = request.user.get_profile().get_partner().partner)
    asupps = []
    for supplier in suppliers:
        if len(supplier.lcrdestination_set.all()):
            supplier.dests = supplier.lcrdestination_set.order_by('name')
            asupps.append(supplier)
    return wrender('dest_list.html', {'asupps': asupps}, request)

@login_required
def dest_details(request, str_did):
    did = int(str_did)
    d = LcrDestination.objects.get(id = did)
    eform = E164Form()
    e164s = LcrDestinationE164.objects.filter(destination = d)
    if request.method == 'POST':
        form = DestinationForm(request.POST, instance = d)
        form.save()
    else:
        form = DestinationForm(instance = d)
    return wrender('dest_details.html', {'form': form, 'd': d, 'eform': eform, 'e164s': e164s}, request)

@login_required
def dest_add_e164(request, strdid):
    did = int(strdid)
    d = LcrDestination.objects.get(id = did)
    codes = re.findall('(\d*)', request.POST['f_prefixes'])
        for code in codes:
        if len(code):
            e164 = LcrDestinationE164(destination = d)
            e164.code = code
            e164.save()
    return HttpResponseRedirect('/dest_details/' + str(d.id) + '/')

@login_required
def dest_del_e164(request, streid):
    eid = int(streid)
    e164 = LcrDestinationE164.objects.get(id = eid)
    did = e164.destination.id
    e164.delete()
    return HttpResponseRedirect('/dest_details/' + str(did) + '/')


@login_required
def view_deal(request):
    deals = LcrDeal.objects.filter(is_active = 1)
    for deal in deals:
        stat_total = LcrStatTotalUpdate.objects.filter(deal = deal).order_by('-id')[0]
        deal.s_total = stat_total
        deal.o_tspent = float(deal.s_total.seconds / 60) * float(deal.sell_price)
        deal.o_tearned = float(deal.s_total.seconds / 60) * float(deal.buy_price)
        deal.o_tprofit = deal.o_tearned - deal.o_tspent
        deal.o_tspointed = deal.pointed_sum(2)
        deal.o_tsleft = deal.o_tspointed - deal.o_tspent
        deal.o_msleft = 0
        if deal.o_tsleft > 0:
            deal.o_msleft = deal.o_tsleft / float(deal.sell_price)
        deal.o_tbpointed = deal.pointed_sum(1)
        deal.o_tbleft = deal.o_tbpointed - deal.o_tearned
        deal.o_mbleft = 0
        if deal.o_tbleft > 0:
            deal.o_mbleft = deal.o_tbleft / float(deal.buy_price)
        # Time Periods
        deal.l15min = LcrStatPeriodUpdate.objects.filter(deal = deal, period = 1).order_by('-id')[0]
        deal.l60min = LcrStatPeriodUpdate.objects.filter(deal = deal, period = 2).order_by('-id')[0]
        deal.l12h = LcrStatPeriodUpdate.objects.filter(deal = deal, period = 3).order_by('-id')[0]
        deal.l24h = LcrStatPeriodUpdate.objects.filter(deal = deal, period = 4).order_by('-id')[0]
        # Daily Breakdown
        deal.s_daily = LcrStatDailyUpdate.objects.filter(deal = deal).order_by('-date')[:7]
    return wrender('deal_list.html', {'deals': deals}, request)

@login_required
def carrier_deal_details(request, strdid):
    did = int(strdid)
    carrier = request.user.lcrwebaccount.carrier
    deal = LcrDeal.objects.get(id = did)
    if deal.buy_carrier.carrier == carrier or deal.destination.supplier.carrier == carrier:
        #stat_total = LcrStatTotalUpdate.objects.filter(deal = deal).order_by('-id')[0]
        stat_total = deal.get_stat_total()
        deal.s_total = stat_total
        deal.o_tspent = float(deal.s_total.seconds / 60) * float(deal.sell_price)
        deal.o_tearned = float(deal.s_total.seconds / 60) * float(deal.buy_price)
        deal.o_tprofit = deal.o_tearned - deal.o_tspent
        deal.o_tspointed = deal.pointed_sum(2)
        deal.o_tsleft = deal.o_tspointed - deal.o_tspent
        deal.o_msleft = 0
        if deal.o_tsleft > 0:
            deal.o_msleft = deal.o_tsleft / float(deal.sell_price)
        deal.o_tbpointed = deal.pointed_sum(1)
        deal.o_tbleft = deal.o_tbpointed - deal.o_tearned
        deal.o_mbleft = 0
        if deal.o_tbleft > 0:
            deal.o_mbleft = deal.o_tbleft / float(deal.buy_price)
        # Time Periods
        deal.l15min = LcrStatPeriodUpdate.objects.filter(deal = deal, period = 1).order_by('-id')[0]
        deal.l60min = LcrStatPeriodUpdate.objects.filter(deal = deal, period = 2).order_by('-id')[0]
        deal.l12h = LcrStatPeriodUpdate.objects.filter(deal = deal, period = 3).order_by('-id')[0]
        deal.l24h = LcrStatPeriodUpdate.objects.filter(deal = deal, period = 4).order_by('-id')[0]
        # Daily Breakdown
        deal.s_daily = LcrStatDailyUpdate.objects.filter(deal = deal).order_by('-date')[:7]
        return wrender('carrier_deal_details.html', {'deal': deal}, request)
    else:
        return HttpResponseRedirect('/carrier/deals/')

@login_required
def edit_deal(request, strdid):
    did = int(strdid)
    deal = LcrDeal.objects.get(id = did)
    codes = LcrCode.objects.filter(deal = deal)
    fcode = CodeForm()
    if request.method == 'POST':
        form = DealForm(request.POST, instance = deal)
        deal.is_active = request.POST['is_active']
        deal.priority = request.POST['priority']
        deal.save()
        return wrender('edit_deal.html', {'deal': deal, 'codes': codes, 'f': form, 'fc': fcode}, request)
    else:
        form = DealForm(instance = deal)
        return wrender('edit_deal.html', {'deal': deal, 'codes': codes, 'f': form, 'fc': fcode}, request)

@login_required
def add_code(request, strdid):
    did = int(strdid)
    deal = LcrDeal.objects.get(id = did)
    f = CodeForm(request.POST)
    if f.is_valid():
        code = f.save(commit = False)
        code.deal = deal
        code.save()
    return HttpResponseRedirect('/edit_deal/' + str(deal.id) + '/')

@login_required
def delete_code(request, strcid):
    cid = int(strcid)
    code = LcrCode.objects.get(id = cid)
    did = code.deal.id
    code.delete()
    return HttpResponseRedirect('/edit_deal/' + str(did) + '/')

@login_required
@staff_member_required
def monitor_edit(request, strmid):
    mid = int(strmid)
    monitor = LcrMonitor.objects.get(id = mid)
    if request.method == 'POST':
        form = MonitorForm(request.POST, instance = monitor)
        form.save()
    else:
        form = MonitorForm(instance = monitor)
    return wrender('monitor_edit.html', {'form': form, 'monitor': monitor}, request)

@login_required
@staff_member_required
def list_monitors(request):
    if request.user.get_profile().is_god():
        monitors = LcrMonitor.objects.all()
    else:
        monitors = LcrMonitor.objects.filter(deal__partner = request.user.get_profile().get_partner().partner)
    return wrender('list_monitors.html', {'monitors': monitors}, request)

@login_required
@staff_member_required
def monitor_reset(request, strmid):
    mid = int(strmid)
    monitor = LcrMonitor.objects.get(id = mid)
    monitor.status = 1
    monitor.save()
    return HttpResponseRedirect('/list_monitors/')

@login_required
@staff_member_required
def monitor_delete(request, strmid):
    mid = int(strmid)
    monitor = LcrMonitor.objects.get(id = mid)
    monitor.delete()
    return HttpResponseRedirect('/list_monitors/')

@login_required
def add_monitor(request):
    if request.method == 'POST':
        f = MonitorForm(request.POST)
        if f.is_valid():
            monitor = f.save()
            return HttpResponseRedirect('/list_monitors/')
    else:
        f = MonitorForm()
        if not request.user.get_profile().is_god():
            f.fields['deal'].queryset = LcrDeal.objects.filter(partner = request.user.get_profile().get_partner().partner)
    return wrender('add_monitor.html', {'f': f}, request)

@login_required
def add_test(request):
    if request.user.get_profile().get_partner().partner.id != 1:
                return wrender('no_feature.html', {}, request)
    if request.method == 'POST':
        f = TestForm(request.POST, prefix = 'antf')
        tnfs = TestNumberFormSet(request.POST, prefix = 'tnfs')
        if f.is_valid() and tnfs.is_valid():
            test = f.save()
            for tnf in tnfs.forms:
                tn = tnf.save(commit = False)
                if tn.number:
                    tn.test = test
                    tn.save()
            return HttpResponse('OK!')
    else:
        f = TestForm(prefix = 'antf')
        tnfs = TestNumberFormSet(prefix = 'tnfs')
    return wrender('add_test.html', {'f': f, 'tnfs': tnfs}, request)

@login_required
def view_test(request, tid):
    if request.user.get_profile().get_partner().partner.id != 1:
                return wrender('no_feature.html', {}, request)
    tid = int(tid)
    if tid == 0:
        tests = LcrTest.objects.all()
        return wrender('test_list.html', {'tests': tests}, request)
    else:
        test = LcrTest.objects.get(id = tid)
        numbers = test.lcrtestnumber_set.all()
        if request.method == 'POST':
            form = ViewTestForm(request.POST, instance = test)
            form.save()
            return wrender('test_view.html', {'test': test, 'numbers': numbers, 'form': form}, request)
        else:
            form = ViewTestForm(instance = test)
            return wrender('test_view.html', {'test': test, 'numbers': numbers, 'form': form}, request)

@login_required
def stats(request):
    if request.method == 'POST':
        f = StatsForm(request.POST)
        if f.is_valid():
            s_callstart = str(f.cleaned_data['dt_from']) + ' 00:00:00'
            s_callend = str(f.cleaned_data['dt_to']) + ' 23:59:59'
            s_callprec = 10
            s_tzinterval = int(f.cleaned_data['tz_delta'])
            q = 'SELECT CONCAT(CONVERT(LEFT(call_start - INTERVAL %d HOUR, %d), CHAR), "") AS "Date / Hour", Login AS "Customer", calls.ip_number AS "Source IP",tariffdesc AS "Route", description AS "Supplier", COUNT(*) AS "cok", (SELECT COUNT(*) FROM callsfailed WHERE callsfailed.id_client = clientsip.id_client AND callsfailed.call_start > LEFT("%s" + INTERVAL %d HOUR, %d) AND callsfailed.call_start < LEFT("%s" + INTERVAL %d HOUR, %d)) AS "cfail", ROUND(SUM(duration)/60,0) AS "Minutes", ROUND(ROUND(SUM(duration)/60,0) / COUNT(*), 2) AS "ACD" FROM dbname.calls JOIN dbname.clientsip JOIN dbname.gateways WHERE dbname.calls.id_client=dbname.clientsip.id_client AND dbname.calls.id_route=dbname.gateways.id_route AND duration>0 AND duration<35940 AND Login = "%s" AND call_start > "%s" + INTERVAL %d HOUR AND call_start < "%s" + INTERVAL %d HOUR GROUP BY LEFT(call_start - INTERVAL %d HOUR, %d),Login,calls.ip_number,tariffdesc,supplier' % (s_tzinterval, s_callprec, s_callstart, s_tzinterval, s_callprec, s_callend, s_tzinterval, s_callprec, f.cleaned_data['customer'], s_callstart, s_tzinterval, s_callend, s_tzinterval, s_tzinterval, s_callprec)
            db = _mysql.connect('stats.vs.1.2.3.4', 'root', 'pass', 'pass')
            db.query(q)
            r = db.store_result()
            o = r.fetch_row(maxrows = 0)
            ol = [list(ox) for ox in o]
            for ox in ol:
                asr = float(ox[5]) * 100 / float(ox[6])
                ox.append(asr)
            db.close()
#		return HttpResponse(q)
            return wrender('stats_complete.html', {'form': f, 'q': q, 'o': ol}, request)
    else:
        f = StatsForm()
    return wrender('stats.html', {'form': f}, request)

@login_required
def switch_stats(request):
    if request.user.get_profile().get_partner().partner.id != 1:
                return wrender('no_feature.html', {}, request)
    delta = timedelta(days = 1)
        str_begin = (date.today() - delta).isoformat()
    int_interval = 0
    int_precision = 10
    q = "SELECT CONCAT(CONVERT(LEFT(call_start - INTERVAL %d HOUR,%d), CHAR), '') AS 'Date / Hour', Login AS 'Source - Trunk', calls.ip_number AS 'Source - IP', tariffdesc AS 'Route', description AS 'Supplier', COUNT(*) AS 'Calls', ROUND(SUM(duration)/60,0) AS 'Minutes' FROM calls JOIN clientsip JOIN gateways WHERE calls.id_client=clientsip.id_client AND calls.id_route=gateways.id_route AND duration>0 AND duration<35940 AND call_start > '%s 00:00:00' + INTERVAL %d HOUR GROUP BY LEFT(call_start - INTERVAL %d HOUR,%d),Login,calls.ip_number,tariffdesc,supplier" % (int_interval, int_precision, str_begin, int_interval, int_interval, int_precision)
    switches = LcrSwitch.objects.filter(type = 1)
    lives = []
    for switch in switches:
        db = switch.get_db()
        db.query(q)
        r = db.store_result()
        o = r.fetch_row(maxrows = 0)
        db.close()
        lives.append({'switch': switch, 'o': o})
    return wrender('switch_stats.html', {'lives': lives}, request)

@login_required
def live_calls(request):
    if request.user.get_profile().is_god():
        switches = LcrSwitch.objects.filter(type = 1)
        deals = LcrDeal.objects.filter(is_active = 1)
    else:
        switches = LcrSwitch.objects.filter(type = 1, partner = request.user.get_profile().get_partner().partner)
        deals = LcrDeal.objects.filter(is_active = 1, partner = request.user.get_profile().get_partner().partner)
    lives = []
    for switch in switches:
        q = 'SELECT login, tariffdesc, COUNT(*) AS cunt FROM currentcalls LEFT JOIN clientsip ON currentcalls.id_client = clientsip.id_client GROUP BY currentcalls.id_client, tariffdesc'
        db = switch.get_db()
        db.query(q)
        r = db.store_result()
        o = r.fetch_row(maxrows = 0)
        db.close()
        lives.append({'switch': switch, 'o': o})
        deals_arr = []
        for deal in deals:
                addme = True
                if len(LcrStatPeriodUpdate.objects.filter(deal = deal, period = 2, seconds__gt = 0, dt_when__gte = datetime.datetime.now() - timedelta(hours = 1))):
            deal.last_pu2 = LcrStatPeriodUpdate.objects.filter(deal = deal, period = 2, seconds__gt = 0, dt_when__gte = datetime.datetime.now() - timedelta(hours = 1))[0]
            deal.avg_chans = int(round(deal.last_pu2.seconds / 3600))
            deals_arr.append(deal)
        else:
            addme = False
    return wrender('live_calls.html', {'lives': lives, 'deals': deals_arr}, request)

def c_request(url, fields):
    c_body = '/home/lcr/public_html/lcr/curl/body.curl'
    c_head = '/home/lcr/public_html/lcr/curl/head.curl'
    c_cookie = '/home/lcr/public_html/lcr/curl/coo.curl'
    # *** #
    f_body = open(c_body, 'wb')
    f_head = open(c_head, 'wb')
    c = pycurl.Curl()
    c.setopt(c.WRITEDATA, f_body)
    c.setopt(c.WRITEHEADER, f_head)
    c.setopt(c.COOKIEFILE, c_cookie)
    c.setopt(c.COOKIEJAR, c_cookie)
    c.setopt(c.URL, url)
    c.setopt(c.FOLLOWLOCATION, 0)
    if len(fields):
        c.setopt(c.POSTFIELDS, urllib.urlencode(fields))
    c.perform()
    f_body.close()
    f_head.close()
    c.close()
    # *** #
    f = open(c_body, 'r')
    ret = f.read()
    f.close()
    return ret

@login_required
@staff_member_required
def cdrgen_index(request):
    if request.method == 'POST':
        f = CDRGenForm(request.POST)
        if f.is_valid():
            c = f.save(commit = False)
            c.partner = request.user.get_profile().get_partner().partner
            c.save()
    else:
        f = CDRGenForm()
    cdrs = LcrCDRGen.objects.all()
    return wrender('cdrgen_index.html', {'cdrs': cdrs, 'f': f}, request)

@login_required
def ems_index(request):
    if request.user.get_profile().get_partner().partner.id != 1:
                return wrender('no_feature.html', {}, request)
    ems_login = 'ems_login'
    ems_pass = 'ems_password'
    #
    c_request('https://www.emsfinancialservices.com/portal/usr_login.php', {})
    #
    pf = {'action': 'chackUser', 'user': ems_login, 'pass': ems_pass}
    r = c_request('https://www.emsfinancialservices.com/portal/ajax/ajax_usr_login.php', pf)
    #
    r = c_request('https://www.emsfinancialservices.com/portal/index.php', {})
    rx = re.search("My Company Balance <span>\$ (.*?)<", r)
    strCompanyBalance = rx.groups()[0]
    rx = re.search("Available Balance <span style='font-weight:bold;'>\$ (.*?)<", r)
    strAvailableBalance = rx.groups()[0]
    rx = re.search("Total Pointed In <span>\$ (.*?)<", r)
    strTotalPointedIn = rx.groups()[0]
    rx = re.search("Total Pointed Out <span>\$ (.*?)<", r)
    strTotalPointedOut = rx.groups()[0]
    strInfo = {
        'cBalance': 	strCompanyBalance,
        'aBalance': 	strAvailableBalance,
        'pIn':		strTotalPointedIn,
        'pOut':		strTotalPointedOut,
    }
    return wrender('ems_index.html', {'strInfo': strInfo}, request)

@login_required
def bank_index(request):
    # Removed for Security Reasons

def ragents_emails(request):
    emails_z = []
    emails_a = []
    emails_nz = []
    zs = LcrRetailARASipFriend.objects.filter(ipaddr__isnull = False)
    for z in zs:
        emails_z.append(z.agent.user.email)
    aa = LcrRetailAgent.objects.all()
    for a in aa:
        emails_a.append(a.user.email)
    for e in emails_a:
        if not e in emails_z:
            emails_nz.append(e)
    return wrender('ragents_emails.html', {'e_z': emails_z, 'e_nz': emails_nz, 'e_a': emails_a, 'ne_z': len(emails_z), 'ne_nz': len(emails_nz), 'ne_a': len(emails_a)}, request)

def agents_action_temp(request):
    if request.user.get_profile().get_partner().partner.id != 1:
                return wrender('no_feature.html', {}, request)

def agent_training(request):
    return wrender('agent_training.html', {}, request)

def agent_help(request):
    return wrender('agent_help.html', {}, request)

def agent_materials(request):
    return wrender('agent_materials.html', {}, request)

def agent_faq(request):
    return wrender('agent_faq.html', {}, request)

def agent_custadd(request, src, lid):
    if request.method == 'POST':
        cf = RetailCandidateForm(request.POST)
        if cf.is_valid():
            c = cf.save(commit = False)
            c.source_type = 1
            c.operator = request.user
            c.status = 99
            c.save()
            cf.save_m2m()
            return HttpResponseRedirect('/agent/custconf/' + str(c.id) + '/')
    else:
        if src == 'pan' and int(lid) != 0 and len(LcrRetailCandidate.objects.filter(operator = request.user, id = int(lid))):
            cf = RetailCandidateForm(instance = LcrRetailCandidate.objects.get(id = int(lid)))
        else:
            cf = RetailCandidateForm()
            if src == 'web' and int(lid) != 0 and len(LcrRetailCandidateWC.objects.filter(operator_id = request.user.id, id = int(lid))):
                wl = LcrRetailCandidateWC.objects.get(id = int(lid))
                first_name = wl.name or ''
                email = wl.email or ''
                phone = wl.phone or ''
                cf = RetailCandidateForm({'first_name': first_name, 'email': email, 'phone': phone})
            elif src == 'rel' and int(lid) != 0 and len(LcrRetailCallBack.objects.filter(agent = request.user.id, id = int(lid))):
                wl = LcrRetailCallBack.objects.get(id = int(lid)).line
                first_name = wl.first_name or ''
                last_name = wl.last_name or ''
                phone = wl.phone_1 or ''
                cf = RetailCandidateForm({'first_name': first_name, 'last_name': last_name, 'phone': phone})
                pbx_callback(request, int(lid))
    cbf = RetailCallBackForm()
    return wrender('agent_custadd.html', {'cf': cf, 'cbf': cbf}, request)

def agent_leads(request):
    leads_web = LcrRetailCandidateWC.objects.filter(operator_id = request.user.id)
    leads_pan = LcrRetailCandidate.objects.filter(operator = request.user, status = 98)
    leads_rel = LcrRetailCallBack.objects.filter(agent = request.user)
    return wrender('agent_leads.html', {'leads_web': leads_web, 'leads_pan': leads_pan, 'leads_rel': leads_rel}, request)

def agent_script(request, page):
    jsnull = 'javascript:void(0);'
    lang = 'en'
    if re.search('[^\w]', page):
        return HttpResponse('')
    else:
        return wrender('ap/en_' + page + '.html', {'jn': jsnull, 'lang': lang}, request)

def agent_custconf(request, cid):
    try:
        c = LcrRetailCandidate.objects.get(id = int(cid))
    except LcrRetailCandidate.DoesNotExist:
        return HttpResponseRedirect('/')
    if c.operator != request.user:
        return HttpResponseRedirect('/')
    if request.method == 'POST':
        cf = RetailCandidateStatusForm(request.POST, instance = c)
        if cf.is_valid():
            cf.save()
            return wrender('agent_custconf_ok.html', {'c': c}, request)
    else:
        ver = telemark_index(c)
        cf = RetailCandidateStatusForm(instance = c)
    return wrender('agent_custconf.html', {'cf': cf, 'c': c, 'ver': ver}, request)

def agent_call(request, asip, dline):
    # TODO: DO NOT REMOVE THE PREVIOUS CALLS!!
    # TODO: ADD TIMESTAMP!!
    if asip == '0':
        if len(LcrRetailRoboRequest.objects.filter(exten = dline)) == 0:
            req = LcrRetailRoboRequest(exten = dline)
            req.save()
        return HttpResponse('OK')
    try:
        ara = LcrRetailARASipFriend.objects.get(name = re.search('(\d+)', base64.b64decode(asip)).group())
    except LcrRetailARASipFriend.DoesNotExist:
        return HttpResponse('ERR_ARASIPNOTFOUND')
    u = ara.agent.user
    excalls = LcrRetailRoboCall.objects.filter(agent = u)
    if len(excalls):
        for ex in excalls:
            ex.delete()
    datas = LcrRetailData.objects.filter(phone_1 = dline[2:])
    if len(datas):
        call = LcrRetailRoboCall(agent = u, line = datas[0])
        call.save()
        req = LcrRetailRoboRequest(exten = dline)
        req.aid = u.id
        req.save()
        return HttpResponse('OK')
    else:
        return HttpResponse('ERR_DATAPHONENOTFOUND')

def agent_cbadd(request):
    cbf = RetailCallBackForm(request.POST)
    try:
        call = LcrRetailRoboCall.objects.get(agent = request.user)
    except LcrRetailRoboCall.DoesNotExist:
        return HttpResponse('ERROR: Call Not Found')
    if cbf.is_valid():
        cb = cbf.save(commit = False)
        cb.agent = request.user
        cb.line = call.line
        cb.save()
        return HttpResponse('OK')
    else:
        return HttpResponse('ERROR: Form Incomplete')

def ajx_ag_data(request):
    try:
        call = LcrRetailRoboCall.objects.get(agent = request.user)
    except LcrRetailRoboCall.DoesNotExist:
        return HttpResponse('{}')
    l = call.line
    dsl = 'DSL'
    ds = LcrRetailDSL.objects.filter(number_from__lte = int(l.phone_1), number_to__gte = int(l.phone_1))
    if len(ds):
        d = ds[0]
        if re.match('1', d.techs):
            dsl = 'DSL: <b>FAST</b> (20 Mbps)'
        elif (re.match('2', d.techs) or re.match('3', d.techs)):
            dsl = 'DSL: <b>SLOW</b> (8 Mbps, <span>+12 GBP</span>)'
    dsl += ' <a href="javascript:void(0);" id="dacb">[ REDIAL ]</a>'
    rs = {
        'first_name':	l.first_name or '',
        'last_name':	l.last_name or '',
        'phone':	l.phone_1 or '',
        'dsl':		dsl,
        'address':	(l.addr_type or '') + ' ' + (l.addr_name or '') + ' ' + (l.addr_no or '') + ' ' + (l.town or '')
    }
    return HttpResponse(simplejson.dumps(rs))

def pbx_join_umeetme(request, str_num):
    try:
        call = LcrRetailRoboCall.objects.get(agent = request.user)
    except LcrRetailRoboCall.DoesNotExist:
        return HttpResponse('ERR: Call not found')
    l = call.line
    acmPrompt = 'Asterisk Call Manager/1.1'
    tn = telnetlib.Telnet('pbx.ip.1.2.3.4', 6969)
    tn.read_until(acmPrompt)
    tn.write('Action: login\r\nUsername: lcr\r\nSecret: secret\r\nEvents: off\r\n\r\n')
    tn.write('Action: Command\r\nCommand: meetme list\r\n\r\n')
    t = tn.read_until('--END')
    p_meetme = '34%s    000(\d)\t      N\/A        (\d{2}):(\d{2}):(\d{2})  Dynamic   No    \n' % (l.phone_1, )
    mms = re.search(p_meetme, t)
    if mms:
        parties = mms.groups()[0]
        if parties > 0:
            q = 'channel originate SIP/99901%s@slave41 extension 34%s@cont-join-meetme' % (str_num, l.phone_1)
            tn.write(str('Action: Command\r\nCommand: %s\r\n\r\n' % (q, )))
            tn.close()
            return HttpResponse('OK')
        else:
            return HttpResponse('ERR: Not enough people in the conference')
    else:
        return HttpResponse('ERR: Conference not found')

def ajx_ag_ver(request):
    return pbx_join_umeetme(request, 'ver_number')

def ajx_ag_ass(request):
    return pbx_join_umeetme(request, 'ass_number')

def pbx_callback(request, cbid):
    try:
        cb = LcrRetailCallBack.objects.get(id = int(cbid))
    except LcrRetailCallBack.DoesNotExist:
        return False
    if cb.agent != request.user:
        return False
    acmPrompt = 'Asterisk Call Manager/1.1'
    tn = telnetlib.Telnet('pbx.ip.1.2.3.4', 6969)
    tn.read_until(acmPrompt)
    tn.write('Action: login\r\nUsername: lcr\r\nSecret: secret\r\nEvents: off\r\n\r\n')
    tn.write('Action: Command\r\nCommand: meetme list\r\n\r\n')
    t = tn.read_until('--END')
    q1 = 'channel originate SIP/%s extension 34%s@cont-join-meetme' % (request.user.get_profile().get_agent_ara().name, cb.line.phone_1)
    q2 = 'channel originate SIP/9990134%s@slave41 extension 34%s@cont-join-meetme' % (cb.line.phone_1, cb.line.phone_1)
    tn.write(str('Action: Command\r\nCommand: %s\r\n\r\n' % (q1, )))
    t = tn.read_until('--END')
    tn.write(str('Action: Command\r\nCommand: %s\r\n\r\n' % (q2, )))
    tn.close()
    return True

def search_code(request):
    str_len = 4
    routes = LcrRoute.objects.filter(partner = request.user.get_profile().get_partner().partner, code__startswith = request.GET['term'], code__regex = r'^\d{1,6}$').order_by('code')
    r_arr = []
    for route in routes:
        rr = {'id': route.code, 'label': route.code + '(' + route.name + ')', 'value': route.code, 'name': route.name}
        if not len(r_arr) or rr['id'] != r_arr[-1]['id']:
            r_arr.append(rr)
    return r_arr

#@login_required
#@staff_member_required
def ajax_mera_calls(request):
    lastupdate = LcrMVTSCalls.objects.all().order_by('-id')[0]
    json_calls = lastupdate.json_calls
        calls = simplejson.loads(json_calls)
        calls_customer = {}
    ret_calls_customer = {}
        calls_supplier = {}
        for call in calls:
            try:
                    if call['call_state'] in ['connected', 'trying']:
                            customer = call['incoming_gateway_name']
                                supplier = call['outgoing_gateway_name']
                dialpeer = call['dialpeer']
                ic_time = 0
                if call['call_state'] == 'connected':
                    ic_time = int(call['incall_time'])
                                if not customer in calls_customer:
                                    calls_customer[customer] = {}
                if not dialpeer in calls_customer[customer]:
                    calls_customer[customer][dialpeer] = {}
                if not 'connected' in calls_customer[customer][dialpeer]:
                    calls_customer[customer][dialpeer]['connected'] = []
                if not 'trying' in calls_customer[customer][dialpeer]:
                    calls_customer[customer][dialpeer]['trying'] = []
                                calls_customer[customer][dialpeer][call['call_state']].append(ic_time)
                                if not supplier in calls_supplier:
                                    calls_supplier[supplier] = {}
                if not dialpeer in calls_supplier[supplier]:
                    calls_supplier[supplier][dialpeer] = {}
                if not 'connected' in calls_supplier[supplier][dialpeer]:
                    calls_supplier[supplier][dialpeer]['connected'] = []
                if not 'trying' in calls_supplier[supplier][dialpeer]:
                    calls_supplier[supplier][dialpeer]['trying'] = []
                                calls_supplier[supplier][dialpeer][call['call_state']].append(ic_time)
        except TypeError:
                    pass
    ret = {'calls_customer': calls_customer, 'calls_supplier': calls_supplier, 'dt_when': lastupdate.dt_when.isoformat()}
        return HttpResponse(simplejson.dumps(ret))

def robo01_answer(request, str_phone):
    """
    robo = LcrRobo01.objects.filter(phone = str_phone)[0]
    robo.call_placed = datetime.datetime.now()
    robo.call_answered = 1
    robo.save()
    """
    robo = LcrRetailData.objects.filter(phone_1 = str_phone[2:])[0]
    robo.placed += 1
    robo.save()
    return HttpResponse('OK')

def robo01_response(request, str_phone, response):
    robo = LcrRetailData.objects.filter(phone_1 = str_phone[2:])[0]
    robo.response = 1
    robo.save()
    return HttpResponse('OK')

def robo01_x(request):
    robo = LcrRobo01.objects.filter(call_answered = 1)
    res = robo.exclude(responses__isnull = True)
    str_res = ''
    for r in res:
        str_res += '%s;%s;%s;%s\r\n' % (r.phone, r.name, r.responses, r.call_placed)
    return HttpResponse(str_res)

@login_required
@staff_member_required
def mvts_report(request):
    conf_days = 7
    reps = LcrMVTSReport.objects.filter(dt_day__gte = datetime.date.today() - datetime.timedelta(days = conf_days))
    customers = []
    for rep in reps:
        if not rep.customer in customers:
            customers.append(rep.customer)
    cds = {}
    cda = {}
    cds_cda = []
    res = []
    days = []
    dt_token = datetime.date.today() - datetime.timedelta(days = conf_days)
        while dt_token < datetime.date.today():
        days.append(dt_token.isoformat())
        dt_token += datetime.timedelta(days = 1)
    for customer in customers:
        cds[customer] = []
        cda[customer] = []
    for rep in reps:
        if not rep.destination in cds[rep.customer]:
            cds[rep.customer].append(rep.destination)
        if not rep.destination.split('_')[0] in cda[rep.customer]:
            cda[rep.customer].append(rep.destination.split('_')[0])
    for customer in customers:
        customer_list = []
        for ca in cda[customer]:
            abbrev_list = {}
            abbrev_list['subs'] = []
            total_sec = {}
            total_ref_sec = {}
            calls = {}
            failed = {}
            for day in days:
                total_sec[day] = 0
                calls[day] = 0
                failed[day] = 0
                total_ref_sec[day] = 0
            for cd in cds[customer]:
                if cd.split('_')[0] == ca:
                    destination_list = []
                    dt_token = datetime.date.today() - datetime.timedelta(days = conf_days)
                    while dt_token < datetime.date.today():
                        rep = reps.filter(customer = customer, destination = cd, dt_day = dt_token)
                        if len(rep):
                            total_sec[dt_token.isoformat()] += rep[0].seconds
                            calls[dt_token.isoformat()] += rep[0].calls
                            failed[dt_token.isoformat()] += rep[0].failed
                            refrep = LcrMVTSReport.objects.filter(dt_day = dt_token - datetime.timedelta(days = 1), customer = customer, destination = cd)
                            if len(refrep) and refrep[0].seconds:
                                total_ref_sec[dt_token.isoformat()] += refrep[0].seconds
                                change = (rep[0].seconds - refrep[0].seconds) * 100 / refrep[0].seconds
                            else:
                                if rep[0].seconds:
                                    change = 100
                                else:
                                    change = 0
                            if change >= 0:
                                css = 'GR'
                            else:
                                css = 'RD'
                            if rep[0].calls:
                                if rep[0].failed:
                                    asr = (rep[0].calls * 100.0) / (rep[0].calls + rep[0].failed)
                                else:
                                    asr = 100.0
                            else:
                                asr = 0.0
                            if rep[0].seconds and rep[0].calls:
                                acd = rep[0].seconds / rep[0].calls
                            else:
                                acd = 0.0
                            result = {
                                'minutes':	rep[0].seconds/60,
                                'change':	change,
                                'css':		css,
                                'asr':		asr,
                                'acd':		acd,
                                'failed':	rep[0].failed
                            }
                        else:
                            refrep = LcrMVTSReport.objects.filter(dt_day = dt_token - datetime.timedelta(days = 1), customer = customer, destination = cd)
                                                        if len(refrep):
                                total_ref_sec[dt_token.isoformat()] += refrep[0].seconds
                            result = {
                                'minutes':	0,
                                'change':	0,
                                'css':		'NO',
                                'asr':		0,
                                'acd':		0,
                                'failed':	0
                            }
                        dt_token += datetime.timedelta(days = 1)
                        destination_list.append((dt_token.isoformat(), result))
                    abbrev_list['subs'].append((cd, destination_list))
                abbrev_list['total'] = []
                for dt_token in days:
                    iso = dt_token
                    r_failed = failed[iso]
                    if calls[iso]:
                        if failed[iso]:
                            asr = (calls[iso] * 100.0) / (calls[iso] + failed[iso])
                        else:
                            asr = 100.0
                    else:
                        asr = 0.0
                    if total_sec[iso] and calls[iso]:
                        acd = total_sec[iso] / calls[iso]
                    else:
                        acd = 0.0
                    if total_ref_sec[iso]:
                        change = (total_sec[iso] - total_ref_sec[iso]) * 100 / total_ref_sec[iso]
                    else:
                        if total_sec[iso]:
                            change = 100
                        else:
                            change = 0
                    if change > 0:
                        css = 'GR'
                    elif change == 0:
                        css = 'NO'
                    elif change < 0:
                        css = 'RD'
                    result = {
                        'minutes':	total_sec[iso]/60,
                        'change':	change,
                        'css':		css,
                        'asr':		asr,
                        'acd':		acd,
                        'failed':	r_failed
                    }
                    abbrev_list['total'].append((iso, result))
            customer_list.append((ca, abbrev_list))
        res.append((customer, customer_list))
    return wrender('mvts_report.html', {'res': res, 'days': days, 'customers': customers, 'cds': cds}, request)

def mvts_get_alert():
    last_sess = LcrMVTSAlertSession.objects.order_by('-id')[0]
    prev_sess = LcrMVTSAlertSession.objects.order_by('-id')[1]
    ret = []
    chan_limit = 10
    chan_divider = 1800.0
    for check in LcrMVTSAlertCheck.objects.filter(session = prev_sess):
        last_checks = LcrMVTSAlertCheck.objects.filter(customer = check.customer, destination = check.destination, session = last_sess)
        if len(last_checks):
            last_check = last_checks[0]
            change = (last_check.seconds - check.seconds) * 100 / check.seconds
            descr = ''
            if change <= -40:
                status = 'ALERT'
                descr = 'Prev sess: %d min, curr sess: %d min' % (check.seconds/60, last_check.seconds/60)
            else:
                status = 'OK'
            chan_p = check.seconds / chan_divider
            chan_l = last_check.seconds / chan_divider
            if chan_p < chan_limit:
                status = 'i' + status
            if check.calls:
                asr_p = check.calls * 100.0 / (check.calls + check.failed)
                acd_p = check.seconds * 1.0 / check.calls
            else:
                asr_p = 0.0
                acd_p = 0.0
            if last_check.calls:
                asr_l = last_check.calls * 100.0 / (last_check.calls + last_check.failed)
                acd_l = last_check.seconds * 1.0 / last_check.calls
            else:
                asr_l = 0.0
                acd_l = 0.0
            if asr_p and asr_l:
                asr_ch = int((asr_l - asr_p) * 100 / asr_p)
                acd_ch = int((acd_l - acd_p) * 100 / acd_p)
            else:
                asr_ch = 0
                acd_ch = 0
            report = {
                'check':	check,
                'status':	status,
                'change':	change,
                'descr':	descr,
                'ch_p':		chan_p,
                'ch_l':		chan_l,
                'asr_p':	asr_p,
                'asr_l':	asr_l,
                'asr_ch':	asr_ch,
                'acd_p':	acd_p,
                'acd_l':	acd_l,
                'acd_ch':	acd_ch
            }
        else:
            chan_p = check.seconds / chan_divider
            if chan_p < chan_limit:
                status = 'iGONE'
            else:
                status = 'GONE'
            if check.calls:
                                asr_p = check.calls * 100.0 / (check.calls + check.failed)
                                acd_p = check.seconds * 1.0 / check.calls
                        else:
                                asr_p = 0.0
                                acd_p = 0.0
            report = {
                'check':	check,
                'status':	status,
                'change':	0,
                'descr':	'Traffic stopped.',
                'ch_p':		chan_p,
                'ch_l':		0,
                'asr_p':	asr_p,
                'asr_l':	0.0,
                'asr_ch':	0,
                'acd_p':	acd_p,
                'acd_l':	0.0,
                'acd_ch':	0
            }
        ret.append(report)
    ret.sort(key = lambda x: x['ch_p'], reverse = True)
    return ret

@login_required
@staff_member_required
def mvts_alert(request):
    return wrender('mvts_alert.html', {'ret': mvts_get_alert()}, request)

#@login_required
#@staff_member_required
def mvts_calls(request):
    return wrender('mvts_calls.html', {}, request)

@login_required
def ajx_ac_code(request):
    routes = search_code(request)
    return HttpResponse(simplejson.dumps(routes))

@login_required
def ajx_sc_code(request):
    routes = search_code(request)
    azs = LcrAZ.objects.filter(partner = request.user.get_profile().get_partner().partner)
    r_azs = {}
    for az in azs:
        r_azs[az.id] = az.supplier.name
    r_arr = []
    for route in routes:
        route_offers = {}
        for az in azs:
            offer = request.user.lcrroute_set.filter(code = route['id'], az = az)
            if len(offer):
                route_offers[az.id] = float(offer[0].price)
            else:
                route_offers[az.id] = 0
        r_arr.append({'code': route['id'], 'dname': route['name'], 'offers': route_offers})
    ret = {'azs': r_azs, 'arr': r_arr}
    return HttpResponse(simplejson.dumps(ret))

@login_required
@staff_member_required
def ajx_rc_term(request):
    terms = request.GET['term'].split()
    qs = []
    for term in terms:
        qs.append(Q(name__icontains = term) | Q(vat_id__icontains = term))
    q = reduce(operator.or_, qs)
    rcs = LcrRetailCustomer.objects.filter(partner = request.user.get_profile().get_partner().partner).filter(q)
    arr_rcs = []
    for rc in rcs:
        arr_rcs.append(rc)
    for term in terms:
        numbers = LcrRetailCustomerNumber.objects.filter(cservice__customer__partner = request.user.get_profile().get_partner().partner, number = term)
        if len(numbers):
            for number in numbers:
                if arr_rcs.count(number.cservice.customer) == 0:
                    arr_rcs.append(number.cservice.customer)
    r_rcs = []
    for rc in arr_rcs:
        rc_arr = {'id': rc.id, 'name': rc.name, 'vat_id': rc.vat_id}
        r_rcs.append(rc_arr)
    return HttpResponse(simplejson.dumps(r_rcs))

def col_is_name(v):
    return True
    return unicode(v).isalnum()

def col_is_code(v):
    match = False
    try:
        match = (float(int(v)) == v)
    except ValueError:
        return False
    return match

def col_is_price(v):
    match = False
    try:
        match = (float(v) == float(v))
    except ValueError:
        return False
    return match

def bt_get_destination(dialed_num):
    e164_found = False
    for i in range(len(dialed_num)):
        if (not e164_found) and (i != len(dialed_num)):
            strip = len(dialed_num) - i
            anal_e164 = dialed_num[0:strip]
            dests = LcrBTDestination.objects.filter(prefix = anal_e164)
            if len(dests):
                return dests[0]
    return False

@login_required
@staff_member_required
def uploadAZ(request):
    if request.method == 'POST':
        form = AZForm(request.POST, request.FILES)
        sform = AZParseForm(request.POST)
        if form.is_valid() and sform.is_valid():
            xls = request.FILES['file'].read()
            x = open_workbook(file_contents = xls)
            sheet = x.sheet_by_index(0)
            az = form.save(commit = False)
            az.user = request.user
            az.partner = request.user.get_profile().get_partner().partner
            az.save()
            col_name = sform.cleaned_data['col_name'] - 1
            col_code = sform.cleaned_data['col_code'] - 1
            col_price = sform.cleaned_data['col_price'] - 1
            sret = '<pre>'
            for row in range(sheet.nrows):
                if col_is_name(sheet.cell(row, col_name).value) and col_is_code(sheet.cell(row, col_code).value) and col_is_price(sheet.cell(row, col_price).value):
                    route = LcrRoute(user = request.user, partner = request.user.get_profile().get_partner().partner)
                    route.code = str(int(sheet.cell(row, col_code).value))
                    route.name = unicode(sheet.cell(row, col_name).value)
                    route.price = str(sheet.cell(row, col_price).value)
                    route.az = az
                    route.save()
            return HttpResponseRedirect('/az/')
    else:
        form = AZForm()
        if not request.user.get_profile().is_god():
            form.fields['supplier'].queryset = LcrCarrier.objects.filter(partner = request.user.get_profile().get_partner().partner)
        sform = AZParseForm()
    return wrender('uploadAZ.html', {'form': form, 'sform': sform}, request)

@login_required
@staff_member_required
def email_index(request):
    if request.method == 'POST':
        sjf = EmailSubmitJobForm(request.POST)
        if sjf.is_valid():
            sj = sjf.save(commit = False)
            sj.partner = request.user.get_profile().get_partner().partner
            sj.save()
    sjobs = LcrEmailSubmitJob.objects.filter(partner = request.user.get_profile().get_partner().partner)
    sjf = EmailSubmitJobForm()
    return wrender('email_index.html', {'sjobs': sjobs, 'sjf': sjf}, request)
