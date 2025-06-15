#!/usr/bin/env python3
"""
Demonstration of production-grade error handling and monitoring in BrowserBot.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from browserbot.agents.browser_agent import BrowserAgent
from browserbot.core.error_handler import GlobalErrorHandler, RecoveryStrategy
from browserbot.core.errors import NetworkError, BrowserError, RateLimitError
from browserbot.monitoring.observability import observability, health_checker, trace_operation
from browserbot.core.logger import get_logger

logger = get_logger(__name__)


class ResilientBrowserBot:
    """
    Example of a resilient BrowserBot implementation with comprehensive
    error handling and monitoring.
    """
    
    def __init__(self):
        self.agent = BrowserAgent()
        self.error_handler = GlobalErrorHandler.get_instance()
        self._setup_health_checks()
    
    def _setup_health_checks(self):
        """Setup health check functions."""
        
        async def browser_health_check():
            """Check if browser automation is working."""
            try:
                stats = self.agent.browser_manager.get_stats()
                return {
                    "healthy": stats["total_browsers"] > 0,
                    "message": f"Browsers: {stats['active_browsers']}/{stats['total_browsers']}",
                    "metadata": stats
                }
            except Exception as e:
                return {
                    "healthy": False,
                    "message": f"Browser check failed: {str(e)}"
                }
        
        async def ai_health_check():
            """Check if AI model is accessible."""
            try:
                # Simple test to verify model is responding
                response = await self.agent.llm.ainvoke("Say 'OK'")
                return {
                    "healthy": True,
                    "message": "AI model responding",
                    "metadata": {"model": self.agent.model_name}
                }
            except Exception as e:
                return {
                    "healthy": False,
                    "message": f"AI model check failed: {str(e)}"
                }
        
        health_checker.register_check("browser", browser_health_check)
        health_checker.register_check("ai_model", ai_health_check)
    
    @trace_operation("execute_resilient_task")
    async def execute_task_with_monitoring(
        self,
        task: str,
        max_retries: int = 3
    ) -> dict:
        """
        Execute a task with full error handling and monitoring.
        """
        attempt = 0
        last_error = None
        
        while attempt < max_retries:
            try:
                logger.info(
                    "Starting task execution",
                    task=task,
                    attempt=attempt + 1,
                    max_retries=max_retries
                )
                
                # Execute with tracing
                async with observability.trace_operation(
                    "browser_task",
                    {"task": task, "attempt": attempt + 1}
                ) as span:
                    result = await self.agent.execute_task(task)
                    
                    if result.get("success"):
                        span.set_attribute("result.success", "true")
                        return result
                    else:
                        span.set_attribute("result.success", "false")
                        span.set_attribute("result.error", result.get("error", "Unknown"))
                        raise Exception(result.get("error", "Task failed"))
                        
            except Exception as e:
                last_error = e
                
                # Handle error with recovery
                error_result = await self.error_handler.handle_error(
                    error=e,
                    operation="browser_task",
                    context={
                        "task": task,
                        "attempt": attempt + 1,
                        "session_id": self.agent.session_id
                    },
                    recovery_enabled=True
                )
                
                # Check if recovery suggests retry
                recovery = error_result.get("recovery_result")
                if recovery and recovery.get("strategy") == "retry":
                    attempt += 1
                    wait_time = min(2 ** attempt, 30)  # Exponential backoff
                    logger.info(f"Retrying after {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                
                # Check for specific error types
                if isinstance(e, RateLimitError):
                    # Handle rate limiting
                    retry_after = getattr(e, 'retry_after', 60)
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    attempt += 1
                    continue
                
                elif isinstance(e, NetworkError):
                    # Network errors get more retries
                    if attempt < max_retries + 2:
                        attempt += 1
                        await asyncio.sleep(5)
                        continue
                
                # If no recovery possible, break
                break
        
        # All retries exhausted
        logger.error(
            "Task failed after all retries",
            task=task,
            attempts=attempt + 1,
            last_error=str(last_error)
        )
        
        return {
            "success": False,
            "error": str(last_error),
            "attempts": attempt + 1,
            "error_id": error_result.get("error_id") if 'error_result' in locals() else None
        }
    
    async def demonstrate_graceful_degradation(self):
        """
        Demonstrate graceful degradation when services fail.
        """
        logger.info("Demonstrating graceful degradation...")
        
        # Primary task with full features
        primary_task = "Navigate to https://example.com and take a screenshot"
        
        # Degraded alternatives
        degraded_tasks = [
            "Navigate to https://example.com without screenshot",
            "Get page title from https://example.com",
            "Check if https://example.com is accessible"
        ]
        
        # Try primary task
        result = await self.execute_task_with_monitoring(
            primary_task,
            max_retries=1
        )
        
        if not result.get("success"):
            logger.info("Primary task failed, trying degraded alternatives...")
            
            for degraded_task in degraded_tasks:
                result = await self.execute_task_with_monitoring(
                    degraded_task,
                    max_retries=1
                )
                
                if result.get("success"):
                    logger.info(f"Degraded task succeeded: {degraded_task}")
                    break
        
        return result
    
    async def demonstrate_circuit_breaker(self):
        """
        Demonstrate circuit breaker pattern.
        """
        logger.info("Demonstrating circuit breaker pattern...")
        
        # Get circuit breaker for a specific service
        breaker = self.error_handler.get_circuit_breaker("external_api")
        
        # Simulate multiple failures to trip the circuit
        for i in range(10):
            try:
                # Simulate API call that fails
                if i < 6:  # First 6 calls fail
                    raise NetworkError("API connection failed")
                else:
                    # Circuit should be open now
                    logger.info("API call would succeed, but circuit is open")
                    
            except Exception as e:
                try:
                    await breaker.async_call(
                        self._simulate_api_call,
                        success=(i >= 6)
                    )
                except Exception as circuit_error:
                    logger.warning(f"Circuit breaker: {circuit_error}")
                    
                    if "Circuit breaker is OPEN" in str(circuit_error):
                        logger.info("Circuit breaker is protecting the system")
                        await asyncio.sleep(2)  # Wait before continuing demo
    
    async def _simulate_api_call(self, success: bool = False):
        """Simulate an API call for demonstration."""
        if not success:
            raise NetworkError("Simulated API failure")
        return {"status": "ok"}
    
    async def demonstrate_error_patterns(self):
        """
        Demonstrate error pattern detection.
        """
        logger.info("Demonstrating error pattern detection...")
        
        # Generate some errors to create a pattern
        tasks = [
            "Click on non-existent element #fake-button",
            "Navigate to http://invalid-domain-12345.com",
            "Click on non-existent element #another-fake",
            "Navigate to http://another-invalid-domain.com",
            "Click on non-existent element #third-fake"
        ]
        
        for task in tasks:
            await self.execute_task_with_monitoring(task, max_retries=0)
            await asyncio.sleep(0.5)
        
        # Check error statistics
        stats = self.error_handler.get_error_stats()
        logger.info("Error statistics", stats=stats)
        
        if stats["patterns"]:
            logger.warning(
                "Error patterns detected!",
                patterns=stats["patterns"]
            )
    
    async def run_health_check(self):
        """Run and display health check results."""
        logger.info("Running health checks...")
        
        health_status = await health_checker.run_checks()
        
        logger.info(
            "Health check results",
            overall_healthy=health_status["healthy"],
            checks=health_status["checks"]
        )
        
        return health_status
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.agent.shutdown()


async def main():
    """Main demonstration function."""
    bot = ResilientBrowserBot()
    
    async with bot.agent:
        logger.info("=== BrowserBot Error Handling Demonstration ===")
        
        # 1. Run health checks
        logger.info("\n1. Health Checks")
        await bot.run_health_check()
        
        # 2. Demonstrate basic error handling and recovery
        logger.info("\n2. Basic Error Handling with Recovery")
        result = await bot.execute_task_with_monitoring(
            "Navigate to https://example.com and extract the main heading"
        )
        logger.info(f"Task result: {result}")
        
        # 3. Demonstrate graceful degradation
        logger.info("\n3. Graceful Degradation")
        await bot.demonstrate_graceful_degradation()
        
        # 4. Demonstrate circuit breaker
        logger.info("\n4. Circuit Breaker Pattern")
        await bot.demonstrate_circuit_breaker()
        
        # 5. Demonstrate error pattern detection
        logger.info("\n5. Error Pattern Detection")
        await bot.demonstrate_error_patterns()
        
        # 6. Final health check
        logger.info("\n6. Final Health Check")
        await bot.run_health_check()
        
        # 7. Display error statistics
        logger.info("\n7. Error Statistics")
        stats = bot.error_handler.get_error_stats()
        logger.info("Final error statistics", stats=stats)


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())