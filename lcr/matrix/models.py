# -*- coding: utf-8 -*-

from django.db import models
from django.db.models import Sum
from django.contrib import admin
from django.forms import ModelForm
from django.forms.formsets import formset_factory
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django import forms
from django.template.defaultfilters import slugify
from django.contrib.localflavor.es.forms import *
import re
import _mysql
import datetime

# --- MODELS --- #

class LcrCurrency(models.Model):
    full_name = models.CharField(max_length = 100)
    abbr_name = models.CharField(max_length = 10)
    symb_name = models.CharField(max_length = 10)

    def __unicode__(self):
        return self.full_name + ' (' + self.abbr_name + ')'

class LcrAZ(models.Model):
    dt_when = models.DateTimeField(auto_now_add = True)
    user = models.ForeignKey(User)
    supplier = models.ForeignKey('LcrCarrier')
    currency = models.ForeignKey('LcrCurrency')
    file = models.FileField(upload_to = 'a2z')
    partner = models.ForeignKey('LcrPartner')

    def rcount(self):
        return len(self.lcrroute_set.all())


CH_NUMPAR = (
    (1001, 'Robo.Interval'),
)		

class LcrNumParameter(models.Model):
    pkey = models.IntegerField(choices = CH_NUMPAR)
    pval = models.IntegerField(default = 0)

CH_NUMLOG = (
    (2001, 'Robo.AgentsAvail'),
    (2002, 'Robo.IntervalSet')
)

class LcrNumLog(models.Model):
    pkey = models.IntegerField(choices = CH_NUMLOG)
    pval = models.IntegerField(default = 0)
    dt_when = models.DateTimeField(auto_now_add = True)

# NOT INCLUDED IN REMOTE DISTRO!!!

CH_REG_STATUS = (
    (1, 'New'),
    (2, 'Processing'),
    (3, 'Rejected'),
    (4, 'Completed')
)

CH_REG_LCRTYPE = (
    (1, 'Full License - Own Infrastructure'),
    (2, 'Offline License - Own Infrastructure'),
    (3, 'Full License - Dedicated Server'),
    (4, 'Modular License - CDR Reconciliation'),
    (5, 'Modular License - CDR Tool'),
    (6, 'Modular License - NOC Website')
)

CH_REG_PAYTYPE = (
    (1, 'Escrow - EMS'),
    (2, 'Escrow - Traffic Exchange'),
    (3, 'Escrow - Arbinet / RouteTrader / etc.'),
    (4, 'PayPal'),
    (5, 'Bank Transfer - SWIFT (USD)'),
    (6, 'Other')
)

CH_REG_SWITCH_TYPE = (
    (1, 'LCR Switch (included in Full License)'),
    (2, 'Asterisk'),
    (3, 'MVTS Pro / MVTS II'),
    (4, 'NextOne'),
    (5, 'OpenSER / Kamailo'),
    (6, 'Freeswitch'),
    (7, 'VoipSwitch'),
    (8, 'Cisco iOS (w/Radius Accounting)'),
    (99, 'Mixed Switches (PEX - Describe below)')
)

class LcrRegistration(models.Model):
    dt_when = models.DateTimeField(auto_now_add = True)
    reg_ip = models.CharField(max_length = 20)
    token = models.CharField(max_length = 200)
    remote_user = models.CharField(blank = True, max_length = 200)
    remote_pass = models.CharField(blank = True, max_length = 200)
    sign_name = models.CharField(blank = True, max_length = 100)
    sign_yn = models.IntegerField(default = 0)
    sign_agent = models.CharField(blank = True, max_length = 250)
    lcr_ip = models.CharField(blank = True, max_length = 20)
    status = models.IntegerField(default = 1, choices = CH_REG_STATUS)
    cust_name = models.CharField(max_length = 250)
    cust_addr = models.CharField(max_length = 250)
    cust_country = models.CharField(max_length = 100)
    cust_email = models.CharField(max_length = 100)
    cust_phone = models.CharField(max_length = 100)
    cust_vat = models.CharField(max_length = 50, default = '', blank = True)
    cust_rep = models.CharField(max_length = 100)
    chk_rep_id = models.BooleanField()
    cust_rep_id_file = models.FileField(blank = True, upload_to = 'a2z')
    cust_pay_type = models.IntegerField(default = 1, choices = CH_REG_PAYTYPE)
    cust_pay_account = models.CharField(max_length = 200)
    chk_srv_lcr = models.BooleanField()
    chk_srv_lcr_type = models.IntegerField(default = 1, choices = CH_REG_LCRTYPE)
    chk_srv_noc = models.BooleanField()
    chk_srv_tts = models.BooleanField()
    chk_srv_ivr = models.BooleanField()
    chk_pex = models.BooleanField()
    switch_type = models.IntegerField(default = 1, choices = CH_REG_SWITCH_TYPE)
    switch_version = models.CharField(max_length = 50)
    srv_information = models.TextField()
    srv_volume = models.CharField(max_length = 200, blank = True, default = '')

class LcrRegistrationSignature(models.Model):
    dt_when = models.DateTimeField(auto_now_add = True)
    reg = models.ForeignKey('LcrRegistration')
    license_text = models.TextField(blank = True)
    sig_ip = models.CharField(max_length = 20)
    sig_agent = models.CharField(max_length = 200)
    sig_name = models.CharField(max_length = 200)

class LcrRegistrationForm(ModelForm):

    class Meta:
        model = LcrRegistration
        exclude = ('dt_when', 'reg_ip', 'token', 'remote_user', 'remote_pass', 'lcr_ip', 'status', 'sign_name', 'sign_yn', 'sign_agent' )

class LcrRegistrationSignatureForm(ModelForm):

    class Meta:
        model = LcrRegistrationSignature
        exclude = ('dt_when', 'reg', )

# /

CH_YESNO = (
    (1, 'No'),
    (2, 'Yes'),
)

CH_BOOL = (
    (0, 'No'),
    (1, 'Yes'),
)

CH_IPCONNTYPE = (
    (1, 'Internet'),
    (2, 'OpenVPN'),
    (3, 'IPSEC'),
    (4, 'PPP / PPTP'),
    (5, 'EoIP'),
    (19, 'Other VPN'),
    (99, 'LAN'),
)

CH_PROTOCOL = (
    (1, 'SIP / UDP'),
    (2, 'SIP / TCP'),
)

CH_ROLE = (
    (1, 'Customer'),
    (2, 'Supplier'),
    (3, 'Both'),
)

CH_CODEC = (
    (1, 'G729'),
    (2, 'G711 (alaw)'),
    (3, 'G711 (ulaw)'),
    (4, 'G723'),
    (5, 'GSM'),
)

CH_PERIOD = (
    (1, '15 MINUTE'),
    (2, '60 MINUTE'),
    (3, '12 HOUR'),
    (4, '24 HOUR'),
)

CH_PARTY = (
    (1, 'Buyer'),
    (2, 'Seller'),
)

class LcrPoint(models.Model):
    deal = models.ForeignKey('LcrDeal', verbose_name = 'Deal Funded')
    party = models.IntegerField(default = 1, verbose_name = 'Funded Party', choices = CH_PARTY)
    amount = models.DecimalField(max_digits = 14, decimal_places = 4, verbose_name = 'Amount Pointed')
    dt_when = models.DateTimeField(auto_now_add = True)
    comment = models.TextField(blank = True, verbose_name = 'Comment')
    ident = models.CharField(max_length = 200, blank = True, verbose_name = 'Ident Field')

class LcrMonitor(models.Model):
    deal = models.ForeignKey('LcrDeal', verbose_name = 'Deal Monitored')
    period = models.IntegerField(verbose_name = 'Time Period', choices = CH_PERIOD)
    asr = models.IntegerField(default = 0, verbose_name = 'Min. ASR')
    acd = models.IntegerField(default = 0, verbose_name = 'Min. ACD')
    vol = models.IntegerField(default = 0, verbose_name = 'Min. Volume')
    status = models.IntegerField(default = 1, verbose_name = 'Is Trigerred?', choices = CH_YESNO)
    dt_when = models.DateTimeField(auto_now_add = True)

    def __unicode__(self):
        return unicode(self.deal)

class LcrStatH(models.Model):
    deal = models.ForeignKey('LcrDeal')
    dt_when = models.DateTimeField(auto_now_add = False)
    calls_ok = models.BigIntegerField()
    calls_fail = models.BigIntegerField()
    seconds = models.BigIntegerField()
    ppm = models.DecimalField(max_digits = 14, decimal_places = 4, default = '0.0000')

    def asr(self):
        fasr = float(0)
        if (self.calls_ok + self.calls_fail) > 0:
            fasr = float(self.calls_ok) / (self.calls_ok + self.calls_fail) * 100
        return fasr

    def acd(self):
        if self.calls_ok:
            return (self.seconds / self.calls_ok)
        else:
            return 0

    def minutes(self):
        return float(self.seconds / 60)

    def chans(self):
        return int(self.seconds / 3600)

    def trend(self):
        cps = LcrStatH.objects.filter(deal = self.deal, dt_when = self.dt_when - datetime.timedelta(hours = 1))
        if len(cps):
            cp = cps[0]
            if self.seconds > cp.seconds:
                return '+'
            elif self.seconds < cp.seconds:
                return '-'
            else:
                return '0'
        else:
            return '0'

class LcrStatPeriodUpdate(models.Model):
    deal = models.ForeignKey('LcrDeal')
    period = models.IntegerField(choices = CH_PERIOD)
    calls_ok = models.BigIntegerField()
    calls_fail = models.BigIntegerField()
    seconds = models.BigIntegerField()
    acd = models.FloatField()
    dt_when = models.DateTimeField(auto_now_add = True)

    def asr(self):
        fasr = float(0)
        if (self.calls_ok + self.calls_fail) > 0:
            fasr = float(self.calls_ok) / (self.calls_ok + self.calls_fail) * 100
        return fasr

    def minutes(self):
        return float(self.seconds / 60)

