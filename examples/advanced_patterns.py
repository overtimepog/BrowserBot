"""
Advanced automation patterns and techniques with BrowserBot.
"""

import asyncio
from typing import List, Dict, Any
from browserbot import BrowserAgent
from browserbot.core.logger import get_logger
from browserbot.core.error_handler import GlobalErrorHandler
from browserbot.core.dead_letter_queue import get_dlq
from browserbot.monitoring.observability import trace_operation

logger = get_logger(__name__)


class AdvancedAutomationPatterns:
    """Advanced automation patterns and techniques."""
    
    def __init__(self):
        self.agent = None
        self.error_handler = GlobalErrorHandler.get_instance()
        self.dlq = get_dlq()
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.agent = BrowserAgent()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.agent:
            await self.agent.close()
    
    @trace_operation("parallel_browsing")
    async def parallel_browsing_example(self):
        """Example: Parallel browsing with multiple agents."""
        logger.info("Starting parallel browsing example")
        
        urls = [
            "https://httpbin.org/delay/1",
            "https://httpbin.org/delay/2", 
            "https://httpbin.org/delay/3",
            "https://httpbin.org/json",
            "https://httpbin.org/xml"
        ]
        
        # Create multiple agents for parallel processing
        agents = [BrowserAgent() for _ in range(3)]
        
        try:
            # Define tasks for each URL
            async def process_url(agent, url):
                return await agent.execute_task(
                    f"Go to {url} and extract any relevant data"
                )
            
            # Execute tasks in parallel
            tasks = []
            for i, url in enumerate(urls):
                agent = agents[i % len(agents)]  # Round-robin agent assignment
                tasks.append(process_url(agent, url))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            successful_results = []
            failed_results = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_results.append({
                        "url": urls[i],
                        "error": str(result)
                    })
                else:
                    successful_results.append({
                        "url": urls[i],
                        "result": result
                    })
            
            logger.info(
                "Parallel browsing completed",
                successful_count=len(successful_results),
                failed_count=len(failed_results)
            )
            
            return {
                "successful": successful_results,
                "failed": failed_results
            }
            
        finally:
            # Clean up all agents
            for agent in agents:
                await agent.close()
    
    @trace_operation("circuit_breaker_pattern")
    async def circuit_breaker_pattern_example(self):
        """Example: Circuit breaker pattern for unreliable services."""
        logger.info("Starting circuit breaker pattern example")
        
        # Simulate calling an unreliable service
        unreliable_urls = [
            "https://httpbin.org/status/500",  # Server error
            "https://httpbin.org/status/502",  # Bad gateway
            "https://httpbin.org/status/503",  # Service unavailable
            "https://httpbin.org/status/200",  # Success
        ]
        
        for url in unreliable_urls:
            try:
                result = await self.agent.execute_task(
                    f"Go to {url} and check the response status"
                )
                
                logger.info("Request successful", url=url, result=result)
                
            except Exception as e:
                # Handle error with circuit breaker
                error_result = await self.error_handler.handle_error(
                    error=e,
                    operation="unreliable_service_call",
                    context={"url": url},
                    recovery_enabled=True
                )
                
                logger.warning(
                    "Request failed, circuit breaker activated",
                    url=url,
                    error_id=error_result["error_id"]
                )
                
                # Add to DLQ if recovery fails
                if not error_result.get("recovery_result", {}).get("success"):
                    await self.dlq.add_message(
                        operation="failed_request",
                        payload={"url": url},
                        error=e,
                        max_retries=3
                    )
    
    @trace_operation("data_pipeline")
    async def data_pipeline_example(self):
        """Example: Data extraction and processing pipeline."""
        logger.info("Starting data pipeline example")
        
        # Step 1: Extract data from multiple sources
        sources = [
            {
                "url": "https://httpbin.org/json",
                "extractor": "json_data"
            },
            {
                "url": "https://httpbin.org/xml", 
                "extractor": "xml_data"
            },
            {
                "url": "https://httpbin.org/html",
                "extractor": "html_content"
            }
        ]
        
        extracted_data = []
        
        for source in sources:
            try:
                result = await self.agent.execute_task(
                    f"""
                    Go to {source['url']} and extract data using the {source['extractor']} method.
                    Return structured data that can be processed further.
                    """
                )
                
                extracted_data.append({
                    "source": source["url"],
                    "type": source["extractor"],
                    "data": result
                })
                
            except Exception as e:
                logger.error(
                    "Data extraction failed",
                    source=source["url"],
                    error=str(e)
                )
        
        # Step 2: Process and transform data
        processed_data = await self._process_extracted_data(extracted_data)
        
        # Step 3: Generate report
        report = await self._generate_data_report(processed_data)
        
        logger.info("Data pipeline completed", report=report)
        return report
    
    async def _process_extracted_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and transform extracted data."""
        processed = []
        
        for item in data:
            # Simulate data processing
            processed_item = {
                "source": item["source"],
                "type": item["type"],
                "processed_at": "2024-01-01T00:00:00Z",
                "data_size": len(str(item["data"])),
                "processed_data": item["data"]
            }
            processed.append(processed_item)
        
        return processed
    
    async def _generate_data_report(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary report of processed data."""
        return {
            "total_sources": len(data),
            "total_data_size": sum(item["data_size"] for item in data),
            "source_types": list(set(item["type"] for item in data)),
            "processing_summary": {
                item["source"]: {
                    "type": item["type"],
                    "size": item["data_size"]
                }
                for item in data
            }
        }
    
    @trace_operation("retry_with_backoff")
    async def retry_with_backoff_example(self):
        """Example: Retry pattern with exponential backoff."""
        logger.info("Starting retry with backoff example")
        
        from browserbot.core.retry import RetryableOperation
        
        max_attempts = 3
        operation_name = "flaky_operation"
        
        async with RetryableOperation(
            max_attempts=max_attempts,
            base_delay=1.0,
            exceptions=(Exception,)
        ) as retry_op:
            
            for attempt in range(max_attempts):
                try:
                    # Simulate a flaky operation
                    if attempt < 2:
                        # Force failure for first two attempts
                        await self.agent.execute_task(
                            "Go to https://httpbin.org/status/500"
                        )
                    else:
                        # Success on third attempt
                        result = await self.agent.execute_task(
                            "Go to https://httpbin.org/status/200 and confirm success"
                        )
                        
                        logger.info(
                            "Operation succeeded",
                            attempt=attempt + 1,
                            result=result
                        )
                        return result
                        
                except Exception as e:
                    logger.warning(
                        "Operation failed, will retry",
                        attempt=attempt + 1,
                        error=str(e)
                    )
                    
                    if retry_op.should_retry():
                        await retry_op.wait_before_retry()
                    else:
                        raise e
    
    @trace_operation("cache_pattern")
    async def caching_pattern_example(self):
        """Example: Caching pattern for expensive operations."""
        logger.info("Starting caching pattern example")
        
        # Simple in-memory cache
        cache = {}
        
        async def cached_operation(url: str) -> Dict[str, Any]:
            """Perform operation with caching."""
            cache_key = f"page_content_{url}"
            
            # Check cache first
            if cache_key in cache:
                logger.info("Cache hit", url=url)
                return cache[cache_key]
            
            # Cache miss - perform operation
            logger.info("Cache miss, fetching data", url=url)
            
            try:
                result = await self.agent.execute_task(
                    f"Go to {url} and extract the main content"
                )
                
                # Store in cache
                cache[cache_key] = {
                    "data": result,
                    "cached_at": "2024-01-01T00:00:00Z"
                }
                
                return cache[cache_key]
                
            except Exception as e:
                # On error, try to return stale cache data
                if cache_key in cache:
                    logger.warning(
                        "Using stale cache data due to error",
                        url=url,
                        error=str(e)
                    )
                    return cache[cache_key]
                raise
        
        # Test caching with repeated requests
        test_urls = [
            "https://httpbin.org/json",
            "https://httpbin.org/json",  # Should hit cache
            "https://httpbin.org/xml",
            "https://httpbin.org/json",  # Should hit cache again
        ]
        
        results = []
        for url in test_urls:
            result = await cached_operation(url)
            results.append(result)
        
        logger.info("Caching pattern completed", cache_size=len(cache))
        return results
    
    @trace_operation("health_monitoring")
    async def health_monitoring_example(self):
        """Example: Health monitoring and self-healing."""
        logger.info("Starting health monitoring example")
        
        from browserbot.monitoring.observability import health_checker
        
        # Register custom health checks
        def browser_health_check() -> Dict[str, Any]:
            """Check if browser is responsive."""
            try:
                # Simple check - this would be more sophisticated in practice
                return {
                    "healthy": True,
                    "message": "Browser is responsive",
                    "metadata": {"browser_version": "chromium-123"}
                }
            except Exception as e:
                return {
                    "healthy": False,
                    "message": f"Browser check failed: {str(e)}"
                }
        
        async def network_health_check() -> Dict[str, Any]:
            """Check network connectivity."""
            try:
                result = await self.agent.execute_task(
                    "Go to https://httpbin.org/get and verify network connectivity"
                )
                return {
                    "healthy": True,
                    "message": "Network connectivity OK",
                    "metadata": {"response": result}
                }
            except Exception as e:
                return {
                    "healthy": False,
                    "message": f"Network check failed: {str(e)}"
                }
        
        # Register health checks
        health_checker.register_check("browser", browser_health_check)
        health_checker.register_check("network", network_health_check)
        
        # Run health checks
        health_status = await health_checker.run_checks()
        
        logger.info("Health monitoring completed", status=health_status)
        
        # Take corrective action if unhealthy
        if not health_status["healthy"]:
            logger.warning("System is unhealthy, taking corrective action")
            await self._self_heal()
        
        return health_status
    
    async def _self_heal(self):
        """Perform self-healing actions."""
        logger.info("Performing self-healing actions")
        
        # Example self-healing actions:
        # 1. Restart browser
        # 2. Clear cache
        # 3. Reset network connections
        # 4. Notify monitoring systems
        
        try:
            # Restart browser agent
            await self.agent.close()
            self.agent = BrowserAgent()
            
            logger.info("Self-healing completed successfully")
            
        except Exception as e:
            logger.error("Self-healing failed", error=str(e))


async def main():
    """Run advanced automation patterns examples."""
    async with AdvancedAutomationPatterns() as patterns:
        
        examples = [
            ("Parallel Browsing", patterns.parallel_browsing_example),
            ("Circuit Breaker Pattern", patterns.circuit_breaker_pattern_example),
            ("Data Pipeline", patterns.data_pipeline_example),
            ("Retry with Backoff", patterns.retry_with_backoff_example),
            ("Caching Pattern", patterns.caching_pattern_example),
            ("Health Monitoring", patterns.health_monitoring_example),
        ]
        
        for name, example_func in examples:
            logger.info(f"Running advanced example: {name}")
            try:
                result = await example_func()
                logger.info(f"✅ {name} completed successfully", result=result)
            except Exception as e:
                logger.error(f"❌ {name} failed", error=str(e))
            
            # Wait between examples
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())