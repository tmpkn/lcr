# LCR VoIP Platform

Welcome to an Open Source release of LCR (formerly known as TrafiGuard, or simply TG). As the name might suggest, it is a voip platform, which originated as a wholesale trader's tool. It was in active development for 3 years, over which time it has been forked into multiple bespoke installations.

What you see here is a final stage product of these years. What began as a simple helper to manage VoipSwitch servers, grew into quite a complex platform.

As we decided to cease all our wholesale related developments, I feel it is the only proper way to preserve all those years of sleepless night by releasing the software as Open Source.

# Features

- Wholesale grade billing, successfully used in production with Tier 1 operators: Verizon, TATA, T-Mobile, BT UK, BT Spain
- Support for multiple SBCs:
	1. **Freeswitch** (full featured integration)
	2. **VoipSwitch** (Windows based softswitch) - including daisy chain setups
	3. Mera **MVTS**-II / MVTS Pro
	4. **Cisco** (Radius)
	5. **Asterisk** PBX
- Traffic Monitoring with Dynamic & Static Alerts
- Partner / Carrier model
- Carrier website, including tickets, stats & escalations
- Reusable Destinations model (address + e164 prefixes + prices)
- Test scheduling and reporting
- CDR Tools:
	1. Live FTP Export (incl. rating)
	2. Offline Export
	3. CDRGEN - Format Editor
- Traffic Reconciliation - with advanced ACD distribution analysis
- Retail Phone Sale Campaigns:
	1. Remote SIP Agents
	2. Predictive Dialer with separate billing module
	3. Campaign websites
	4. Products / Discounts / Tariffs management
	5. Dynamic call script support based on a simple markup syntax

# Source Code

What you see here is the most complete version of the LCR platform, combined from a couple of separate instances to form the big picture. The only things that have been removed had to do with banking operations and were proprietary to customers that used them.

Initial commits will be a mess. The code was in production for a couple of years, forked and merged multiple times, and finally sandwiched into the release you see here. There will be typos, indentation issues, and so on. I will do my best to fix them, to achieve a usable basic installation.

# Instructions

At this stage it's too early to write a proper installation howto. As the time goes, I will add the remaining components, like SQL methods, LUA scripts for FS and so on.

The LCR itself is based on Django framework, so the first step would be to make sure your system supports it. Afterwards, make sure your settings.py are up to date and fill in your company details in views.py.

The preferred way of running LCR on production is using uWSGI.

More instructions, including the switch integration, will follow soon.

# Support

This project is no longer considered a commercial product and at the moment we offer no business support whatsoever. Shortly, I will set up a dedicated mailbox for people wishing to get involved in cleaning up the source code and further development.