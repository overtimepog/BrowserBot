"""
Integration tests for error handling system.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

from browserbot.core.error_handler import ErrorHandler, RecoveryStrategy
from browserbot.core.errors import (
    BrowserBotError, ErrorSeverity, ErrorCategory, ErrorContext,
    NetworkError, RateLimitError, BrowserError, AIModelError
)
from browserbot.core.retry import CircuitBreaker, CircuitBreakerConfig
from browserbot.core.dead_letter_queue import DeadLetterQueue, MessageStatus


class TestErrorHandler:
    """Test error handler functionality."""
    
    @pytest.fixture
    def error_handler(self):
        """Create error handler for testing."""
        return ErrorHandler(enable_monitoring=False)
    
    @pytest.mark.asyncio
    async def test_basic_error_handling(self, error_handler):
        """Test basic error handling without recovery."""
        error = NetworkError("Connection failed")
        
        result = await error_handler.handle_error(
            error=error,
            operation="test_operation",
            context={"url": "https://example.com"},
            recovery_enabled=False
        )
        
        assert result["success"] is False
        assert result["error_type"] == "NetworkError"
        assert result["operation"] == "test_operation"
        assert result["recovery_attempted"] is False
        assert "error_id" in result
        assert result["user_response"].message == "Unable to connect to the service."
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, error_handler):
        """Test error recovery mechanisms."""
        error = RateLimitError("Rate limit exceeded", retry_after=60)
        
        # Mock recovery strategy
        with patch.object(error_handler, '_execute_recovery_strategy') as mock_recovery:
            mock_recovery.return_value = {
                "success": True,
                "strategy": "circuit_breaker", 
                "message": "Recovery successful"
            }
            
            result = await error_handler.handle_error(
                error=error,
                operation="api_call",
                recovery_enabled=True
            )
            
            assert result["recovery_result"]["success"] is True
            assert result["recovery_result"]["strategy"] == "circuit_breaker"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self, error_handler):
        """Test circuit breaker recovery strategy."""
        error = NetworkError("Service unavailable")
        
        # Mock a healthy circuit breaker
        breaker = Mock()
        breaker.state.state.value = "closed"
        
        with patch.object(error_handler, 'get_circuit_breaker', return_value=breaker):
            result = await error_handler._execute_recovery_strategy(
                RecoveryStrategy.CIRCUIT_BREAKER,
                error,
                "test_operation",
                {}
            )
            
            assert result["success"] is True
            assert result["strategy"] == "circuit_breaker"
    
    @pytest.mark.asyncio
    async def test_cache_recovery(self, error_handler):
        """Test cache recovery strategy."""
        error = NetworkError("Network timeout")
        context = {"cached_result": {"data": "cached_value"}}
        
        result = await error_handler._execute_recovery_strategy(
            RecoveryStrategy.CACHE,
            error,
            "data_fetch",
            context
        )
        
        assert result["success"] is True
        assert result["strategy"] == "cache"
        assert result["data"] == {"data": "cached_value"}
    
    def test_user_error_response_formatting(self, error_handler):
        """Test user-friendly error response formatting."""
        error = RateLimitError("Rate limit exceeded", retry_after=120)
        error_id = "test-error-123"
        
        response = error_handler.format_user_response(error, error_id)
        
        assert response.message == "Too many requests. Please slow down."
        assert response.action == "Wait a moment before trying again."
        assert response.error_id == error_id
        assert response.additional_info["retry_after"] == 120
    
    @pytest.mark.asyncio
    async def test_error_pattern_analysis(self, error_handler):
        """Test error pattern identification."""
        # Simulate multiple similar errors
        for i in range(15):
            error_handler._buffer_error(
                NetworkError("Connection timeout"),
                "api_request",
                {"attempt": i}
            )
        
        patterns = error_handler._identify_patterns()
        
        assert len(patterns) == 1
        assert patterns[0].error_type == "NetworkError"
        assert patterns[0].frequency == 15
    
    def test_error_statistics(self, error_handler):
        """Test error statistics collection."""
        # Add some test errors
        error_handler._buffer_error(NetworkError("Error 1"), "op1", {})
        error_handler._buffer_error(BrowserError("Error 2"), "op2", {})
        error_handler._buffer_error(NetworkError("Error 3"), "op1", {})
        
        stats = error_handler.get_error_stats()
        
        assert stats["total_errors"] == 3
        assert stats["error_types"]["NetworkError"] == 2
        assert stats["error_types"]["BrowserError"] == 1


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker for testing."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60,
            expected_exception=Exception
        )
        return CircuitBreaker(config)
    
    def test_circuit_breaker_normal_operation(self, circuit_breaker):
        """Test normal operation with circuit breaker."""
        def successful_operation():
            return "success"
        
        result = circuit_breaker.call(successful_operation)
        assert result == "success"
        assert circuit_breaker.state.failure_count == 0
    
    def test_circuit_breaker_failure_handling(self, circuit_breaker):
        """Test circuit breaker failure handling."""
        def failing_operation():
            raise Exception("Test failure")
        
        # First few failures should be allowed through
        for i in range(2):
            with pytest.raises(Exception):
                circuit_breaker.call(failing_operation)
        
        assert circuit_breaker.state.failure_count == 2
        assert circuit_breaker.state.state.value == "closed"
        
        # Third failure should open the circuit
        with pytest.raises(Exception):
            circuit_breaker.call(failing_operation)
        
        assert circuit_breaker.state.state.value == "open"
    
    def test_circuit_breaker_open_state(self, circuit_breaker):
        """Test circuit breaker in open state."""
        # Force circuit open
        circuit_breaker.state.failure_count = 5
        circuit_breaker.state.state.value = "open"
        circuit_breaker.state.last_failure_time = datetime.utcnow()
        
        def any_operation():
            return "should not execute"
        
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            circuit_breaker.call(any_operation)
    
    @pytest.mark.asyncio
    async def test_async_circuit_breaker(self, circuit_breaker):
        """Test async circuit breaker functionality."""
        async def successful_async_operation():
            return "async_success"
        
        result = await circuit_breaker.async_call(successful_async_operation)
        assert result == "async_success"


class TestDeadLetterQueue:
    """Test dead letter queue functionality."""
    
    @pytest.fixture
    def dlq(self, tmp_path):
        """Create DLQ for testing."""
        return DeadLetterQueue(
            storage_path=str(tmp_path / "dlq"),
            enable_persistence=False  # Disable for testing
        )
    
    @pytest.mark.asyncio
    async def test_add_message_to_dlq(self, dlq):
        """Test adding message to DLQ."""
        error = NetworkError("Connection failed")
        
        message_id = await dlq.add_message(
            operation="api_call",
            payload={"url": "https://api.example.com"},
            error=error,
            max_retries=3
        )
        
        assert message_id in dlq.messages
        message = dlq.messages[message_id]
        assert message.operation == "api_call"
        assert message.error_type == "NetworkError"
        assert message.status == MessageStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_retry_message(self, dlq):
        """Test message retry functionality."""
        # Add message to DLQ
        error = NetworkError("Test error")
        message_id = await dlq.add_message(
            operation="test_operation",
            payload={"data": "test"},
            error=error
        )
        
        # Register handler
        async def success_handler(payload):
            return {"success": True, "data": payload}
        
        dlq.register_handler("test_operation", success_handler)
        
        # Retry message
        success = await dlq.retry_message(message_id)
        
        assert success is True
        message = dlq.messages[message_id]
        assert message.status == MessageStatus.RESOLVED
        assert message.retry_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_message_failure(self, dlq):
        """Test message retry failure handling."""
        # Add message to DLQ
        error = NetworkError("Test error")
        message_id = await dlq.add_message(
            operation="failing_operation",
            payload={"data": "test"},
            error=error,
            max_retries=2
        )
        
        # Register failing handler
        async def failing_handler(payload):
            raise Exception("Handler failed")
        
        dlq.register_handler("failing_operation", failing_handler)
        
        # First retry should fail but allow more retries
        success = await dlq.retry_message(message_id)
        assert success is False
        
        message = dlq.messages[message_id]
        assert message.status == MessageStatus.PENDING
        assert message.retry_count == 1
        
        # Second retry should also fail but still allow one more
        success = await dlq.retry_message(message_id)
        assert success is False
        assert message.retry_count == 2
        assert message.status == MessageStatus.FAILED  # Max retries reached
    
    @pytest.mark.asyncio
    async def test_list_messages_with_filtering(self, dlq):
        """Test message listing with filters."""
        # Add different types of messages
        await dlq.add_message("op1", {}, NetworkError("Error 1"), max_retries=1)
        await dlq.add_message("op2", {}, BrowserError("Error 2"), max_retries=1)
        await dlq.add_message("op1", {}, AIModelError("Error 3"), max_retries=1)
        
        # Test filtering by operation
        op1_messages = await dlq.list_messages(operation="op1")
        assert len(op1_messages) == 2
        
        # Test filtering by status
        pending_messages = await dlq.list_messages(status=MessageStatus.PENDING)
        assert len(pending_messages) == 3
    
    @pytest.mark.asyncio
    async def test_dlq_statistics(self, dlq):
        """Test DLQ statistics collection."""
        # Add some messages
        await dlq.add_message("op1", {}, NetworkError("Error 1"), max_retries=1)
        await dlq.add_message("op2", {}, BrowserError("Error 2"), max_retries=1)
        
        stats = await dlq.get_stats()
        
        assert stats["total_messages"] == 2
        assert stats["status_counts"]["pending"] == 2
        assert stats["operation_counts"]["op1"] == 1
        assert stats["operation_counts"]["op2"] == 1
        assert "oldest_message" in stats
        assert "newest_message" in stats
    
    @pytest.mark.asyncio
    async def test_message_expiration(self, dlq):
        """Test message expiration handling."""
        # Add message with expiration
        error = NetworkError("Test error")
        message_id = await dlq.add_message(
            operation="test_op",
            payload={},
            error=error,
            expires_in=timedelta(seconds=1)
        )
        
        message = dlq.messages[message_id]
        assert not message.is_expired()
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        assert message.is_expired()
        assert not message.can_retry()
    
    @pytest.mark.asyncio
    async def test_bulk_retry(self, dlq):
        """Test bulk retry functionality."""
        # Add multiple messages
        for i in range(5):
            await dlq.add_message(
                f"op{i}",
                {"index": i},
                NetworkError(f"Error {i}"),
                max_retries=3
            )
        
        # Register handlers for some operations
        async def success_handler(payload):
            return {"success": True}
        
        dlq.register_handler("op0", success_handler)
        dlq.register_handler("op1", success_handler)
        # op2, op3, op4 have no handlers
        
        results = await dlq.retry_all_pending()
        
        assert results["total"] == 5
        assert results["successful"] == 2  # op0 and op1
        assert results["skipped"] == 3   # op2, op3, op4 (no handlers)
        assert results["failed"] == 0


class TestIntegratedErrorFlow:
    """Test integrated error handling flow."""
    
    @pytest.mark.asyncio
    async def test_complete_error_flow(self):
        """Test complete error handling flow with DLQ integration."""
        error_handler = ErrorHandler(enable_monitoring=False)
        dlq = DeadLetterQueue(enable_persistence=False)
        
        # Simulate operation failure
        async def failing_operation():
            raise NetworkError("Simulated network failure")
        
        # Handle the error
        try:
            await failing_operation()
        except Exception as e:
            # Handle error
            result = await error_handler.handle_error(
                error=e,
                operation="critical_operation",
                context={"url": "https://api.example.com"},
                recovery_enabled=True
            )
            
            # If recovery fails, add to DLQ
            if result["recovery_result"] is None:
                message_id = await dlq.add_message(
                    operation="critical_operation",
                    payload={"url": "https://api.example.com"},
                    error=e,
                    max_retries=3
                )
                
                # Register a handler for later retry
                async def recovery_handler(payload):
                    # Simulate successful recovery
                    return {"success": True, "data": "recovered"}
                
                dlq.register_handler("critical_operation", recovery_handler)
                
                # Retry the message
                retry_success = await dlq.retry_message(message_id)
                assert retry_success is True
                
                # Verify message was resolved
                message = await dlq.get_message(message_id)
                assert message.status == MessageStatus.RESOLVED
    
    @pytest.mark.asyncio
    async def test_error_escalation_chain(self):
        """Test error escalation through different recovery mechanisms."""
        error_handler = ErrorHandler(enable_monitoring=False)
        
        # Create a rate limit error
        rate_limit_error = RateLimitError("API rate limit exceeded", retry_after=300)
        
        # Mock circuit breaker to be open (no immediate retry)
        with patch.object(error_handler, 'get_circuit_breaker') as mock_breaker:
            breaker = Mock()
            breaker.state.state.value = "open"
            mock_breaker.return_value = breaker
            
            result = await error_handler.handle_error(
                error=rate_limit_error,
                operation="api_heavy_operation",
                recovery_enabled=True
            )
            
            # Should attempt circuit breaker strategy but fail due to open state
            assert result["recovery_attempted"] is True
            # Since circuit is open, should try degraded mode as fallback
            
        # Verify user gets appropriate message
        user_response = result["user_response"]
        assert "Too many requests" in user_response.message
        assert user_response.additional_info["retry_after"] == 300