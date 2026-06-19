import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()


import traceback
import sys

original_application = application

def application(environ, start_response):
    try:
        return original_application(environ, start_response)
    except Exception:
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        raise