class LcrStatDailyUpdate(models.Model):
    deal = models.ForeignKey('LcrDeal')
    date = models.DateField(auto_now = False)
    calls_ok = models.BigIntegerField()
    calls_fail = models.BigIntegerField()
    seconds = models.BigIntegerField()
    acd = models.FloatField()
    dt_when = models.DateTimeField(auto_now_add = True)

    def asr(self):
        fasr = float(0)
        if (self.calls_ok + self.calls_fail) > 0:
            fasr = float(self.calls_ok) / (self.calls_ok + self.calls_fail) * 100
        return fasr

    def minutes(self):
        return float(self.seconds / 60)

class LcrStatDailyDelta(models.Model):
    deal = models.ForeignKey('LcrDeal')
    date = models.DateField(auto_now = False)
    calls_ok = models.BigIntegerField()
    seconds = models.BigIntegerField()
    dt_when = models.DateTimeField(auto_now_add = True)

    def minutes(self):
        return float(self.seconds / 60)

class LcrStatTotalUpdate(models.Model):
    deal = models.ForeignKey('LcrDeal')
    calls_ok = models.BigIntegerField()
    calls_fail = models.BigIntegerField()
    seconds = models.BigIntegerField()
    acd = models.FloatField()
    dt_when = models.DateTimeField(auto_now_add = True)

    def asr(self):
        fasr = float(0)
        if (self.calls_ok + self.calls_fail) > 0:
            fasr = float(self.calls_ok) / (self.calls_ok + self.calls_fail) * 100
        return fasr

    def minutes(self):
        return float(self.seconds / 60)

class LcrStatServerMonitor(models.Model):
    host = models.CharField(max_length = 15, verbose_name = 'VoipSwitch IP')
    call_code = models.CharField(max_length = 10, verbose_name = 'Test Call Code')
    log = models.TextField(verbose_name = 'Log')
    dt_when = models.DateTimeField(auto_now_add = True)

class LcrStatSwitchHour(models.Model):
    switch = models.ForeignKey('LcrSwitch')
    date = models.DateField(auto_now = False)
    hour = models.IntegerField()
    seconds = models.BigIntegerField()

class LcrStatSessionStat(models.Model):
    dt_when = models.DateTimeField(auto_now_add = True)

CH_INV_STATUS = (
    (1, 'Issued'),
    (2, 'Sent'),
    (89, 'Disputed'),
    (99, 'Paid in Full'),
)

CH_INV_DIR = (
    (1, 'Customer'),
    (2, 'Supplier'),
)

class LcrInvoice(models.Model):
    partner = models.ForeignKey('LcrPartner')
    dt_when = models.DateTimeField(auto_now_add = True)
    dt_updated = models.DateTimeField(auto_now = True)
    status = models.SmallIntegerField(choices = CH_INV_STATUS)
    due_days = models.IntegerField(verbose_name = 'Days Due')
    dt_from = models.DateTimeField(verbose_name = 'Date/Time FROM')
    dt_to = models.DateTimeField(verbose_name = 'Date/Time TO')	# THIS IS INCLUSIVE
    carrier = models.ForeignKey('LcrCarrier')
    direction = models.SmallIntegerField(choices = CH_INV_DIR, default = 1)
    tax = models.IntegerField(default = 0)

    def number(self):
        # ---------LCR :-)
        return '%d/527-%04d%04d%04d' % (self.dt_when.year, self.partner.id + 1000, self.carrier.id, self.id)

    def sum_cost(self):
        sum_cost = 0.0
        for position in self.lcrinvoiceposition_set.all():
            sum_cost += position.sum_cost()
        return sum_cost

    def total(self):
        return 1.0 * self.sum_cost() * ((100.0 + self.tax) / 100)

    def due_date(self):
        return self.dt_when + datetime.timedelta(days = self.due_days)

class LcrInvoicePosition(models.Model):
    invoice = models.ForeignKey('LcrInvoice')
    deal = models.ForeignKey('LcrDeal')
    ppm = models.DecimalField(max_digits = 14, decimal_places = 4)

    def sum_minutes(self):
        sum_seconds = 0
        for stat in LcrStatH.objects.filter(deal = self.deal, dt_when__gte = self.invoice.dt_from, dt_when__lte = self.invoice.dt_to):
            sum_seconds += stat.seconds
        return 1.0 * sum_seconds / 60

    def sum_cost(self):
        return self.sum_minutes() * float(self.ppm)

# Heart of LCR <3
class LcrDeal(models.Model):
    partner = models.ForeignKey('LcrPartner', verbose_name = 'Partner')
    buy_carrier = models.ForeignKey('LcrCustomer', related_name = 'buy_carrier', verbose_name = 'Buyer')
    buy_price = models.DecimalField(max_digits = 14, decimal_places = 4, verbose_name = 'Buyer Price')
    sell_price = models.DecimalField(max_digits = 14, decimal_places = 4, verbose_name = 'Supplier Price')
    destination = models.ForeignKey('LcrDestination', verbose_name = 'Destination')
    ems_pid_buyer = models.CharField(max_length = 20, null = True, blank = True, verbose_name = 'EMS ID - Buyer')
    ems_pid_seller = models.CharField(max_length = 20, null = True, blank = True, verbose_name = 'EMS ID - Seller')
    dt_when = models.DateTimeField(auto_now_add = True)
    is_active = models.IntegerField(default = 1, verbose_name = 'Is Active?', choices = CH_BOOL)
    priority = models.IntegerField(default = 0, verbose_name = 'Routing Priority')
    tech_prefix = models.CharField(max_length = 10, blank = True, default = '', verbose_name = 'Tech Prefix')
    tod = models.ForeignKey('LcrTod', default = 4, verbose_name = 'ToD Tarriff')
    s_name = models.CharField(max_length = 200, blank = True, verbose_name = 'Switch Name')
    dt_updated = models.DateTimeField(auto_now = True)
    # Old LCR Concept below :-)
    #sell_carrier = models.ForeignKey('LcrSupplier', related_name = 'sell_carrier', verbose_name = 'Seller')
    #vs_client = models.CharField(max_length = 100, verbose_name = 'VS Client Name')
    #vs_gw = models.CharField(max_length = 100, verbose_name = 'VS GW Name')

    def __unicode__(self):
        return '#' + str(self.id) + ': ' + unicode(self.buy_carrier) + ' > ' + unicode(self.destination) + ')'

    def stat_seconds(self, dt_from, dt_to):
        # WARNING! dt_to IS INCLUSIVE!!! (for billing: 2012-03-01 - 2012-03-31 get whole march)
        return LcrStatH.objects.filter(deal = self, dt_when__gte = dt_from, dt_when__lte = dt_to).aggregate(Sum('seconds'))['seconds__sum']

    def stat_calls_ok(self, dt_from, dt_to):
        return LcrStatH.objects.filter(deal = self, dt_when__gte = dt_from, dt_when__lte = dt_to).aggregate(Sum('calls_ok'))['calls_ok__sum']

    def stat_calls_fail(self, dt_from, dt_to):
        return LcrStatH.objects.filter(deal = self, dt_when__gte = dt_from, dt_when__lte = dt_to).aggregate(Sum('calls_fail'))['calls_fail__sum']

    def tot_stat_seconds(self):
        return self.stat_seconds(datetime.datetime(2011, 1, 1, 0, 0, 0), datetime.datetime.now())

    def tot_stat_calls_ok(self):
        return self.stat_calls_ok(datetime.datetime(2011, 1, 1, 0, 0, 0), datetime.datetime.now())

    def tot_stat_calls_fail(self):
        return self.stat_calls_fail(datetime.datetime(2011, 1, 1, 0, 0, 0), datetime.datetime.now())

    def tot_minutes(self):
        return self.tot_stat_seconds() / 60

    def stat_last_traffic(self):
        x = LcrStatH.objects.filter(deal = self, seconds__gt = 0).order_by('-dt_when')
        if len(x):
            return x[0].dt_when
        else:
            return False

    def number_prefix(self):
        ret = ''
        if self.buy_carrier.switch.is_slave():
            ret += '527%07d' % (self.buy_carrier.id, )
        if self.buy_carrier.tech_prefix:
            ret += self.buy_carrier.tech_prefix
        if self.tech_prefix:
            ret += self.tech_prefix
        return ret

    def pointed_sum(self, party):
        sum = LcrPoint.objects.filter(deal = self, party = party).aggregate(res = Sum('amount'))
        if type(sum).__name__ == 'dict':
            if sum['res'] == None:
                return float(0)
            else:
                return float(sum['res'])
        else:
            return float(0)

    def total_minutes(self):
        stat = self.get_stat_total()
        return int(round(stat.seconds / 60))

    def total_funds(self, party):
        if party == 1:
            return self.total_minutes() * self.buy_price
        elif party == 2:
            return self.total_minutes() * self.sell_price

    def total_balance(self, party):
        if party == 1:
            price = self.buy_price
        elif party == 2:
            price = self.sell_price
        minutes = self.total_minutes()
        pointed = self.pointed_sum(party)
        balance = float(pointed) - float(minutes * price)
        return balance

    def total_balance_buyer(self):
        return self.total_balance(1)

    def total_balance_seller(self):
        return self.total_balance(2)

    def customer_switch_name(self):
        if self.buy_carrier.switch.is_slave():
            return self.buy_carrier.switch.master_switch_cu_name
        else:
            return self.buy_carrier.switch_name()

    def get_stat_total(self):
        st = LcrStatTotalUpdate(deal = self)
        st.calls_ok = 0
        st.calls_fail = 0
        st.seconds = 0
        st.acd = 0
        #
        dailies = LcrStatDailyUpdate.objects.filter(deal = self)
        if len(dailies):
            for daily in dailies:
                st.seconds += daily.seconds
                st.calls_ok += daily.calls_ok
                st.calls_fail += daily.calls_fail
        #
        dds = LcrStatDailyDelta.objects.filter(deal = self).order_by('-id')
        if len(dds):
            dd = dds[0]
            st.seconds += dd.seconds
            st.calls_ok += dd.calls_ok
        #
        if st.calls_ok:
            st.acd = st.seconds / st.calls_ok
        return st

    def get_str_tech_prefix(self):
        if len(self.tech_prefix):
            return self.tech_prefix
        else:
            return '- none -'

    def lasth(self):
        dnp = datetime.datetime.now() - datetime.timedelta(hours = 1)
        dn = datetime.datetime(dnp.year, dnp.month, dnp.day, dnp.hour, 0)
        shs = LcrStatH.objects.filter(dt_when = dn, deal = self)
        if len(shs):
            return shs[0]
        else:
            return False

