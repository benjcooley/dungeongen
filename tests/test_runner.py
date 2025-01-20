"""Test runner for all test cases."""

from typing import Set
from tests.test_passages import TestPassages, TestTags
from options import Options
from debug_config import debug_draw, DebugDrawFlags

def run_tests(tags: Set[TestTags] = {TestTags.ALL}) -> None:
    """Run all test cases matching the given tags.
    
    Args:
        tags: Set of tags indicating which tests to run
    """
    # Create test instances
    passage_tests = TestPassages()
    
    # Run each test suite
    passage_tests.run_tests(tags)
