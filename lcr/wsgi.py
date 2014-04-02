import os, sys

apache_configuration = os.path.dirname(__file__)
project = os.path.dirname(apache_configuration)
workspace = os.path.dirname(project)
sys.path.append(workspace)

sys.path.append('/usr/lib/python2.4/site-packages/django')

os.environ['DJANGO_SETTINGS_MODULE'] = 'lcr.settings'
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()