class LcrCode(models.Model):
    deal = models.ForeignKey('LcrDeal', verbose_name = 'Deal')
    vs_prefix = models.CharField(max_length = 100, verbose_name = 'VS Prefix')

    def __unicode__(self):
        return self.vs_prefix

class LcrPartner(models.Model):
    name = models.CharField(max_length = 100, verbose_name = 'Full Name')
    details = models.TextField(blank = True)
    logo = models.CharField(max_length = 100, blank = True)

    def __unicode__(self):
        return self.name

class LcrPartnerAccount(models.Model):
    user = models.OneToOneField(User)
    partner = models.ForeignKey('LcrPartner')

    def __unicode__(self):
        return self.user.username + ' (' + unicode(self.partner) + ')'

class LcrProfile(models.Model):
    user = models.OneToOneField(User)

    def is_god(self):
        if self.user.id == 1:
            return True
        else:
            return False

    def is_partner(self):
        if len(LcrPartnerAccount.objects.filter(user = self.user)):
            return True
        else:
            return False

    def is_carrier(self):
        if len(LcrWebAccount.objects.filter(user = self.user)):
            return True
        else:
            return False

    def is_agent(self):
        if len(LcrRetailAgent.objects.filter(user = self.user)):
            return True
        else:
            return False

    def get_partner(self):
        if self.is_partner():
            return LcrPartnerAccount.objects.filter(user = self.user)[0]

    def get_carrier(self):
        if self.is_carrier():
            return LcrWebAccount.objects.filter(user = self.user)[0]

    def get_agent(self):
        if self.is_agent():
            return LcrRetailAgent.objects.filter(user = self.user)[0]

    def get_agent_ara(self):
        if self.is_agent():
            return LcrRetailARASipFriend.objects.filter(agent = self.get_agent())[0]

    # modules
    def ma_management(self):
        return len(LcrModuleAccess.objects.filter(module = 1, partner = self.get_partner().partner))

    def ma_test(self):
        return len(LcrModuleAccess.objects.filter(module = 2, partner = self.get_partner().partner))

    def ma_deals(self):
        return len(LcrModuleAccess.objects.filter(module = 3, partner = self.get_partner().partner))

    def ma_financial(self):
        return len(LcrModuleAccess.objects.filter(module = 4, partner = self.get_partner().partner))

    def ma_technical(self):
        return len(LcrModuleAccess.objects.filter(module = 5, partner = self.get_partner().partner))

    def ma_retail(self):
        return len(LcrModuleAccess.objects.filter(module = 6, partner = self.get_partner().partner))

    def ma_mvts(self):
        return len(LcrModuleAccess.objects.filter(module = 7, partner = self.get_partner().partner))

    def ma_agents(self):
        return len(LcrModuleAccess.objects.filter(module = 8, partner = self.get_partner().partner))


class LcrWebAccount(models.Model):
    user = models.OneToOneField(User)
    carrier = models.OneToOneField('LcrCarrier')

    def __unicode__(self):
        return self.user.username + ' (' + unicode(self.carrier) + ')'

class LcrTod(models.Model):
    name = models.CharField(max_length = 50, verbose_name = 'ToD Tarriff')

    def __unicode__(self):
        return self.name

CH_TP_DOW = (
    (0, 'Sunday'),
    (1, 'Monday'),
    (2, 'Tuesday'),
    (3, 'Wednesday'),
    (4, 'Thursday'),
    (5, 'Friday'),
    (6, 'Saturday')
)

class LcrTodPeriod(models.Model):
    tod = models.ForeignKey('LcrTod')
    from_day = models.IntegerField(verbose_name = 'From / Day', choices = CH_TP_DOW)
    to_day = models.IntegerField(verbose_name = 'To / Day', choices = CH_TP_DOW)
    from_hour = models.IntegerField(verbose_name = 'From / Hour')
    to_hour = models.IntegerField(verbose_name = 'To / Hour')

    def __unicode__(self):
        return unicode(self.tod) + ': ' + self.get_from_day_display() + ' ' + str(self.from_hour) + ':00 - ' + self.get_to_day_display() + ' ' + str(self.to_hour) + ':59'

CH_SWITCH_TYPE = (
    (1, 'VoipSwitch SIP'),
    (2, 'FS/SBC SIP'),
    (3, 'MVTS Pro SIP'),
    (4, 'Cisco (Radius)'),
    (5, 'Asterisk PBX'),
)

class LcrSwitch(models.Model):
    type = models.IntegerField(verbose_name = 'Switch Type', choices = CH_SWITCH_TYPE)
    ip_addr = models.CharField(max_length = 20, verbose_name = 'Switch IP')
    sql_ip = models.CharField(max_length = 20, verbose_name = 'LIVE SQL IP')
    sql_user = models.CharField(max_length = 20, verbose_name = 'LIVE SQL Username')
    sql_pass = models.CharField(max_length = 20, verbose_name = 'LIVE SQL Password')
    sql_base = models.CharField(max_length = 20, verbose_name = 'LIVE SQL Database')
    stats_sql_ip = models.CharField(max_length = 20, blank = True, null = True, verbose_name = 'STATS SQL IP')
    stats_sql_user = models.CharField(max_length = 20, blank = True, null = True, verbose_name = 'STATS SQL Username')
    stats_sql_pass = models.CharField(max_length = 20, blank = True, null = True, verbose_name = 'STATS SQL Password')
    stats_sql_base = models.CharField(max_length = 20, blank = True, null = True, verbose_name = 'STATS SQL Database')
    master_switch = models.ForeignKey('self', blank = True, null = True, verbose_name = 'Master Switch')
    master_switch_sw_name = models.CharField(max_length = 10, blank = True, null = True, default = '', verbose_name = 'MS Gateway Name (@SS)')
    master_switch_cu_name = models.CharField(max_length = 10, blank = True, null = True, default = '', verbose_name = 'SS Client Name (@MS)')
    tod_interval = models.IntegerField(verbose_name = 'ToD Interval', blank = True, null = True, default = 0)
    partner = models.ForeignKey('LcrPartner')

    def __unicode__(self):
        str_type = ' ['
        if self.master_switch:
            str_type += 'SLAVE -> ' + self.master_switch.ip_addr + ']'
        else:
            str_type += 'MASTER]'
        return self.ip_addr + ' (' + self.get_type_display() + ')'

    def is_slave(self):
        if self.master_switch:
            return True
        else:
            return False

    def get_db(self):
        db = _mysql.connect(self.sql_ip, self.sql_user, self.sql_pass, self.sql_base)
        return db

    def get_stat_db(self):
        if self.stats_sql_ip:
            db = _mysql.connect(self.stats_sql_ip, self.stats_sql_user, self.stats_sql_pass, self.stats_sql_base)
        else:
            db = self.get_db()
        return db

class LcrCustomer(models.Model):
    carrier = models.ForeignKey('LcrCarrier')
    switch = models.ForeignKey('LcrSwitch')
    s_name = models.CharField(max_length = 200, verbose_name = 'Switch Name')
    tech_prefix = models.CharField(max_length = 10, blank = True, default = '', verbose_name = 'Tech Prefix')

    def __unicode__(self):
        return '[' + self.s_name + '] ' + unicode(self.carrier) + ' @ ' + unicode(self.switch)

    def switch_name(self):
        return 'lcr-' + slugify(self.s_name)

    def num_ips(self):
        return len(LcrCustomerIp.objects.filter(customer = self))

    def get_ips(self):
        return LcrCustomerIp.objects.filter(customer = self)

    def get_deals(self, is_active = 1):
        return LcrDeal.objects.filter(buy_carrier = self, is_active = is_active)

    def get_deal_num(self):
        return len(self.get_deals())

    def get_total_credit(self):
        c = 0
        for deal in self.get_deals():
            c += deal.pointed_sum(1)
        return c

    def get_total_consumed(self):
        c = 0
        for deal in self.get_deals():
            c += deal.total_funds(1)
        return c

    def get_delta(self):
        cr = self.get_total_credit()
        co = self.get_total_consumed()
        return float(cr) - float(co)

class LcrCustomerIp(models.Model):
    customer = models.ForeignKey('LcrCustomer')
    ip_addr = models.CharField(max_length = 20, verbose_name = 'IP Address')

    def __unicode__(self):
        return self.ip_addr

class LcrSupplier(models.Model):
    carrier = models.ForeignKey('LcrCarrier')
    s_name = models.CharField(max_length = 8, verbose_name = 'Switch Name')

    def __unicode__(self):
        return '[' + self.s_name + '] ' + unicode(self.carrier)

    def switch_name(self):
        return 'lcr-' + slugify(self.s_name)

    def get_deals(self, is_active = 1):
        return LcrDeal.objects.filter(destination__supplier = self, is_active = is_active)

    def get_deal_num(self):
        return len(self.get_deals())

    def get_total_credit(self):
        c = 0
        for deal in self.get_deals():
            c += deal.pointed_sum(2)
        return c

    def get_total_consumed(self):
        c = 0
        for deal in self.get_deals():
            c += deal.total_funds(2)
        return c

    def get_delta(self):
        cr = self.get_total_credit()
        co = self.get_total_consumed()
        return float(cr) - float(co)

