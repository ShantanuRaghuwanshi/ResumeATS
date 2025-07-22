"""
Performance tests for LLM integration and real-time features.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock
from concurrent.futures import ThreadPoolExecutor
import statistics


class TestLLMPerformance:
    """Performance tests for LLM integration."""

    @pytest.fixture
    def performance_llm_provider(self):
        """Create LLM provider with performance monitoring."""
        provider = AsyncMock()
        provider.call_times = []
        provider.response_sizes = []

        async def mock_generate_response(prompt, **kwargs):
            start_time = time.time()
            # Simulate LLM processing time
            await asyncio.sleep(0.1)  # 100ms simulated response time
            end_time = time.time()

            provider.call_times.append(end_time - start_time)
            response = f"Mock response for: {prompt[:50]}..."
            provider.response_sizes.append(len(response))
            return response

        provider.generate_response = mock_generate_response
        return provider

    @pytest.mark.asyncio
    async def test_llm_response_time_single_request(self, performance_llm_provider):
        """Test single LLM request response time."""
        start_time = time.time()

        response = await performance_llm_provider.generate_response(
            "Analyze this resume section for improvements"
        )

        end_time = time.time()
        response_time = end_time - start_time

        # Assertions
        assert response is not None
        assert response_time < 0.5  # Should respond within 500ms
        assert len(performance_llm_provider.call_times) == 1
        assert performance_llm_provider.call_times[0] < 0.2  # Mock processing time

    @pytest.mark.asyncio
    async def test_llm_concurrent_requests_performance(self, performance_llm_provider):
        """Test concurrent LLM requests performance."""
        num_requests = 10
        prompts = [f"Analyze resume section {i}" for i in range(num_requests)]

        start_time = time.time()

        # Execute concurrent requests
        tasks = [
            performance_llm_provider.generate_response(prompt) for prompt in prompts
        ]
        responses = await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        # Assertions
        assert len(responses) == num_requests
        assert all(response is not None for response in responses)
        assert total_time < 1.0  # Concurrent requests should be faster than sequential
        assert len(performance_llm_provider.call_times) == num_requests

        # Check average response time
        avg_response_time = statistics.mean(performance_llm_provider.call_times)
        assert avg_response_time < 0.2

    @pytest.mark.asyncio
    async def test_llm_batch_processing_performance(self, performance_llm_provider):
        """Test batch processing performance."""
        batch_size = 5
        num_batches = 3

        batch_times = []

        for batch_num in range(num_batches):
            batch_start = time.time()

            # Process batch
            batch_prompts = [f"Batch {batch_num}, item {i}" for i in range(batch_size)]

            batch_tasks = [
                performance_llm_provider.generate_response(prompt)
                for prompt in batch_prompts
            ]

            await asyncio.gather(*batch_tasks)

            batch_end = time.time()
            batch_times.append(batch_end - batch_start)

        # Assertions
        assert len(batch_times) == num_batches
        assert all(
            batch_time < 0.5 for batch_time in batch_times
        )  # Each batch under 500ms

        # Check consistency across batches
        batch_time_std = statistics.stdev(batch_times)
        assert batch_time_std < 0.1  # Low variance in batch processing times

    @pytest.mark.asyncio
    async def test_llm_memory_usage_monitoring(self, performance_llm_provider):
        """Test LLM memory usage during processing."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process multiple requests
        large_prompts = [
            "Analyze this very long resume section with detailed work experience: "
            + "x" * 1000
            for _ in range(20)
        ]

        tasks = [
            performance_llm_provider.generate_response(prompt)
            for prompt in large_prompts
        ]

        await asyncio.gather(*tasks)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Assertions
        assert memory_increase < 50  # Should not increase memory by more than 50MB
        assert len(performance_llm_provider.response_sizes) == 20

    @pytest.mark.asyncio
    async def test_llm_error_handling_performance(self, performance_llm_provider):
        """Test performance when handling LLM errors."""
        # Mock provider to occasionally fail
        original_generate = performance_llm_provider.generate_response
        call_count = 0

        async def failing_generate_response(prompt, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count % 3 == 0:  # Fail every 3rd request
                raise Exception("Mock LLM API error")

            return await original_generate(prompt, **kwargs)

        performance_llm_provider.generate_response = failing_generate_response

        # Test error handling performance
        num_requests = 10
        successful_responses = 0
        failed_requests = 0

        start_time = time.time()

        for i in range(num_requests):
            try:
                await performance_llm_provider.generate_response(f"Request {i}")
                successful_responses += 1
            except Exception:
                failed_requests += 1

        end_time = time.time()
        total_time = end_time - start_time

        # Assertions
        assert successful_responses > 0
        assert failed_requests > 0
        assert (
            total_time < 2.0
        )  # Error handling shouldn't significantly slow down processing
        assert successful_responses + failed_requests == num_requests


class TestRealTimeFeaturesPerformance:
    """Performance tests for real-time features."""

    @pytest.fixture
    def real_time_services(self, mock_database):
        """Create services for real-time testing."""
        from conftest import create_mock_feedback_analyzer

        feedback_analyzer = create_mock_feedback_analyzer(mock_database)

        # Mock real-time methods with performance tracking
        feedback_analyzer.processing_times = []

        original_generate_feedback = feedback_analyzer.generate_real_time_feedback

        async def timed_generate_feedback(*args, **kwargs):
            start_time = time.time()

            # Mock the internal methods for performance testing
            feedback_analyzer._calculate_readability_score = AsyncMock(return_value=0.8)
            feedback_analyzer._calculate_keyword_density = AsyncMock(
                return_value={"python": 0.1}
            )
            feedback_analyzer._identify_grammar_issues = AsyncMock(return_value=[])
            feedback_analyzer._generate_style_suggestions = AsyncMock(
                return_value=["suggestion"]
            )
            feedback_analyzer._generate_keyword_suggestions = AsyncMock(
                return_value=["keyword"]
            )
            feedback_analyzer._calculate_content_quality_score = AsyncMock(
                return_value=0.8
            )
            feedback_analyzer._calculate_ats_score = AsyncMock(return_value=0.85)

            result = await original_generate_feedback(*args, **kwargs)

            end_time = time.time()
            feedback_analyzer.processing_times.append(end_time - start_time)

            return result

        feedback_analyzer.generate_real_time_feedback = timed_generate_feedback
        return {"feedback_analyzer": feedback_analyzer}

    @pytest.mark.asyncio
    async def test_real_time_feedback_response_time(self, real_time_services):
        """Test real-time feedback response time."""
        feedback_analyzer = real_time_services["feedback_analyzer"]

        content = "Developed web applications using Python and React"

        start_time = time.time()

        feedback = await feedback_analyzer.generate_real_time_feedback(
            session_id="test-session",
            section="work_experience",
            current_content=content,
        )

        end_time = time.time()
        response_time = end_time - start_time

        # Assertions
        assert feedback is not None
        assert response_time < 0.1  # Real-time feedback should be under 100ms
        assert len(feedback_analyzer.processing_times) == 1

    @pytest.mark.asyncio
    async def test_real_time_feedback_typing_simulation(self, real_time_services):
        """Test real-time feedback during typing simulation."""
        feedback_analyzer = real_time_services["feedback_analyzer"]

        # Simulate user typing
        typing_sequence = [
            "D",
            "De",
            "Dev",
            "Deve",
            "Devel",
            "Develop",
            "Developed",
            "Developed web",
            "Developed web app",
            "Developed web applications",
            "Developed web applications using",
            "Developed web applications using Python",
        ]

        feedback_times = []

        for i, content in enumerate(typing_sequence):
            start_time = time.time()

            await feedback_analyzer.generate_real_time_feedback(
                session_id="typing-session",
                section="work_experience",
                current_content=content,
                previous_content=typing_sequence[i - 1] if i > 0 else None,
            )

            end_time = time.time()
            feedback_times.append(end_time - start_time)

        # Assertions
        assert len(feedback_times) == len(typing_sequence)
        assert all(time < 0.05 for time in feedback_times)  # Each feedback under 50ms
        assert statistics.mean(feedback_times) < 0.03  # Average under 30ms

    @pytest.mark.asyncio
    async def test_concurrent_real_time_sessions(self, real_time_services):
        """Test concurrent real-time feedback sessions."""
        feedback_analyzer = real_time_services["feedback_analyzer"]

        num_sessions = 5
        content_per_session = 10

        async def simulate_session(session_id):
            session_times = []

            for i in range(content_per_session):
                content = f"Session {session_id} content update {i}"

                start_time = time.time()

                await feedback_analyzer.generate_real_time_feedback(
                    session_id=f"session-{session_id}",
                    section="work_experience",
                    current_content=content,
                )

                end_time = time.time()
                session_times.append(end_time - start_time)

                # Small delay to simulate typing
                await asyncio.sleep(0.01)

            return session_times

        # Run concurrent sessions
        start_time = time.time()

        session_tasks = [
            simulate_session(session_id) for session_id in range(num_sessions)
        ]

        session_results = await asyncio.gather(*session_tasks)

        end_time = time.time()
        total_time = end_time - start_time

        # Assertions
        assert len(session_results) == num_sessions
        assert all(len(times) == content_per_session for times in session_results)

        # Check individual session performance
        for session_times in session_results:
            assert all(time < 0.1 for time in session_times)

        # Check overall performance
        all_times = [
            time for session_times in session_results for time in session_times
        ]
        assert statistics.mean(all_times) < 0.05
        assert total_time < 2.0  # All sessions should complete quickly

    @pytest.mark.asyncio
    async def test_websocket_simulation_performance(self, real_time_services):
        """Test WebSocket-like real-time communication performance."""
        feedback_analyzer = real_time_services["feedback_analyzer"]

        # Simulate WebSocket message queue
        message_queue = asyncio.Queue()
        response_times = []

        # Producer: simulate incoming messages
        async def message_producer():
            for i in range(50):
                message = {
                    "session_id": "websocket-session",
                    "content": f"Real-time update {i}",
                    "timestamp": time.time(),
                }
                await message_queue.put(message)
                await asyncio.sleep(0.02)  # 20ms between messages

        # Consumer: process messages and generate feedback
        async def message_consumer():
            processed_count = 0

            while processed_count < 50:
                try:
                    message = await asyncio.wait_for(message_queue.get(), timeout=1.0)

                    start_time = time.time()

                    await feedback_analyzer.generate_real_time_feedback(
                        session_id=message["session_id"],
                        section="work_experience",
                        current_content=message["content"],
                    )

                    end_time = time.time()
                    processing_time = end_time - start_time

                    # Include network latency simulation
                    total_time = end_time - message["timestamp"]
                    response_times.append(total_time)

                    processed_count += 1

                except asyncio.TimeoutError:
                    break

        # Run producer and consumer concurrently
        await asyncio.gather(message_producer(), message_consumer())

        # Assertions
        assert len(response_times) == 50
        assert all(time < 0.2 for time in response_times)  # Total response under 200ms
        assert statistics.mean(response_times) < 0.1  # Average under 100ms

    @pytest.mark.asyncio
    async def test_memory_usage_real_time_features(self, real_time_services):
        """Test memory usage during extended real-time operations."""
        import psutil
        import os

        feedback_analyzer = real_time_services["feedback_analyzer"]
        process = psutil.Process(os.getpid())

        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Simulate extended real-time session
        session_duration = 100  # Number of updates

        for i in range(session_duration):
            content = f"Extended session content update {i} " + "x" * (
                i * 10
            )  # Growing content

            await feedback_analyzer.generate_real_time_feedback(
                session_id="memory-test-session",
                section="work_experience",
                current_content=content,
            )

            # Check memory every 20 updates
            if i % 20 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = current_memory - initial_memory

                # Memory shouldn't grow excessively
                assert memory_increase < 100  # Less than 100MB increase

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = final_memory - initial_memory

        # Assertions
        assert total_memory_increase < 150  # Total increase under 150MB
        assert len(feedback_analyzer.processing_times) == session_duration

    @pytest.mark.asyncio
    async def test_database_performance_under_load(self, mock_database):
        """Test database performance under high load."""
        # Simulate high-frequency database operations
        num_operations = 1000
        operation_times = []

        async def database_operation(operation_id):
            start_time = time.time()

            # Create
            mock_database.create(
                "performance_test",
                f"key_{operation_id}",
                {"data": f"test_data_{operation_id}", "timestamp": time.time()},
            )

            # Read
            data = mock_database.read("performance_test", f"key_{operation_id}")
            assert data is not None

            # Update
            mock_database.update(
                "performance_test",
                f"key_{operation_id}",
                {"data": f"updated_data_{operation_id}", "timestamp": time.time()},
            )

            # Find
            results = mock_database.find(
                "performance_test", data=f"updated_data_{operation_id}"
            )
            assert len(results) > 0

            end_time = time.time()
            operation_times.append(end_time - start_time)

        # Execute operations concurrently
        start_time = time.time()

        tasks = [database_operation(i) for i in range(num_operations)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        # Assertions
        assert len(operation_times) == num_operations
        assert total_time < 5.0  # All operations should complete within 5 seconds
        assert statistics.mean(operation_times) < 0.01  # Average operation under 10ms
        assert max(operation_times) < 0.1  # No single operation over 100ms

    @pytest.mark.asyncio
    async def test_service_integration_performance(
        self, real_time_services, mock_database
    ):
        """Test performance of integrated service operations."""
        from conftest import (
            create_mock_conversation_manager,
            create_mock_section_optimizer,
        )

        conversation_manager = create_mock_conversation_manager(mock_database)
        section_optimizer = create_mock_section_optimizer(mock_database)
        feedback_analyzer = real_time_services["feedback_analyzer"]

        # Mock service methods
        conversation_manager._get_resume_data = AsyncMock(return_value={"sections": {}})
        conversation_manager._get_user_preferences = AsyncMock(return_value={})
        conversation_manager._generate_initial_message = AsyncMock(return_value=None)

        section_optimizer._analyze_section = AsyncMock(return_value=Mock())
        section_optimizer._generate_optimized_content = AsyncMock(
            return_value={"optimized": True}
        )
        section_optimizer._generate_section_suggestions = AsyncMock(return_value=[])
        section_optimizer._calculate_improvement_metrics = AsyncMock(
            return_value=Mock(improvement_percentage=15.0, ats_improvement=0.1)
        )
        section_optimizer._calculate_keyword_density = AsyncMock(return_value=0.05)
        section_optimizer._calculate_readability_score = AsyncMock(return_value=0.8)
        section_optimizer._generate_changes_summary = AsyncMock(return_value="Summary")

        # Test integrated workflow performance
        workflow_times = []

        for i in range(10):
            start_time = time.time()

            # Step 1: Start conversation
            session = await conversation_manager.start_section_conversation(
                resume_id=f"resume-{i}", user_id=f"user-{i}", section="work_experience"
            )

            # Step 2: Optimize section
            result = await section_optimizer.optimize_section(
                section_data={"test": "data"}, context=session.context
            )

            # Step 3: Generate real-time feedback
            await feedback_analyzer.generate_real_time_feedback(
                session_id=session.id,
                section="work_experience",
                current_content="test content",
            )

            end_time = time.time()
            workflow_times.append(end_time - start_time)

        # Assertions
        assert len(workflow_times) == 10
        assert all(time < 0.5 for time in workflow_times)  # Each workflow under 500ms
        assert statistics.mean(workflow_times) < 0.2  # Average under 200ms
