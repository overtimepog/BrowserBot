"""
Basic browser automation examples with BrowserBot.
"""

import asyncio
from browserbot import BrowserAgent
from browserbot.core.logger import get_logger

logger = get_logger(__name__)


async def basic_web_navigation():
    """Example: Basic web navigation and data extraction."""
    agent = BrowserAgent()
    
    try:
        # Navigate to a website
        result = await agent.execute_task(
            "Go to https://httpbin.org/get and extract the JSON response"
        )
        
        logger.info("Navigation result", result=result)
        
        # Take a screenshot
        screenshot_result = await agent.execute_task(
            "Take a screenshot of the current page"
        )
        
        logger.info("Screenshot saved", path=screenshot_result.get("screenshot_path"))
        
    except Exception as e:
        logger.error("Basic navigation failed", error=str(e))
    
    finally:
        await agent.close()


async def form_automation():
    """Example: Automated form filling."""
    agent = BrowserAgent()
    
    try:
        # Navigate to a form page
        await agent.execute_task(
            "Go to https://httpbin.org/forms/post"
        )
        
        # Fill out the form
        result = await agent.execute_task(
            """
            Fill out the form with the following information:
            - Customer name: John Doe
            - Telephone: +1-555-123-4567
            - Email: john.doe@example.com
            - Size: Medium
            - Topping: cheese
            - Delivery time: now
            - Comments: Please deliver to the front door
            """
        )
        
        logger.info("Form filled", result=result)
        
        # Submit the form
        submit_result = await agent.execute_task(
            "Submit the form and capture the response"
        )
        
        logger.info("Form submitted", result=submit_result)
        
    except Exception as e:
        logger.error("Form automation failed", error=str(e))
    
    finally:
        await agent.close()


async def search_and_extract():
    """Example: Search and data extraction."""
    agent = BrowserAgent()
    
    try:
        # Perform a search
        result = await agent.execute_task(
            """
            Go to DuckDuckGo and search for 'Python web scraping best practices'.
            Extract the titles and URLs of the first 5 search results.
            """
        )
        
        logger.info("Search results", results=result)
        
        # Click on the first result and extract content
        content_result = await agent.execute_task(
            "Click on the first search result and summarize the main points of the article"
        )
        
        logger.info("Article summary", content=content_result)
        
    except Exception as e:
        logger.error("Search and extraction failed", error=str(e))
    
    finally:
        await agent.close()


async def ecommerce_automation():
    """Example: E-commerce site automation."""
    agent = BrowserAgent()
    
    try:
        # Browse product catalog
        result = await agent.execute_task(
            """
            Go to https://fakestoreapi.com/ and browse the product catalog.
            Find products in the 'electronics' category and extract:
            - Product names
            - Prices
            - Ratings
            Return the top 3 highest-rated products.
            """
        )
        
        logger.info("Product search results", products=result)
        
        # Simulate adding to cart (on a demo site)
        cart_result = await agent.execute_task(
            "Add the highest-rated product to the shopping cart"
        )
        
        logger.info("Added to cart", result=cart_result)
        
    except Exception as e:
        logger.error("E-commerce automation failed", error=str(e))
    
    finally:
        await agent.close()


async def multi_page_workflow():
    """Example: Multi-page workflow automation."""
    agent = BrowserAgent()
    
    try:
        # Step 1: Login page
        await agent.execute_task(
            "Go to https://httpbin.org/basic-auth/testuser/testpass"
        )
        
        # Step 2: Navigate to different sections
        sections = [
            "Go to https://httpbin.org/json",
            "Go to https://httpbin.org/xml",
            "Go to https://httpbin.org/html"
        ]
        
        results = []
        for section in sections:
            result = await agent.execute_task(
                f"{section} and extract the main content"
            )
            results.append(result)
        
        logger.info("Multi-page workflow completed", results=results)
        
    except Exception as e:
        logger.error("Multi-page workflow failed", error=str(e))
    
    finally:
        await agent.close()


async def error_handling_example():
    """Example: Error handling and recovery."""
    agent = BrowserAgent()
    
    try:
        # Attempt to navigate to a non-existent page
        result = await agent.execute_task(
            "Go to https://httpbin.org/status/404 and handle the error gracefully"
        )
        
        logger.info("Error handling result", result=result)
        
        # Try alternative approach
        fallback_result = await agent.execute_task(
            "Since the previous page returned 404, go to https://httpbin.org/ instead"
        )
        
        logger.info("Fallback successful", result=fallback_result)
        
    except Exception as e:
        logger.error("Error handling example failed", error=str(e))
    
    finally:
        await agent.close()


async def main():
    """Run all examples."""
    examples = [
        ("Basic Web Navigation", basic_web_navigation),
        ("Form Automation", form_automation),
        ("Search and Extract", search_and_extract),
        ("E-commerce Automation", ecommerce_automation),
        ("Multi-page Workflow", multi_page_workflow),
        ("Error Handling", error_handling_example),
    ]
    
    for name, example_func in examples:
        logger.info(f"Running example: {name}")
        try:
            await example_func()
            logger.info(f"✅ {name} completed successfully")
        except Exception as e:
            logger.error(f"❌ {name} failed", error=str(e))
        
        # Wait between examples
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())