class LcrDestination(models.Model):
    name = models.CharField(max_length = 60, verbose_name = 'Destination Name')
    s_name = models.CharField(max_length = 200, verbose_name = 'Switch Destination Name')
    supplier = models.ForeignKey('LcrSupplier')
    ip_addr = models.CharField(max_length = 20, verbose_name = 'Gateway IP')
    tech_prefix = models.CharField(default = '', blank = True, max_length = 10, verbose_name = 'Tech Prefix')

    def __unicode__(self):
        return self.name + ' @ ' + unicode(self.supplier)

    def switch_name(self):
        return 'lcr-' + slugify(self.supplier.s_name) + '-' +  slugify(self.s_name)

    def get_num_deals(self):
        return len(LcrDeal.objects.filter(destination = self))

    def get_deals(self):
        return LcrDeal.objects.filter(destination = self)

    def get_str_tech_prefix(self):
        if len(self.tech_prefix):
            return self.tech_prefix
        else:
            return '- none -'

class LcrDestinationE164(models.Model):
    destination = models.ForeignKey('LcrDestination')
    code = models.CharField(max_length = 15, verbose_name = 'E.164 Prefix')

    def __unicode__(self):
        return self.code

class LcrCarrier(models.Model):
    partner = models.ForeignKey('LcrPartner')
    name = models.CharField(max_length = 200, verbose_name = 'Carrier Name')
    address = models.TextField(blank = True, verbose_name = 'Full Address')
    gen_phone = models.CharField(blank = True, max_length = 100, verbose_name = 'Phone Number')
    gen_www = models.CharField(blank = True, max_length = 100, verbose_name = 'Website Address')
    gen_email = models.CharField(blank = True, max_length = 100, verbose_name = 'E-mail Address')
    bill_name = models.CharField(blank = True, max_length = 200, verbose_name = 'Billing - Contact Name')
    bill_phone = models.CharField(blank = True, max_length = 100, verbose_name = 'Billing - Phone Number')
    bill_msn = models.CharField(blank = True, max_length = 100, verbose_name = 'Billing - MSN')
    bill_email = models.EmailField(blank = True, verbose_name = 'Billing - Email Address')
    bill_hours = models.CharField(blank = True, max_length = 100, verbose_name = 'Billing - Working Hours')
    noc_name = models.CharField(blank = True, max_length = 200, verbose_name = 'NOC - Contact Name')
    noc_phone = models.CharField(blank = True, max_length = 100, verbose_name = 'NOC - Phone Number')
    noc_msn = models.CharField(blank = True, max_length = 100, verbose_name = 'NOC - MSN')
    noc_email = models.EmailField(blank = True, verbose_name = 'NOC - Email Address')
    noc_hours = models.CharField(blank = True, max_length = 100, verbose_name = 'NOC - Working Hours')
    isp_city = models.CharField(blank = True, max_length = 100, verbose_name = 'City & Country')
    isp_provider = models.CharField(blank = True, max_length = 100, verbose_name = 'Provider Name')
    isp_as = models.CharField(blank = True, max_length = 50, verbose_name = 'AS Number')
    isp_asx = models.IntegerField(blank = True, default = 0, null = True, verbose_name = 'Dedicated AS?', choices = CH_YESNO)
    isp_bandwidth = models.CharField(blank = True, max_length = 50, verbose_name = 'Dedicated Internet Bandwidth')
    ip_signal = models.CharField(blank = True, max_length = 75, verbose_name = 'Signaling Address Range (CIDR)')
    ip_port = models.CharField(blank = True, max_length = 10, verbose_name = 'UDP/TCP SIP Port')
    ip_signal_other = models.IntegerField(blank = True, default = 0, null = True, verbose_name = 'Other Signaling IPs?', choices = CH_YESNO)
    ip_media = models.CharField(blank = True, max_length = 75, verbose_name = 'Media Address Range (CIDR)')
    ip_media_other = models.IntegerField(blank = True, default = 0, null = True, verbose_name = 'Other Media IPs?', choices = CH_YESNO)
    ip_conntype = models.IntegerField(blank = True, default = 0, null = True, verbose_name = 'IP Connection Type', choices = CH_IPCONNTYPE)
    prov_gw_brand = models.CharField(blank = True, max_length = 100, verbose_name = 'Gateway Manufacturer')
    prov_gw_model = models.CharField(blank = True, max_length = 100, verbose_name = 'Gateway Model')
    prov_gw_soft = models.CharField(blank = True, max_length = 100, verbose_name = 'Software Version')
    prov_protocol = models.IntegerField(blank = True, default = 0, null = True, verbose_name = 'Preferred Protocol', choices = CH_PROTOCOL)
    prov_req_sessions = models.CharField(blank = True, max_length = 25, verbose_name = 'Requested Number of Sessions')
    prov_req_cps = models.CharField(blank = True, max_length = 25, verbose_name = 'Requested CPS (Calls per Second)')
    prov_role = models.IntegerField(blank = True, default = 0, null = True, verbose_name = 'Primary Role', choices = CH_ROLE)
    prov_codec = models.IntegerField(blank = True, default = 0, null = True, verbose_name = 'Primary Codec', choices = CH_CODEC)
    prov_payload = models.CharField(blank = True, max_length = 50, verbose_name = 'Payload Size (ms)')
    prov_ss = models.IntegerField(blank = True, default = 0, null = True, verbose_name = 'Silence Suppresion Support?', choices = CH_YESNO)
    prov_rfc2833 = models.IntegerField(blank = True, null = True, default = 0,  verbose_name = 'RFC 2833 Support?', choices = CH_YESNO)
    info_dt = models.DateTimeField(auto_now_add = True, verbose_name = 'INFO: Date/Time')
    info_ip = models.CharField(blank = True, max_length = 30, verbose_name = 'INFO: IP Address')

    def __unicode__(self):
        return self.name + ' (' + self.partner.name + ')'

    def num_customers(self):
        return len(LcrCustomer.objects.filter(carrier = self))

    def get_customers(self):
        return LcrCustomer.objects.filter(carrier = self)

    def num_suppliers(self):
        return len(LcrSupplier.objects.filter(carrier = self))

    def get_suppliers(self):
        return LcrSupplier.objects.filter(carrier = self)

    def get_deals_customer(self):
        return self.get_deals(1, 1)

    def get_deals_supplier(self):
        return self.get_deals(2, 1)

    def get_deals(self, role, is_active = 1):
        if role == 1:
            deals = LcrDeal.objects.filter(is_active = is_active, buy_carrier__carrier = self)
        elif role == 2:
            deals = LcrDeal.objects.filter(is_active = is_active, destination__supplier__carrier = self)
        return deals

    def get_tickets(self, status = -1):
        if status == -1:
            return LcrEscalation.objects.filter(carrier = self)
        else:
            return LcrEscalation.objects.filter(carrier = self, status = status)

    def get_new_tickets(self):
        return self.get_tickets(0)

CH_REQUESTTYPE = (
    ('General', (
        (101, 'We want to update our corporate information'),
        (102, 'We want to change our contact e-mail address'),
        (103, 'We want to change our msn/phone information'),
        (199, 'Other (Describe in Details)'),
    )),
    ('VoIP', (
        (201, 'We want to add/remove a SIP gateway'),
        (202, 'We want to change our codec preferences'),
        (203, 'We want to set up/change a VPN connection'),
        (204, 'We are having issues with one of the routes we\'re buing'),
        (205, 'We are having issues with one of the routes we\'re selling'),
        (206, 'We want to open a test window for a new route'),
        (207, 'We want to compare our billing information'),
        (208, 'We are having problems interconnecting'),
        (299, 'Other (Describe in Details)'),
    )),
    ('Billing', (
        (301, 'We have not received a payment for our invoice'),
        (302, 'We have not received an invoice we expected'),
        (303, 'We want to use another currency'),
        (304, 'We want to re-bill a certain period of time'),
        (399, 'Other (Describe in Details)'),
    )),
)

CH_ESCSTATUS = (
    (0, 'New'),
    (99, 'Closed')
)

class LcrEscalation(models.Model):
    partner = models.ForeignKey('LcrPartner')
    followup_id = models.CharField(blank = True, max_length = 50, verbose_name = 'Escalation ID (Follow Up)')
    carrier = models.ForeignKey('LcrCarrier')
    status = models.IntegerField(blank = True, null = True, default = 0, choices = CH_ESCSTATUS)
    author_name = models.CharField(blank = True, max_length = 100, verbose_name = 'Request Author')
    request_type = models.IntegerField(blank = True, null = True, default = 0, verbose_name = 'Request Type', choices = CH_REQUESTTYPE)
    request_details = models.TextField(blank = True, verbose_name = 'Request Details')
    file = models.FileField(blank = True, upload_to = 'a2z', verbose_name = 'Additional File')
    info_dt = models.DateTimeField(auto_now_add = True, verbose_name = 'INFO: Date/Time')
    info_ip = models.CharField(blank = True, max_length = 30, verbose_name = 'INFO: IP Address')

class LcrEscalationResponse(models.Model):
    escalation = models.ForeignKey('LcrEscalation')
    author = models.ForeignKey(User)
    response_details = models.TextField(blank = True, verbose_name = 'Response Details')
    file = models.FileField(blank = True, upload_to = 'a2z', verbose_name = 'Additional File')
    status = models.IntegerField(blank = True, null = True, default = 0, choices = CH_ESCSTATUS)
    info_dt = models.DateTimeField(auto_now_add = True, verbose_name = 'INFO: Date/Time')

# Not anymore -> Destination!
#class LcrSupplier(models.Model):
#	name = models.CharField(max_length = 200, verbose_name = 'Company Name')
#	address = models.TextField(blank = True, verbose_name = 'Address')
#	phone = models.CharField(blank = True, max_length = 100, verbose_name = 'Phone Number')
#	bill_name = models.CharField(blank = True, max_length = 200, verbose_name = 'Billing - Contact Name')
#	bill_phone = models.CharField(blank = True, max_length = 100, verbose_name = 'Billing - Phone Number')
#	bill_msn = models.CharField(blank = True, max_length = 100, verbose_name = 'Billing - MSN')
#	bill_email = models.EmailField(blank = True, verbose_name = 'Billing - Email Address')
#	noc_name = models.CharField(blank = True, max_length = 200, verbose_name = 'NOC - Contact Name')
#	noc_phone = models.CharField(blank = True, max_length = 100, verbose_name = 'NOC - Phone Number')
#	noc_msn = models.CharField(blank = True, max_length = 100, verbose_name = 'NOC - MSN')
#	noc_email = models.EmailField(blank = True, verbose_name = 'NOC - Email Address')
#	prov_gw_brand = models.CharField(blank = True, max_length = 100, verbose_name = 'Gateway Manufacturer')
#	prov_gw_model = models.CharField(blank = True, max_length = 100, verbose_name = 'Gateway Model')
#	prov_gw_soft = models.CharField(blank = True, max_length = 100, verbose_name = 'Software Version')
#	prov_ip_signal = models.CharField(blank = True, max_length = 20, verbose_name = 'IP (Signalling)')
#	prov_ip_media = models.CharField(blank = True, max_length = 20, verbose_name = 'IP (Media)')
#
#	def __unicode__(self):
#		return self.name

