# Resume Optimization System - Test Suite

This directory contains comprehensive tests for the resume optimization system, including unit tests, integration tests, end-to-end tests, and performance tests.

## Test Structure

```
tests/
├── conftest.py                    # Shared test fixtures and configuration
├── pytest.ini                    # Pytest configuration
├── run_tests.py                   # Test runner script
├── README.md                      # This file
├── test_conversation_manager.py   # Unit tests for ConversationManager
├── test_section_optimizer.py      # Unit tests for SectionOptimizer
├── test_job_matcher.py            # Unit tests for JobMatcher
├── test_feedback_analyzer.py      # Unit tests for FeedbackAnalyzer
├── test_version_manager.py        # Unit tests for VersionManager
├── test_mock_llm_provider.py      # Tests for mock LLM provider
├── test_integration_api.py        # Integration tests for API endpoints
├── test_end_to_end.py             # End-to-end workflow tests
└── test_performance.py            # Performance and load tests
```

## Test Categories

### 1. Unit Tests

- **Purpose**: Test individual service methods in isolation
- **Files**: `test_*_manager.py`, `test_*_optimizer.py`, `test_*_analyzer.py`
- **Coverage**: All service classes and their methods
- **Mocking**: Extensive use of mocks for dependencies

### 2. Integration Tests

- **Purpose**: Test API endpoints and database operations
- **Files**: `test_integration_api.py`
- **Coverage**: FastAPI endpoints, database CRUD operations, service integration
- **Environment**: Uses TestClient and mock databases

### 3. End-to-End Tests

- **Purpose**: Test complete user workflows
- **Files**: `test_end_to_end.py`
- **Coverage**: Full user journeys from resume upload to optimization
- **Scenarios**: Multiple optimization workflows, version management, error recovery

### 4. Performance Tests

- **Purpose**: Test system performance under load
- **Files**: `test_performance.py`
- **Coverage**: LLM response times, real-time features, concurrent operations
- **Metrics**: Response times, memory usage, throughput

## Running Tests

### Prerequisites

1. **Python 3.8+** is required
2. **Dependencies**: Install test dependencies
   ```bash
   pip install pytest pytest-asyncio pytest-mock pytest-cov httpx faker psutil
   ```

### Quick Start

```bash
# Run all tests
python tests/run_tests.py

# Run with coverage report
python tests/run_tests.py --coverage

# Run specific test categories
python tests/run_tests.py --unit
python tests/run_tests.py --integration
python tests/run_tests.py --e2e
python tests/run_tests.py --performance

# Run tests in parallel
python tests/run_tests.py --parallel 4

# Skip slow tests
python tests/run_tests.py --fast
```

### Direct Pytest Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_conversation_manager.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test method
pytest tests/test_conversation_manager.py::TestConversationManager::test_start_section_conversation_success

# Run tests matching pattern
pytest -k "conversation"

