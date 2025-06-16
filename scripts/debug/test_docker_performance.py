#!/usr/bin/env python3
"""
Performance test for BrowserBot in Docker environment.
"""

import asyncio
import time
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, '/home/browserbot/app')

from src.browserbot.agents.browser_agent import BrowserAgent


async def test_task_performance(task: str, runs: int = 3):
    """Test a specific task multiple times to measure caching impact."""
    print(f"\n🧪 Testing: {task}")
    print("=" * 60)
    
    timings = []
    
    async with BrowserAgent(enable_caching=True) as agent:
        for i in range(runs):
            print(f"\nRun {i+1}:")
            start = time.time()
            
            result = await agent.execute_task(task)
            
            duration = time.time() - start
            timings.append(duration)
            
            print(f"  ⏱️  Duration: {duration:.2f}s")
            print(f"  ✅ Success: {result.get('success', False)}")
            
            # Get browser stats
            stats = agent.browser_manager.get_stats()
            print(f"  🌐 Active browsers: {stats.get('active_browsers', 0)}")
            print(f"  🔥 Warm browsers: {stats.get('warm_browsers', 0)}")
            
            # Get cache stats if available
            if hasattr(agent.llm, 'get_cache_stats'):
                cache_stats = agent.llm.get_cache_stats()
                print(f"  💾 AI Cache: {cache_stats}")
            
            if stats.get('cache_stats'):
                print(f"  📊 Browser Cache: Hit rate {stats['cache_stats'].get('hit_rate', 0):.1f}%")
    
    # Calculate improvements
    if len(timings) >= 2:
        improvement = (timings[0] - timings[1]) / timings[0] * 100
        speedup = timings[0] / timings[1]
        
        print(f"\n📊 Performance Summary for: {task[:50]}...")
        print(f"  First run:  {timings[0]:.2f}s (cold cache)")
        print(f"  Second run: {timings[1]:.2f}s (warm cache)")
        if len(timings) >= 3:
            print(f"  Third run:  {timings[2]:.2f}s")
        print(f"\n  🚀 Speedup: {speedup:.1f}x faster")
        print(f"  📈 Improvement: {improvement:.0f}%")
    
    return timings


async def main():
    """Run performance tests."""
    print("\n🚀 BrowserBot Docker Performance Test")
    print("Testing with Redis caching enabled")
    print("=" * 60)
    
    # Test 1: Simple navigation
    await test_task_performance(
        "Navigate to example.com and tell me the main heading",
        runs=3
    )
    
    # Small delay between tests
    await asyncio.sleep(2)
    
    # Test 2: Complex task
    await test_task_performance(
        "Go to news.ycombinator.com and list the top 3 story titles",
        runs=2
    )
    
    print("\n\n✅ All tests completed!")
    print("\n💡 Key Insights:")
    print("  - First runs are slower (building cache)")
    print("  - Subsequent runs benefit from:")
    print("    • Warm browser instances")
    print("    • Cached AI responses")
    print("    • Cached DOM snapshots")
    print("    • Reduced delays")


if __name__ == "__main__":
    asyncio.run(main())