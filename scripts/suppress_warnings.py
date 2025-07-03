"""
Warning suppression module for urllib3 and other common warnings.
Import this module first in any script to suppress SSL warnings.
"""
import os
import warnings
import sys

# Set environment variables to suppress warnings
os.environ['PYTHONWARNINGS'] = 'ignore'
os.environ['URLLIB3_DISABLE_WARNINGS'] = '1'

# Suppress all warnings
warnings.filterwarnings('ignore')

# Specifically suppress urllib3 warnings
try:
    import urllib3
    urllib3.disable_warnings()
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Try to suppress NotOpenSSLWarning specifically
    try:
        from urllib3.exceptions import NotOpenSSLWarning
        warnings.filterwarnings('ignore', category=NotOpenSSLWarning)
        urllib3.disable_warnings(NotOpenSSLWarning)
    except (ImportError, AttributeError):
        pass
        
except ImportError:
    pass

# Suppress other common warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
