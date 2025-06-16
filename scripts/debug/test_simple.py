#!/usr/bin/env python3
"""
Simple performance test that can be run with: python3 -m browserbot.main --task "..."
"""

import asyncio
import time
from browserbot.agents.browser_agent import BrowserAgent


async def test_performance():
    """Run a simple performance test."""
    print("\n🧪 Testing BrowserBot Performance Optimizations")
    print("=" * 50)
    
    # Test task
    test_task = "Go to example.com and take a screenshot"
    
    print(f"\n📋 Test Task: {test_task}")
    print("\n🏃 Running test 3 times to measure caching impact...\n")
    
    async with BrowserAgent(enable_caching=True) as agent:
        timings = []
        
        for i in range(3):
            print(f"Run {i+1}:")
            start = time.time()
            
            result = await agent.execute_task(test_task)
            
            duration = time.time() - start
            timings.append(duration)
            
            print(f"  ✅ Completed in {duration:.2f}s")
            print(f"  Success: {result.get('success', False)}")
            
            # Show cache stats if available
            if hasattr(agent.browser_manager, 'get_stats'):
                stats = agent.browser_manager.get_stats()
                print(f"  Active browsers: {stats.get('active_browsers', 0)}")
                print(f"  Warm browsers: {stats.get('warm_browsers', 0)}")
                
                if 'cache_stats' in stats:
                    cache_stats = stats['cache_stats']
                    print(f"  Cache hit rate: {cache_stats.get('hit_rate', 0):.1f}%")
            
            print()
    
    # Calculate improvements
    if len(timings) >= 2:
        improvement = (timings[0] - timings[1]) / timings[0] * 100
        speedup = timings[0] / timings[1]
        
        print("\n📊 Performance Summary:")
        print(f"  First run:  {timings[0]:.2f}s (cold cache)")
        print(f"  Second run: {timings[1]:.2f}s (warm cache)")
        if len(timings) >= 3:
            print(f"  Third run:  {timings[2]:.2f}s")
        print(f"\n  🚀 Speedup: {speedup:.1f}x faster")
        print(f"  📈 Improvement: {improvement:.0f}%")
    
    print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(test_performance())