# Run tests with markers
pytest -m "unit"
pytest -m "not slow"
```

## Test Configuration

### Pytest Configuration (`pytest.ini`)

- Test discovery patterns
- Coverage settings
- Async test support
- Warning filters
- Custom markers

### Fixtures (`conftest.py`)

- Mock database
- Mock LLM provider
- Sample data (resume, job descriptions, etc.)
- Service factory functions
- Shared test utilities

## Test Data

### Sample Resume Data

```python
{
    "sections": {
        "personal_details": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "summary": "Experienced software engineer..."
        },
        "work_experience": [...],
        "education": [...],
        "skills": [...],
        "projects": [...]
    }
}
```

### Sample Job Description

- Realistic job posting text
- Multiple skill requirements
- Experience level specifications
- Industry-specific keywords

## Mocking Strategy

### Database Mocking

- In-memory dictionary-based mock
- CRUD operations simulation
- Query filtering support
- Concurrent access testing

### LLM Provider Mocking

- Configurable response times
- Response size tracking
- Error simulation
- Performance monitoring

### Service Mocking

- Method-level mocking
- Return value configuration
- Call tracking
- Exception simulation

## Test Scenarios

### Unit Test Scenarios

1. **Service Initialization**

   - Proper configuration loading
   - Strategy initialization
   - Database connection setup

2. **Core Functionality**

   - Method input validation
   - Business logic execution
   - Error handling
   - Edge cases

3. **Data Processing**
   - Content analysis
   - Optimization algorithms
   - Feedback generation
   - Version management

### Integration Test Scenarios

1. **API Endpoints**

   - Request/response validation
   - Authentication/authorization
   - Error handling
   - Content type validation

2. **Database Operations**

   - CRUD operations
   - Transaction handling
   - Concurrent access
   - Data consistency

3. **Service Integration**
   - Cross-service communication
   - Data flow validation
   - Error propagation
   - Performance impact

### End-to-End Test Scenarios

1. **Complete Resume Optimization**

   - Upload → Analyze → Optimize → Save
   - Multi-step user interactions
   - Data persistence verification

2. **Job-Targeted Optimization**

   - Job analysis → Resume matching → Targeted optimization
   - Skill gap identification
   - Recommendation generation

3. **Version Management**

   - Version creation → Comparison → Rollback
   - History tracking
   - Template creation

4. **Real-Time Features**
   - Live editing feedback
   - WebSocket simulation
   - Concurrent sessions

### Performance Test Scenarios

1. **LLM Performance**

   - Single request latency
   - Concurrent request handling
   - Batch processing efficiency
   - Error recovery performance

2. **Real-Time Features**

   - Feedback response times
   - Typing simulation
   - Memory usage monitoring
   - WebSocket performance

3. **System Load**
   - High-frequency operations
   - Concurrent user sessions
   - Database performance
   - Memory leak detection

## Coverage Goals

- **Overall Coverage**: 80%+
- **Service Classes**: 90%+
- **Critical Paths**: 95%+
- **Error Handling**: 85%+

## Performance Benchmarks

### Response Time Targets

- **LLM Requests**: < 500ms
- **Real-Time Feedback**: < 100ms
- **API Endpoints**: < 200ms
- **Database Operations**: < 50ms

### Throughput Targets

- **Concurrent Users**: 50+
- **Requests per Second**: 100+
- **Real-Time Sessions**: 20+

### Resource Usage Limits

- **Memory Growth**: < 100MB per hour
- **CPU Usage**: < 80% sustained
- **Database Connections**: < 20 concurrent

## Continuous Integration

### GitHub Actions Integration

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.9"
      - run: pip install -r requirements.txt
      - run: python tests/run_tests.py --coverage
      - uses: codecov/codecov-action@v3
```

### Pre-commit Hooks

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: python tests/run_tests.py --fast
        language: system
        pass_filenames: false
```

## Debugging Tests

### Common Issues

1. **Async Test Failures**

   - Ensure `pytest-asyncio` is installed
   - Use `@pytest.mark.asyncio` decorator
   - Check event loop configuration

2. **Mock Configuration**

   - Verify mock return values
   - Check call arguments
   - Reset mocks between tests

3. **Database State**
   - Ensure clean state between tests
   - Check transaction isolation
   - Verify data cleanup

### Debugging Commands

```bash
# Run single test with debugging
pytest -s -vv tests/test_conversation_manager.py::test_specific_method

# Run with pdb debugger
pytest --pdb tests/test_conversation_manager.py

# Run with coverage and show missing lines
pytest --cov=app --cov-report=term-missing tests/

# Run with profiling
pytest --profile tests/test_performance.py
```

## Contributing

### Adding New Tests

1. Follow naming conventions (`test_*.py`)
2. Use appropriate fixtures from `conftest.py`
3. Add docstrings explaining test purpose
4. Include both positive and negative test cases
5. Mock external dependencies
6. Add performance considerations for slow tests

### Test Quality Guidelines

1. **Isolation**: Tests should not depend on each other
2. **Repeatability**: Tests should produce consistent results
3. **Clarity**: Test names and structure should be self-documenting
4. **Coverage**: Aim for high code coverage with meaningful tests
5. **Performance**: Keep tests fast, mark slow tests appropriately

### Code Review Checklist

- [ ] Tests cover new functionality
- [ ] Edge cases are tested
- [ ] Error conditions are tested
- [ ] Mocks are properly configured
- [ ] Performance impact is considered
- [ ] Documentation is updated
