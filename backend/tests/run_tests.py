#!/usr/bin/env python3
"""
Test runner script for the resume optimization system.
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {description} failed")
        print(f"Return code: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Run tests for resume optimization system"
    )
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument(
        "--integration", action="store_true", help="Run integration tests only"
    )
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests only")
    parser.add_argument(
        "--performance", action="store_true", help="Run performance tests only"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Generate coverage report"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument(
        "--parallel", "-n", type=int, help="Run tests in parallel (number of workers)"
    )

    args = parser.parse_args()

    # Change to the backend directory
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)

    # Base pytest command
    pytest_cmd = ["python", "-m", "pytest"]

    # Add verbosity
    if args.verbose:
        pytest_cmd.extend(["-v", "-s"])

    # Add parallel execution
    if args.parallel:
        pytest_cmd.extend(["-n", str(args.parallel)])

    # Add coverage
    if args.coverage:
        pytest_cmd.extend(
            [
                "--cov=app",
                "--cov-report=html",
                "--cov-report=term-missing",
                "--cov-report=xml",
            ]
        )

    # Skip slow tests if requested
    if args.fast:
        pytest_cmd.extend(["-m", "not slow"])

    success = True

    # Run specific test categories
    if args.unit:
        cmd = pytest_cmd + [
            "-m",
            "unit",
            "tests/test_*_manager.py",
            "tests/test_*_optimizer.py",
            "tests/test_*_analyzer.py",
        ]
        success &= run_command(cmd, "Unit Tests")

    elif args.integration:
        cmd = pytest_cmd + ["-m", "integration", "tests/test_integration_*.py"]
        success &= run_command(cmd, "Integration Tests")

    elif args.e2e:
        cmd = pytest_cmd + ["-m", "e2e", "tests/test_end_to_end.py"]
        success &= run_command(cmd, "End-to-End Tests")

    elif args.performance:
        cmd = pytest_cmd + ["-m", "performance", "tests/test_performance.py"]
        success &= run_command(cmd, "Performance Tests")

    else:
        # Run all tests in sequence
        test_suites = [
            (
                [
                    "tests/test_conversation_manager.py",
                    "tests/test_section_optimizer.py",
                    "tests/test_job_matcher.py",
                    "tests/test_feedback_analyzer.py",
                    "tests/test_version_manager.py",
                ],
                "Unit Tests",
            ),
            (["tests/test_integration_api.py"], "Integration Tests"),
            (["tests/test_end_to_end.py"], "End-to-End Tests"),
            (["tests/test_performance.py"], "Performance Tests"),
        ]

        for test_files, description in test_suites:
            cmd = pytest_cmd + test_files
            suite_success = run_command(cmd, description)
            success &= suite_success

            if not suite_success:
                print(f"\n❌ {description} failed!")
            else:
                print(f"\n✅ {description} passed!")

    # Generate final report
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")

    if success:
        print("🎉 All tests passed successfully!")
        return 0
    else:
        print("❌ Some tests failed. Please check the output above.")
        return 1


def install_dependencies():
    """Install test dependencies."""
    print("Installing test dependencies...")

    dependencies = [
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "pytest-mock>=3.10.0",
        "pytest-cov>=4.0.0",
        "pytest-xdist>=3.0.0",  # For parallel execution
        "httpx>=0.24.0",  # For FastAPI testing
        "faker>=18.0.0",  # For generating test data
        "psutil>=5.9.0",  # For performance monitoring
    ]

    for dep in dependencies:
        cmd = [sys.executable, "-m", "pip", "install", dep]
        success = run_command(cmd, f"Installing {dep}")
        if not success:
            print(f"Failed to install {dep}")
            return False

    return True


def check_environment():
    """Check if the test environment is properly set up."""
    print("Checking test environment...")

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return False

    print(f"✅ Python version: {sys.version}")

    # Check if we're in the right directory
    if not Path("app").exists():
        print("❌ Not in the backend directory. Please run from backend/")
        return False

    print("✅ Directory structure looks correct")

    # Check if pytest is available
    try:
        import pytest

        print(f"✅ pytest version: {pytest.__version__}")
    except ImportError:
        print("❌ pytest not found. Installing dependencies...")
        if not install_dependencies():
            return False

    return True


if __name__ == "__main__":
    print("Resume Optimization System - Test Runner")
    print("=" * 60)

    if not check_environment():
        print("❌ Environment check failed")
        sys.exit(1)

    exit_code = main()
    sys.exit(exit_code)