class LcrRoute(models.Model):
    code = models.CharField(max_length = 25)
    name = models.CharField(max_length = 200)
    price = models.DecimalField(max_digits = 14, decimal_places = 4)
    az = models.ForeignKey('LcrAZ')
    user = models.ForeignKey(User)
    partner = models.ForeignKey('LcrPartner')

CH_TEST_STATUS = (
    (0, 'New'),
    (1, 'Succeeded'),
    (2, 'Failed'),
)

class LcrTest(models.Model):
    supplier = models.ForeignKey('LcrSupplier')
    destination = models.CharField(max_length = 200, verbose_name = 'Destination')
    gw_ip = models.CharField(max_length = 50, verbose_name = 'SIP GW IP')
    prefix = models.CharField(max_length = 15, verbose_name = 'Prefix (if required)', blank = True, null = True)
    is_direct = models.BooleanField(verbose_name = 'Route is Direct')
    is_cli = models.BooleanField(verbose_name = 'Route has CLI')
    is_fas = models.BooleanField(verbose_name = 'Route is FAS\'d')
    status = models.SmallIntegerField(default = 0, verbose_name = 'Test Status', choices = CH_TEST_STATUS)
    comment = models.TextField(verbose_name = 'Test Comment', blank = True, null = True)
    dt_when = models.DateTimeField(auto_now_add = True)
    dt_stat = models.DateTimeField(blank = True, null = True)

class LcrTestNumber(models.Model):
    test = models.ForeignKey('LcrTest')
    number = models.CharField(max_length = 50, verbose_name = 'Test Number')

CH_RECON_PT = (
    (10, 'Customer - Deal'),
    (20, 'Supplier - Destination')
)

CH_RECON_ST = (
    (0, 'New'),
    (10, 'Processing'),
    (99, 'Completed')
)

class LcrRecon(models.Model):
    author = models.ForeignKey(User)
    party_type = models.IntegerField(choices = CH_RECON_PT)
    party_id = models.BigIntegerField()
    cdr = models.FileField(upload_to = 'a2z')
    tolerance = models.IntegerField(default = 2)
    dt_when = models.DateTimeField(auto_now_add = True)

    def get_party(self):
        if self.party_type == 10:
            return LcrDeal.objects.get(id = self.party_id)
        elif self.party_type == 20:
            return LcrDestination.objects.get(id = self.party_id)
        else:
            return 0

    def str_party(self):
        if self.party_type == 20:
            return 'Destination: %s' % (unicode(self.get_party()))
        elif self.party_type == 10:
            return 'Deal: %s' % (unicode(self.get_party()))

    def get_mac(self):
        i = 0
        mac = 0
        dist_max_s = LcrReconACDDistro.objects.filter(recon = self).order_by('acd_length')
        for dist in dist_max_s:
            if dist.acd_number == 0:
                i += 1
            else:
                i = 0
            if i >= 12:
                mac = dist.acd_length - 110
                break
        return mac

    def get_overmacs(self):
        return LcrReconCDR.objects.filter(party = 2, recon = self, cdr_duration__gt = self.get_mac).order_by('cdr_start')

    def set_status(self, status):
        s = LcrReconStatus(recon = self)
        s.status = status
        s.save()

    def get_status(self):
        ss = LcrReconStatus.objects.filter(recon = self).order_by('-id')
        if len(ss):
            return ss[0]
        else:
            return LcrReconStatus(recon = self, status = 0)

    def secs_disputed(self):
        ob = 0
        for d in LcrReconDispute.objects.filter(recon = self, type__gte = 3, type__lte = 4):
            ob += d.cdr_ext.cdr_duration - d.cdr_lcr.cdr_duration
        return ob

    def secs_miss_lcr(self):
        miss = 0
        for d in LcrReconDispute.objects.filter(recon = self, type = 1):
            miss += d.cdr_lcr.cdr_duration
        return miss

    def secs_miss_ext(self):
        miss = 0
        for d in LcrReconDispute.objects.filter(recon = self, type = 2):
            miss += d.cdr_ext.cdr_duration
        return miss

    def secs_overlap(self):
        olap = 0
        for d in LcrReconOverlap.objects.filter(recon = self):
            olap += d.cdr_ext_1.cdr_duration
            olap += d.cdr_ext_2.cdr_duration
        return olap

    def secs_overbill(self):
        obill = 0
        for d in self.get_overmacs():
            obill += d.cdr_duration
        return obill

class LcrReconStatus(models.Model):
    recon = models.ForeignKey('LcrRecon')
    status = models.IntegerField(choices = CH_RECON_ST)
    dt_when = models.DateTimeField(auto_now_add = True)

CH_RCDR_PARTY = (
    (1, 'LCR'),
    (2, 'External')
)

class LcrReconCDR(models.Model):
    recon = models.ForeignKey('LcrRecon')
    party = models.SmallIntegerField(choices = CH_RCDR_PARTY)
    cdr_number = models.CharField(max_length = 50)
    cdr_start = models.DateTimeField(auto_now_add = False)
    cdr_duration = models.IntegerField()

class LcrReconResultsGlobal(models.Model):
    recon = models.OneToOneField('LcrRecon')
    interval = models.IntegerField()
    lcr_calls = models.IntegerField()
    ext_calls = models.IntegerField()
    lcr_secs = models.IntegerField()
    ext_secs = models.IntegerField()
    lcr_unmatched = models.IntegerField()
    ext_unmatched = models.IntegerField()
    diff_calls = models.IntegerField()

class LcrReconResultsHour(models.Model):
    recon = models.ForeignKey('LcrRecon')
    date = models.DateField()
    hour = models.IntegerField()
    lcr_calls = models.IntegerField()
    ext_calls = models.IntegerField()
    lcr_secs = models.IntegerField()
    ext_secs = models.IntegerField()
    lcr_unmatched = models.IntegerField()
    ext_unmatched = models.IntegerField()
    diff_calls = models.IntegerField()

CH_RDISPUTE = (
    (1, 'Unmatched Call (Present in LCR)'),
    (2, 'Unmatched Call (Not present in LCR)'),
    (3, 'Billing Difference - EXT Underbilled'),
    (4, 'Billing Difference - EXT Overbilled')
)

class LcrReconDispute(models.Model):
    recon = models.ForeignKey('LcrRecon')
    cdr_lcr = models.ForeignKey('LcrReconCDR', blank = True, null = True, related_name = 'cdr_lcr')
    cdr_ext = models.ForeignKey('LcrReconCDR', blank = True, null = True, related_name = 'cdr_ext')
    type = models.SmallIntegerField(choices = CH_RDISPUTE)

class LcrReconOverlap(models.Model):
    recon = models.ForeignKey('LcrRecon')
    cdr_ext_1 = models.ForeignKey('LcrReconCDR', blank = True, null = True, related_name = 'cdr_ext_1')
    cdr_ext_2 = models.ForeignKey('LcrReconCDR', blank = True, null = True, related_name = 'cdr_ext_2')

class LcrReconACDDistro(models.Model):
    recon = models.ForeignKey('LcrRecon')
    acd_length = models.IntegerField()
    acd_number = models.BigIntegerField()

CH_CR_JOB = (
    (1, 'SWITCHES - VoipSwitch Synchronization'),
    (2, 'STATS - LCR Statistics Session'),
    (3, 'MONITORS - QoS Monitors'),
    (4, 'WATCHDOG - VoipSwitch Watchdog'),
    (5, 'DIALER - Predictive Dialer'),
)

CH_CR_STATUS = (
    (0, 'Idle'),
    (1, 'Running')
)

class LcrCronStatus(models.Model):
    job = models.IntegerField(choices = CH_CR_JOB)
    status = models.IntegerField(choices = CH_CR_STATUS)

    def __unicode__(self):
        return self.get_job_display() + ' / ' + self.get_status_display()

# --- RETAIL STUFF --- #

class LcrRetailCustomer(models.Model):
    partner = models.ForeignKey('LcrPartner')
    name = models.CharField(max_length = 200, verbose_name = 'Name')
    address = models.TextField(verbose_name = 'Address')
    vat_id = models.CharField(max_length = 25, verbose_name = 'VAT Number', null = True, blank = True)
    pincode = models.CharField(max_length = 25, verbose_name = 'PIN Code', default = 'ABC123')

    def __unicode__(self):
        return self.name

    def get_active_cservices(self):
        ret_arr = []
        cservices = self.lcrretailcustomerservice_set.filter(switch = 1)
        for cservice in cservices:
            if len(self.lcrretailcustomerservice_set.filter(switch = 2, service = cservice.service, d_when__gte = cservice.d_when)) == 0:
                ret_arr.append(cservice)
        return ret_arr

CH_CS_SWITCH = (
    (1, 'On'),
    (2, 'Off')
)

CH_RC_SOURCE = (
    (1, 'Agent Website'),
    (2, 'Robo-Dialer')
)

CH_RC_DOCTYPE = (
    (1, 'DNI/NIF/NIE (Particular)'),
    (2, 'CIF (Empresa)')
)

CH_RC_LANGUAGE = (
    (1, 'English'),
    (2, 'Español')
)

CH_RC_STATUS = (
    (1, 'Enviado al Centro de Verificación / Verification Centre'),
    (2, 'Enviado por Correo Postal / Postal Service'),
    (99, 'Móvil / Otros')
)

