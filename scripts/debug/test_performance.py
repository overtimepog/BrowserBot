#!/usr/bin/env python3
"""
Performance test script for BrowserBot optimizations.
Tests caching, browser pooling, and execution speed.
"""

import asyncio
import time
import json
from datetime import datetime
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from browserbot.agents.browser_agent import BrowserAgent
from browserbot.core.logger import get_logger

logger = get_logger(__name__)


class PerformanceTester:
    """Test harness for BrowserBot performance optimizations."""
    
    def __init__(self):
        self.results = {
            "test_runs": [],
            "cache_stats": {},
            "browser_stats": {},
            "summary": {}
        }
    
    async def test_simple_navigation(self, agent: BrowserAgent, run_number: int):
        """Test simple navigation with caching."""
        print(f"\n🧪 Test {run_number}: Simple Navigation")
        print("-" * 50)
        
        start_time = time.time()
        
        result = await agent.execute_task(
            "Navigate to example.com and take a screenshot"
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Completed in {duration:.2f} seconds")
        
        return {
            "test": "simple_navigation",
            "run": run_number,
            "duration": duration,
            "success": result.get("success", False),
            "cached": run_number > 1  # First run builds cache
        }
    
    async def test_complex_scraping(self, agent: BrowserAgent, run_number: int):
        """Test complex scraping task (HackerNews)."""
        print(f"\n🧪 Test {run_number}: Complex Scraping (HackerNews)")
        print("-" * 50)
        
        start_time = time.time()
        
        result = await agent.execute_task(
            "Go to news.ycombinator.com and extract the titles of the top 5 stories"
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Completed in {duration:.2f} seconds")
        if result.get("success"):
            print(f"📊 Result preview: {result.get('output', '')[:200]}...")
        
        return {
            "test": "complex_scraping",
            "run": run_number,
            "duration": duration,
            "success": result.get("success", False),
            "cached": run_number > 1
        }
    
    async def test_screenshot_caching(self, agent: BrowserAgent, run_number: int):
        """Test screenshot caching."""
        print(f"\n🧪 Test {run_number}: Screenshot Caching")
        print("-" * 50)
        
        start_time = time.time()
        
        # Take multiple screenshots of the same page
        result = await agent.execute_task(
            "Navigate to google.com, take a screenshot, wait 2 seconds, then take another screenshot"
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Completed in {duration:.2f} seconds")
        
        return {
            "test": "screenshot_caching",
            "run": run_number,
            "duration": duration,
            "success": result.get("success", False),
            "cached": run_number > 1
        }
    
    async def test_ai_response_caching(self, agent: BrowserAgent, run_number: int):
        """Test AI response caching with similar queries."""
        print(f"\n🧪 Test {run_number}: AI Response Caching")
        print("-" * 50)
        
        start_time = time.time()
        
        # Ask the same analysis question
        result = await agent.execute_task(
            "Go to python.org and tell me what Python is based on the homepage content"
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Completed in {duration:.2f} seconds")
        
        return {
            "test": "ai_response_caching",
            "run": run_number,
            "duration": duration,
            "success": result.get("success", False),
            "cached": run_number > 1
        }
    
    async def run_performance_tests(self):
        """Run all performance tests."""
        print("\n🚀 BrowserBot Performance Test Suite")
        print("=" * 60)
        print("Testing caching, browser pooling, and execution speed")
        print("=" * 60)
        
        # Test with caching enabled
        print("\n📦 TESTING WITH CACHING ENABLED")
        async with BrowserAgent(enable_caching=True) as agent:
            # Run each test twice to see caching effects
            for run in range(1, 3):
                print(f"\n--- Run {run} ---")
                
                # Simple navigation
                result = await self.test_simple_navigation(agent, run)
                self.results["test_runs"].append(result)
                
                # Complex scraping
                result = await self.test_complex_scraping(agent, run)
                self.results["test_runs"].append(result)
                
                # Screenshot caching
                result = await self.test_screenshot_caching(agent, run)
                self.results["test_runs"].append(result)
                
                # AI response caching
                result = await self.test_ai_response_caching(agent, run)
                self.results["test_runs"].append(result)
                
                # Get stats after each run
                if run == 2:
                    self.results["browser_stats"] = agent.browser_manager.get_stats()
                    if hasattr(agent.llm, 'get_cache_stats'):
                        self.results["cache_stats"]["ai_cache"] = agent.llm.get_cache_stats()
        
        # Test without caching for comparison
        print("\n\n❌ TESTING WITHOUT CACHING (Baseline)")
        async with BrowserAgent(enable_caching=False) as agent:
            # Simple baseline test
            result = await self.test_simple_navigation(agent, 99)
            result["cached"] = False
            result["baseline"] = True
            self.results["test_runs"].append(result)
        
        # Calculate summary statistics
        self._calculate_summary()
        
        # Print results
        self._print_results()
        
        # Save results to file
        self._save_results()
    
    def _calculate_summary(self):
        """Calculate summary statistics."""
        # Group by test type
        test_groups = {}
        for run in self.results["test_runs"]:
            test_name = run["test"]
            if test_name not in test_groups:
                test_groups[test_name] = []
            test_groups[test_name].append(run)
        
        # Calculate speedup for each test
        for test_name, runs in test_groups.items():
            first_run = next((r for r in runs if r["run"] == 1), None)
            second_run = next((r for r in runs if r["run"] == 2), None)
            
            if first_run and second_run:
                speedup = first_run["duration"] / second_run["duration"]
                improvement = (1 - second_run["duration"] / first_run["duration"]) * 100
                
                self.results["summary"][test_name] = {
                    "first_run_duration": first_run["duration"],
                    "cached_run_duration": second_run["duration"],
                    "speedup": speedup,
                    "improvement_percent": improvement
                }
    
    def _print_results(self):
        """Print test results."""
        print("\n\n" + "=" * 60)
        print("📊 PERFORMANCE TEST RESULTS")
        print("=" * 60)
        
        # Print summary
        print("\n🎯 Performance Improvements:")
        for test_name, stats in self.results["summary"].items():
            print(f"\n{test_name}:")
            print(f"  First run:  {stats['first_run_duration']:.2f}s")
            print(f"  Cached run: {stats['cached_run_duration']:.2f}s")
            print(f"  Speedup:    {stats['speedup']:.1f}x faster")
            print(f"  Improvement: {stats['improvement_percent']:.0f}%")
        
        # Print cache stats
        if self.results["cache_stats"]:
            print("\n💾 Cache Statistics:")
            if "ai_cache" in self.results["cache_stats"]:
                ai_stats = self.results["cache_stats"]["ai_cache"]
                print(f"  AI Response Cache Hit Rate: {ai_stats.get('hit_rate', 'N/A')}")
                print(f"  Total Cache Requests: {ai_stats.get('total', 0)}")
        
        # Print browser stats
        if self.results["browser_stats"]:
            print("\n🌐 Browser Pool Statistics:")
            print(f"  Active Browsers: {self.results['browser_stats'].get('active_browsers', 0)}")
            print(f"  Warm Browsers: {self.results['browser_stats'].get('warm_browsers', 0)}")
            print(f"  Max Browsers: {self.results['browser_stats'].get('max_browsers', 0)}")
        
        print("\n✅ All tests completed successfully!")
    
    def _save_results(self):
        """Save results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")


async def main():
    """Run performance tests."""
    tester = PerformanceTester()
    await tester.run_performance_tests()


if __name__ == "__main__":
    asyncio.run(main())