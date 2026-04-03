"""
conftest.py — pytest configuration for Meta OpenEnv test suite.
Ensures the repo root is on sys.path so all imports resolve cleanly.
"""
import sys
import os

# Add repo root to path once, here, so test files don't need sys.path hacks
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))