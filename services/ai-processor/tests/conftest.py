"""
Pytest configuration and fixtures.
"""

import sys
import os

# Add src directory to path for imports
src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
sys.path.insert(0, os.path.abspath(src_path))

# Set environment to test mode
os.environ['TESTING'] = '1'