class LcrRetailCandidateProduct(models.Model):
    name = models.CharField(max_length = 200, verbose_name = 'Product Name')

    def __unicode__(self):
        return self.name

class LcrRetailCandidate(models.Model):
    first_name = models.CharField(max_length = 200, verbose_name = 'First Name')
    last_name = models.CharField(max_length = 200, verbose_name = 'Last Name')
    company_name = models.CharField(max_length = 200, verbose_name = 'Company', blank = True)
    document_type = models.SmallIntegerField(verbose_name = 'Document Type', choices = CH_RC_DOCTYPE)
    document_number = models.CharField(max_length = 100, verbose_name = 'Document Number')
    account = models.CharField(max_length = 50, verbose_name = 'Account No.')
    phone = models.CharField(max_length = 50, verbose_name = 'Phone No.')
    mobile = models.CharField(max_length = 50, verbose_name = 'Mobile No.', blank = True)
    email = models.CharField(max_length = 100, verbose_name = 'Email', blank = True)
    address = models.TextField(verbose_name = 'Address')
    province = models.TextField(verbose_name = 'Province')
    zipcode = models.CharField(max_length = 10, verbose_name = 'Zip Code')
    language = models.SmallIntegerField(verbose_name = 'Language', choices = CH_RC_LANGUAGE)
    products = models.ManyToManyField('LcrRetailCandidateProduct', verbose_name = 'Products')
    source_type = models.IntegerField(verbose_name = 'Source Type', choices = CH_RC_SOURCE)
    source_key = models.IntegerField(verbose_name = 'Source ID', null = True, blank = True)
    dt_input = models.DateTimeField(auto_now_add = True)
    dt_processed = models.DateTimeField(auto_now_add = False, null = True, blank = True)
    operator = models.ForeignKey(User)
    status = models.SmallIntegerField(verbose_name = 'Status', blank = True, choices = CH_RC_STATUS)
    comment = models.TextField(verbose_name = 'Comments', blank = True)

class LcrRetailCandidateWC(models.Model):
    name = models.CharField(max_length = 200, null = True, blank = True)
    email = models.CharField(max_length = 200, null = True, blank = True)
    phone = models.CharField(max_length = 200, null = True, blank = True)
    ip_addr = models.CharField(max_length = 20, null = True, blank = True)
    operator_id = models.IntegerField(default = 0)
    dt_input = models.DateTimeField(auto_now_add = True)

class LcrRetailRoboCall(models.Model):
    agent = models.ForeignKey(User)
    line = models.ForeignKey('LcrRetailData')

    def __unicode__(self):
        return 'Agent: ' + self.agent.first_name + ' ' + self.agent.last_name + ' Ext: ' + self.line.phone_1

class LcrRetailCallBack(models.Model):
    agent = models.ForeignKey(User)
    line = models.ForeignKey('LcrRetailData')
    dt_when_date = models.DateField(auto_now_add = False)
    dt_when_time = models.TimeField(auto_now_add = False)
    comment = models.TextField(blank = True)

    def dt_when(self):
        return datetime.datetime.combine(self.dt_when_date, self.dt_when_time)

class LcrRetailRoboRequest(models.Model):
    aid = models.IntegerField(default = 0)
    exten = models.CharField(max_length = 20)
    dt_when = models.DateTimeField(auto_now_add = True)

    def str_agent(self):
        if self.aid != 0:
            u = User.objects.get(id = self.aid)
            return u.first_name + ' ' + u.last_name
        else:
            return '-'

    def int_answered(self):
        if self.aid != 0:
            return 1
        else:
            return 0

class LcrRetailCustomerService(models.Model):
    customer = models.ForeignKey('LcrRetailCustomer')
    service = models.ForeignKey('LcrRetailService')
    switch = models.IntegerField(choices = CH_CS_SWITCH)
    d_when = models.DateField(auto_now_add = False)

    def __unicode__(self):
        return 'Service ' + self.get_switch_display() + ': ' + unicode(self.service) + ' @ ' + unicode(self.customer)

    def get_numbers(self):
        if self.service.type == 1:
            return self.lcrretailcustomernumber_set.all()
        else:
            return {}

CH_RSTYPE = (
    (1, 'Landline'),
    (2, 'ISDN'),
    (3, 'MVNO'),
    (4, 'VoIP'),
    (5, 'ADSL'),
    (101, 'Destination Bundle')
)

class LcrRetailCustomerNumber(models.Model):
    #customer = models.ForeignKey('LcrRetailCustomer')
    cservice = models.ForeignKey('LcrRetailCustomerService')
    dt_when = models.DateTimeField(auto_now_add = True)
    number = models.CharField(max_length = 50)

    def __unicode__(self):
        return self.number + ' @ ' + ' (' + unicode(self.cservice) + ')'

class LcrRetailService(models.Model):
    partner = models.ForeignKey('LcrPartner')
    name = models.CharField(max_length = 200, verbose_name = 'Name')
    period_day = models.IntegerField(verbose_name = 'Billing - Days', default = 0)
    period_month = models.IntegerField(verbose_name = 'Billing - Months', default = 1)
    price = models.DecimalField(max_digits = 14, decimal_places = 4, verbose_name = 'Cost')
    type = models.IntegerField(verbose_name = 'Service Type', choices = CH_RSTYPE)

    def __unicode__(self):
        return self.name

    def get_profile(self):
        if (self.type == 1):
            ps = LcrRetailSPLandline.objects.filter(service = self)
            if len(ps):
                return ps[0]
        return False

    def get_tariff_info(self):
        if (self.type == 1):
            return unicode(self.get_profile().tariff)
        return False

    def num_active_customers(self):
        cnt = 0
        sopens = LcrRetailCustomerService.objects.filter(service = self, switch = 1)
        for sopen in sopens:
            scloses = LcrRetailCustomerService.objects.filter(service = self, switch = 2, d_when__gte = sopen.d_when)
            if len(scloses):
                cnt += 1
        return cnt

    def get_mod_destinations(self, mid):
        return LcrRetailServiceModDestination.objects.filter(service = self, mod_type = mid)

    def get_mod_include_destinations(self):
        return self.get_mod_destinations(1)

    def get_mod_volume_destinations(self):
        return self.get_mod_destinations(3)

CH_MODULE = (
    (1, 'MANAGEMENT'),
    (2, 'TEST TRAFFIC'),
    (3, 'DEALS'),
    (4, 'FINANCIAL'),
    (5, 'TECHNICAL'),
    (6, 'RETAIL'),
    (7, 'MVTS'),
    (8, 'AGENTS')
)

class LcrModuleAccess(models.Model):
    partner = models.ForeignKey('LcrPartner')
    module = models.IntegerField(choices = CH_MODULE)

    def __unicode__(self):
        return unicode(self.partner) + ' / ' + self.get_module_display()

CH_DEFPOL = (
    (1, 'Default Include'),
    (2, 'Default Exclude')
)
 
class LcrRetailSPLandline(models.Model):
    service = models.ForeignKey('LcrRetailService')
    mod_include_minutes = models.IntegerField(verbose_name = 'M-INCL Number of Minutes', default = 0)
    mod_include_policy = models.IntegerField(verbose_name = 'M-INCL Default Policy', default = 1, choices = CH_DEFPOL)
    mod_volume_minutes = models.IntegerField(verbose_name = 'M-VOL Number of Minutes', default = 0)
    mod_volume_discount = models.IntegerField(verbose_name = 'M-VOL Discount Value (%)', default = 0)
    mod_volume_repeats = models.IntegerField(verbose_name = 'M-VOL Number of Repeats', default = 0)
    mod_volume_policy = models.IntegerField(verbose_name = 'M-VOL Default Policy', default = 1, choices = CH_DEFPOL)
    tariff = models.ForeignKey('LcrRetailTariffPhone')

    def __unicode__(self):
        return 'Landline @ ' + unicode(self.service)

class LcrRetailTariffPhone(models.Model):
    partner = models.ForeignKey('LcrPartner')
    name = models.CharField(max_length = 100)
    sub_tariffs = models.ManyToManyField("self", symmetrical = False, null = True, blank = True)
    sub_price = models.IntegerField(verbose_name = 'Sub-Tariff Price (%)', default = 100)

    def __unicode__(self):
        return self.name

    def num_prefixes(self):
        return len(self.lcrretailratephone_set.all())

    def num_subtariffs(self):
        return len(self.sub_tariffs.all())

    def num_services(self):
        return len(self.lcrretailsplandline_set.all())

class LcrRetailRatePhone(models.Model):
    tariff = models.ForeignKey('LcrRetailTariffPhone')
    tod = models.ForeignKey('LcrTod')
    prefix = models.CharField(max_length = 50, verbose_name = 'Prefix')
    name = models.CharField(max_length = 250, verbose_name = 'Destination Name')
    rate_1 = models.DecimalField(max_digits = 14, decimal_places = 4, verbose_name = 'Price #1')
    billing_1 = models.IntegerField(verbose_name = 'Billing #1')
    ticks_1 = models.IntegerField(verbose_name = 'Ticks #1', default = 0)
    rate_2 = models.DecimalField(max_digits = 14, decimal_places = 4, verbose_name = 'Price #2', default = 0, blank = True)
    billing_2 = models.IntegerField(verbose_name = 'Billing #2', default = 0, blank = True)

    def __unicode__(self):
        return self.prefix

CH_CDR_SOURCE_TYPE = (
    (1, 'BT FTP Repository'),
)

class LcrRetailCDRSource(models.Model):
    partner = models.ForeignKey('LcrPartner')
    type = models.IntegerField(choices = CH_CDR_SOURCE_TYPE)
    id_name = models.CharField(max_length = 200, verbose_name = 'File Name')
    id_crc = models.CharField(max_length = 200, verbose_name = 'File CRC')
    dt_when = models.DateTimeField(auto_now_add = True)

    def __unicode__(self):
        return self.id_name + ' @ ' + self.get_type_display()

