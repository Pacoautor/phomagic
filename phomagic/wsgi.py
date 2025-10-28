

"""
WSGI config for phomagic project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'phomagic.settings')

application = get_wsgi_application()
