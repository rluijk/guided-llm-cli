# tests/conftest.py
import pytest
import sys
import os

# Add the parent directory of 'concepts' to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from concepts.generalized import AuthorListCLI

@pytest.fixture
def cli():
    return AuthorListCLI()