class LcrRetailCDR(models.Model):
    partner = models.ForeignKey('LcrPartner')
    source = models.ForeignKey('LcrRetailCDRSource')
    dn_source = models.CharField(max_length = 75, verbose_name = 'Source Number')
    dn_destination = models.CharField(max_length = 75, verbose_name = 'Destination Number')
    dt_when = models.DateTimeField(auto_now_add = False, verbose_name = 'Call Date/Time')
    duration = models.IntegerField(verbose_name = 'Switch Duration')

    def __unicode__(self):
        return self.dn_source + ' >> ' + self.dn_destination + ' @ ' + self.duration + 's'

CH_MOD_TYPE = (
    (1, 'MOD_INCLUDE'),
    (2, 'MOD_BUNDLE'),
    (3, 'MOD_VOLUME')
)

class LcrRetailServiceModDestination(models.Model):
    service = models.ForeignKey('LcrRetailService')
    mod_type = models.IntegerField(choices = CH_MOD_TYPE, verbose_name = 'Modifier Type')
    destination = models.ForeignKey('LcrRetailDestination')

    def __unicode__(self):
        return self.get_mod_type_display() + ' @ ' + unicode(self.service) + ' + ' + unicode(self.destination)

class LcrRetailCallCost(models.Model):
    partner = models.ForeignKey('LcrPartner')
    cdr = models.ForeignKey('LcrRetailCDR')
    period = models.ForeignKey('LcrRetailBillPeriod')
    mod_type = models.IntegerField(choices = CH_MOD_TYPE, verbose_name = 'Modifier Type')
    mod_id = models.IntegerField(verbose_name = 'Modifier Origin ID')
    price = models.DecimalField(max_digits = 14, decimal_places = 4, verbose_name = 'Cost')

    def __unicode__(self):
        return 'Call Cost #' + str(self.id) + ': ' + str(self.price)

class LcrRetailBillPeriod(models.Model):
    partner = models.ForeignKey('LcrPartner')
    customer = models.ForeignKey('LcrRetailCustomer')
    service = models.ForeignKey('LcrRetailService')
    d_from = models.DateField(auto_now_add = False)
    d_to = models.DateField(auto_now_add = False)
    price_plan_base = models.DecimalField(max_digits = 14, decimal_places = 4, verbose_name = 'Base Plan Price')
    price_units_base = models.DecimalField(max_digits = 14, decimal_places = 4, verbose_name = 'Base Units Price')
    discount_plan = models.IntegerField(verbose_name = 'Plan Discount')
    discount_units = models.IntegerField(verbose_name = 'Units Discount')
    price_total = models.DecimalField(max_digits = 14, decimal_places = 4, verbose_name = 'Final Price')

    def __unicode__(self):
        return 'Bill Period #' + str(self.id) + ' (' + unicode(self.service) + ' @ ' + unicode(self.customer) +')'

class LcrRetailDestination(models.Model):
    partner = models.ForeignKey('LcrPartner')
    name = models.CharField(max_length = 150)
    sub_destinations = models.ManyToManyField("self", symmetrical = False, null = True, blank = True)

    def __unicode__(self):
        return self.name

    def match_number(self, number):
        for prefix in self.lcrretaildestinationprefix_set.all():
            if re.match(prefix.prefix, number):
                return True
        for destination in self.sub_destinations.all():
            if destination.match_number(number):
                return True
        return False

    def num_prefixes(self):
        return len(self.lcrretaildestinationprefix_set.all())

    def num_subdestinations(self):
        return len(self.sub_destinations.all())

    def get_prefixes(self):
        return self.lcrretaildestinationprefix_set.all()

class LcrRetailDestinationPrefix(models.Model):
    destination = models.ForeignKey('LcrRetailDestination')
    prefix = models.CharField(max_length = 50)

    def __unicode__(self):
        return self.prefix + ' @ ' + unicode(self.destination)

class LcrRetailDataCampaign(models.Model):
    code = models.CharField(max_length = 20)
    descr = models.CharField(max_length = 200)
    dt_when = models.DateTimeField(auto_now_add = True)

class LcrRetailData(models.Model):
    campaign = models.ForeignKey('LcrRetailDataCampaign')
    country = models.CharField(max_length = 200, null = True, blank = True)
    first_name = models.CharField(max_length = 100, null = True, blank = True)
    last_name = models.CharField(max_length = 100, null = True, blank = True)
    middle_name = models.CharField(max_length = 100, null = True, blank = True)
    business_name = models.CharField(max_length = 200, null = True, blank = True)
    addr_type = models.CharField(max_length = 20, null = True, blank = True)
    addr_name = models.CharField(max_length = 200, null = True, blank = True)
    addr_no = models.CharField(max_length = 20, null = True, blank = True)
    zip = models.CharField(max_length = 15, null = True, blank = True)
    town = models.CharField(max_length = 100, null = True, blank = True)
    state = models.CharField(max_length = 100, null = True, blank = True)
    phone_1 = models.CharField(max_length = 50, null = True, blank = True)
    phone_2 = models.CharField(max_length = 50, null = True, blank = True)
    phone_3 = models.CharField(max_length = 50, null = True, blank = True)
    mobile_1 = models.CharField(max_length = 50, null = True, blank = True)
    mobile_2 = models.CharField(max_length = 50, null = True, blank = True)
    mobile_3 = models.CharField(max_length = 50, null = True, blank = True)
    email = models.CharField(max_length = 50, null = True, blank = True)
    placed = models.SmallIntegerField(default = 0)
    answered = models.SmallIntegerField(default = 0)
    response = models.SmallIntegerField(default = 0)

class LcrRetailDSL(models.Model):
    number_from = models.BigIntegerField(default = 0)
    number_to = models.BigIntegerField(default = 0)
    techs = models.CharField(max_length = 20, default = '')

class LcrRetailARASipFriend(models.Model):
    agent = models.ForeignKey('LcrRetailAgent')
    name = models.CharField(max_length = 100)
    host = models.CharField(max_length = 30, default = 'dynamic')
    secret = models.CharField(max_length = 100)
    nat = models.CharField(max_length = 10, default = 'yes')
    allow = models.CharField(max_length = 100, default = 'alaw')
    disallow = models.CharField(max_length = 100, default = 'all')
    context = models.CharField(max_length = 100)
    type = models.CharField(max_length = 100, default = 'friend')
    ipaddr = models.CharField(max_length = 100, blank = True, null = True)
    port = models.IntegerField(blank = True, null = True)
    regseconds = models.IntegerField(blank = True, null = True)
    lastms = models.IntegerField(blank = True, null = True)
    useragent = models.CharField(max_length = 100, blank = True, null = True)
    defaultuser = models.CharField(max_length = 100, blank = True, null = True)
    fullcontact = models.CharField(max_length = 100, blank = True, null = True)
    regserver = models.CharField(max_length = 100, blank = True, null = True)

class LcrMVTSCalls(models.Model):
    mvts_id = models.IntegerField()
    json_calls = models.TextField()
    dt_when = models.DateTimeField(auto_now_add = True)

class LcrMVTSReport(models.Model):
    mvts_id = models.IntegerField()
    dt_day = models.DateField(auto_now_add = False)
    customer = models.CharField(max_length = 50)
    destination = models.CharField(max_length = 250)
    seconds = models.BigIntegerField()
    calls = models.BigIntegerField()
    failed = models.BigIntegerField()

class LcrMVTSAlertSession(models.Model):
    mvts_id = models.IntegerField()
    dt_when = models.DateTimeField(auto_now_add = True)

class LcrMVTSAlertCheck(models.Model):
    session = models.ForeignKey('LcrMVTSAlertSession')
    customer = models.CharField(max_length = 50)
    destination = models.CharField(max_length = 250)
    seconds = models.BigIntegerField()
    calls = models.BigIntegerField()
    failed = models.BigIntegerField()

class LcrRetailRSM(models.Model):
    user = models.ForeignKey(User)

class LcrRetailAgentCampaign(models.Model):
    code = models.CharField(max_length = 35)

CH_AG_LAN = (
    (1, 'English'),
    (2, 'Spanish')
)

CH_AG_STATUS = (
    (1, 'Offline'),
    (10, 'Offline'),
    (100, 'Online')
)

class LcrRetailAgent(models.Model):
    user = models.ForeignKey(User)
    campaign = models.ForeignKey('LcrRetailAgentCampaign')
    address = models.TextField()
    tax = models.CharField(max_length = 50, blank = True)
    pid = models.CharField(max_length = 50)
    company = models.CharField(max_length = 200, blank = True)
    iban = models.CharField(max_length = 50, blank = True)
    language = models.SmallIntegerField(choices = CH_AG_LAN)
    status = models.IntegerField(choices = CH_AG_STATUS, default = 1)
    phone = models.CharField(max_length = 50, blank = True, null = True, default = '0')

    def get_ara(self):
        return LcrRetailARASipFriend.objects.get(agent = self)

class LcrRobo01(models.Model):
    phone = models.CharField(max_length = 20)
    name = models.CharField(max_length = 100, blank = True, null = True)
    call_placed = models.DateTimeField(blank = True, null = True, auto_now_add = False)
    call_answered = models.IntegerField(default = 0)
    responses = models.CharField(max_length = 20, blank = True, null = True)

class LcrBTCDR(models.Model):
    ph_src = models.CharField(max_length = 35)
    ph_dest = models.CharField(max_length = 35)
    dt_when = models.DateTimeField(auto_now_add = False)
    duration = models.IntegerField()

class LcrBTDestination(models.Model):
    code = models.CharField(max_length = 20)
    prefix = models.CharField(max_length = 50)
    name = models.CharField(max_length = 200)

class LcrBTRate(models.Model):
    code = models.CharField(max_length = 20)
    price = models.DecimalField(max_digits = 14, decimal_places = 4)
    eff_date = models.DateField(auto_now_add = False)

class LcrBTCost(models.Model):
    cdr = models.ForeignKey('LcrBTCDR')
    destination = models.ForeignKey('LcrBTDestination')
    rate = models.ForeignKey('LcrBTRate')
    cost = models.DecimalField(max_digits = 14, decimal_places = 4)

CH_CG_STATUS = (
    (0, 'New'),
    (99, 'Ready')
)

