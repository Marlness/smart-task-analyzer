# WSGI configuration for PythonAnywhere
# Replace 'yourusername' with your PythonAnywhere username

import os
import sys

# Add your project directory to the sys.path
path = '/home/yourusername/smart-task-analyzer'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

