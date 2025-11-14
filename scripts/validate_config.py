#!/usr/bin/env python3
"""
Standalone configuration validation script
Run this to validate your environment configuration before deployment
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config.validator import main

if __name__ == '__main__':
    main()