CH_CG_COLUMN = (
    (1, '[NUM_SRC] - Source number (CLI)'),
    (2, '[NUM_DST] - Destination number'),
    (3, '[IP_SRC] - Source Address'),
    (4, '[IP_DST] - Destination Address'),
    (5, '[DT_INVITE] - Datetime of SIP INVITE (Call initiation)'),
    (6, '[DT_OK] - Datetime of SIP OK (Call establishment)'),
    (7, '[DT_BYE] - Datetime of hangup (Call termination)'),
    (8, '[SESS_ID_SRC] - Source Session ID'),
    (9, '[SESS_ID_DST] - Destination Session ID'),
    (10, '[BILL_S] - Billable time (s)'),
    (11, '[BILL_MS] - Billable time (ms)'),
    (12, '[CODEC_SRC] - Source Codec'),
    (13, '[CODEC_DST] - Destination Codec'),
    (14, '[SIP_PROFILE] - Softswitch Profile Name'),
    (91, '[CUSTOM1] - Custom Field #1'),
    (92, '[CUSTOM2] - Custom Field #2'),
    (93, '[CUSTOM3] - Custom Field #3'),
)

class LcrCDRGen(models.Model):
    partner = models.ForeignKey('LcrPartner')
    dt_when = models.DateTimeField(auto_now_add = True)
    status = models.IntegerField(verbose_name = 'Status', default = 0, choices = CH_CG_STATUS)
    cdr_src = models.FileField(verbose_name = 'Source CDR', upload_to = 'src_cdr')
    delimiter = models.CharField(max_length = 1, verbose_name = 'Delimiter')
    col_1 = models.IntegerField(verbose_name = 'Column 1', choices = CH_CG_COLUMN)
    col_2 = models.IntegerField(verbose_name = 'Column 2', choices = CH_CG_COLUMN)
    col_3 = models.IntegerField(verbose_name = 'Column 3', choices = CH_CG_COLUMN)
    col_4 = models.IntegerField(verbose_name = 'Column 4', choices = CH_CG_COLUMN)
    col_5 = models.IntegerField(verbose_name = 'Column 5', choices = CH_CG_COLUMN)
    col_6 = models.IntegerField(verbose_name = 'Column 6', choices = CH_CG_COLUMN)
    col_7 = models.IntegerField(verbose_name = 'Column 7', choices = CH_CG_COLUMN)
    col_8 = models.IntegerField(verbose_name = 'Column 8', choices = CH_CG_COLUMN)
    col_9 = models.IntegerField(verbose_name = 'Column 9', choices = CH_CG_COLUMN)
    col_10 = models.IntegerField(verbose_name = 'Column 10', choices = CH_CG_COLUMN)
    str_dt_src = models.CharField(max_length = 50, verbose_name = 'DT Format (SRC)')
    str_dt_dst = models.CharField(max_length = 50, verbose_name = 'DT Format (DST)')
    cdr_dst = models.CharField(max_length = 250, verbose_name = 'Destination Format')
    cdr_ftp = models.CharField(max_length = 250, verbose_name = 'Destination FTP URL')

CH_EM_STATUS = (
    (0, 'New'),
    (99, 'Ready')
)

class LcrEmailSubmitJob(models.Model):
    partner = models.ForeignKey('LcrPartner')
    filename = models.CharField(verbose_name = 'File Name', max_length = 50)
    count = models.BigIntegerField(default = 0)
    status = models.IntegerField(default = 0, choices = CH_EM_STATUS)
    campaign_1 = models.CharField(verbose_name = 'Campaign #1', blank = True, max_length = 100)
    campaign_2 = models.CharField(verbose_name = 'Campaign #2', blank = True, max_length = 100)
    scountry = models.CharField(verbose_name = 'S. Country', blank = True, max_length = 100)

class LcrEmailEntry(models.Model):
    sjob = models.ForeignKey('LcrEmailSubmitJob')
    email = models.CharField(blank = True, max_length = 200)

# --- FORMS --- #

class LcrInvoiceForm(ModelForm):

    class Meta:
        model = LcrInvoice
        fields = ('due_days', 'dt_from', 'dt_to')

class EmailSubmitJobForm(ModelForm):

    class Meta:
        model = LcrEmailSubmitJob
        fields = ('filename', 'campaign_1', 'campaign_2', 'scountry')

class RetailCallBackForm(ModelForm):

    class Meta:
        model = LcrRetailCallBack
        fields = ('dt_when_date', 'dt_when_time', 'comment')

# Requires Spain Django Contrib:
#
#class RetailCandidateForm(ModelForm):
#    account = ESCCCField()
#    document_number = ESIdentityCardNumberField()
#    zipcode = ESPostalCodeField()
#
#    class Meta:
#        model = LcrRetailCandidate
#        exclude = ('source_type', 'source_key', 'dt_input', 'dt_processed', 'operator', 'status', 'comment')
#        widgets = {
#            'province': ESProvinceSelect
#        }

class RetailCandidateStatusForm(ModelForm):

    class Meta:
        model = LcrRetailCandidate
        fields = ('status', 'comment')

class RetailAgentForm(ModelForm):

    class Meta:
        model = LcrRetailAgent
        exclude = ('user', 'campaign', 'status')

class RetailBasicForm(forms.Form):
    first_name = forms.CharField(max_length = 100)
    last_name = forms.CharField(max_length = 100)
    email = forms.EmailField()

class CDRGenForm(ModelForm):

    class Meta:
        model = LcrCDRGen
        exclude = ('partner', 'dt_when', 'status')

class RetailCustomerServiceForm(ModelForm):

    class Meta:
        model = LcrRetailCustomerService
        exclude = ('customer', 'switch', 'd_when')

class RetailCustomerForm(ModelForm):

    class Meta:
        model = LcrRetailCustomer
        exclude = ('partner', )

class RetailTariffPhoneForm(ModelForm):

    class Meta:
        model = LcrRetailTariffPhone
        exclude = ('partner', )

class RetailRatePhoneForm(ModelForm):

    class Meta:
        model = LcrRetailRatePhone
        exclude = ('tariff', )

class RetailServiceModDestinationForm(ModelForm):

    class Meta:
        model = LcrRetailServiceModDestination
        exclude = ('service', 'mod_type')

class RetailDestinationForm(ModelForm):

    class Meta:
        model = LcrRetailDestination
        exclude = ('partner', )

class RetailDestinationPrefixForm(ModelForm):

    class Meta:
        model = LcrRetailDestinationPrefix

class RetailServiceForm(ModelForm):

    class Meta:
        model = LcrRetailService
        exclude = ('partner', 'type' )

class RetailSPLandlineForm(ModelForm):

    class Meta:
        model = LcrRetailSPLandline
        exclude = ('service', )

class ReconForm(ModelForm):

    class Meta:
        model = LcrRecon
        exclude = ('author', 'dt_when', )

class AddTRForm(forms.Form):
    name = forms.CharField(max_length = 50, label = 'Route Name')
    ip_num = forms.CharField(max_length = 20, label = 'IP Address')

class CarrierForm(ModelForm):

    class Meta:
        model = LcrCarrier
        exclude = ('partner', 'info_dt', 'info_ip', )

class CustomerForm(ModelForm):

    class Meta:
        model = LcrCustomer
        exclude = ('carrier', )

class SupplierForm(ModelForm):

    class Meta:
        model = LcrSupplier
        exclude = ('carrier', )

class EscalationForm(ModelForm):

    class Meta:
        model = LcrEscalation
        exclude = ('partner', 'info_dt', 'info_ip', 'carrier', 'status' )

class EscalationResponseForm(ModelForm):

    class Meta:
        model = LcrEscalationResponse
        exclude = ('escalation', 'info_dt', 'author' )

class TestForm(ModelForm):

    class Meta:
        model = LcrTest
        exclude = ('status', 'dt_when', 'dt_stat', 'comment', )

class MonitorForm(ModelForm):

    class Meta:
        model = LcrMonitor
        exclude = ('status', 'dt_when', )

class PointForm(ModelForm):

    class Meta:
        model = LcrPoint
        exclude = ('dt_when', 'ident', )

class DealForm(ModelForm):

    class Meta:
        model = LcrDeal
        exclude = ('dt_when', )

class DestinationForm(ModelForm):

    class Meta:
        model = LcrDestination

class CodeForm(ModelForm):

    class Meta:
        model = LcrCode
        exclude = ('deal', )

class E164Form(ModelForm):

    class Meta:
        model = LcrDestinationE164
        exclude = ('destination', )

class CustomerIpForm(ModelForm):

    class Meta:
        model = LcrCustomerIp
        exclude = ('customer', )

class ViewTestForm(ModelForm):

    class Meta:
        model = LcrTest
        exclude = ('supplier', 'destination', 'gw_ip', 'prefix', 'is_direct', 'is_cli', 'is_fas', 'dt_when', 'dt_stat', )

class TestNumberForm(ModelForm):

    class Meta:
        model = LcrTestNumber
        exclude = ('test', )

TestNumberFormSet = formset_factory(TestNumberForm, extra = 10)

class AZForm(ModelForm):
        
    class Meta:
                model = LcrAZ
                exclude = ('user', 'dt_when', 'partner', )

class AZParseForm(forms.Form):
    col_name = forms.IntegerField(max_value = 10, label = 'Name Column #', initial = 1)
    col_code = forms.IntegerField(max_value = 10, label = 'Code Column #', initial = 2)
    col_price = forms.IntegerField(max_value = 10, label = 'Price Column #', initial = 3)

class USupplierForm(forms.Form):
    svform = forms.FileField(label = 'SV Interconnect Form')

CH_TZ = (
    (6, 'GMT-04'),
    (2, 'GMT+00'),
    (0, 'GMT+02')
)

class StatsForm(forms.Form):
    dt_from = forms.DateField(label = 'From Day')
    dt_to = forms.DateField(label = 'To Day')
    tz_delta = forms.ChoiceField(label = 'Time Zone', choices = CH_TZ)
    customer = forms.CharField(max_length = 50, label = 'Customer ID')
