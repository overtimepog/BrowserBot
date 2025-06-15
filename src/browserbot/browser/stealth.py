"""
Stealth configuration and anti-detection measures for browser automation.
"""

import random
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from playwright.async_api import Page, BrowserContext
import asyncio

from ..core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StealthConfig:
    """Configuration for stealth browser settings."""
    
    # User agent settings
    randomize_user_agent: bool = True
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    ])
    
    # Viewport settings
    randomize_viewport: bool = True
    viewport_sizes: List[Dict[str, int]] = field(default_factory=lambda: [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 1280, "height": 720},
    ])
    
    # Timing settings
    randomize_timings: bool = True
    min_action_delay: float = 0.1  # seconds
    max_action_delay: float = 0.5  # seconds
    
    # Language and locale
    languages: List[str] = field(default_factory=lambda: ["en-US", "en"])
    locale: str = "en-US"
    timezone: str = "America/New_York"
    
    # WebGL and Canvas fingerprinting
    mask_webgl: bool = True
    mask_canvas: bool = True
    
    # WebRTC
    disable_webrtc: bool = True
    
    # Permissions
    deny_permissions: List[str] = field(default_factory=lambda: [
        "geolocation",
        "notifications",
        "camera",
        "microphone",
    ])


async def apply_stealth_settings(
    context: BrowserContext,
    config: StealthConfig
) -> None:
    """
    Apply stealth settings to browser context.
    
    Args:
        context: Playwright browser context
        config: Stealth configuration
    """
    logger.info("Applying stealth settings to browser context")
    
    # Select random user agent if enabled
    if config.randomize_user_agent and config.user_agents:
        user_agent = random.choice(config.user_agents)
        await context.set_extra_http_headers({"User-Agent": user_agent})
    
    # Apply additional stealth scripts
    await context.add_init_script(get_stealth_script(config))
    
    logger.info("Stealth settings applied successfully")


async def apply_page_stealth(
    page: Page,
    config: StealthConfig
) -> None:
    """
    Apply stealth settings to a specific page.
    
    Args:
        page: Playwright page instance
        config: Stealth configuration
    """
    # Override navigator properties
    await page.add_init_script("""
        // Override navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Override navigator.plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {
                    0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                }
            ]
        });
        
        // Override navigator.languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Override Permissions API
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
    """)
    
    # Add random mouse movements
    if config.randomize_timings:
        asyncio.create_task(simulate_human_behavior(page, config))


def get_stealth_script(config: StealthConfig) -> str:
    """
    Generate comprehensive stealth JavaScript to inject.
    
    Args:
        config: Stealth configuration
        
    Returns:
        JavaScript code to inject
    """
    script = """
    (() => {
        // Chrome runtime
        window.chrome = {
            runtime: {
                id: 'fake-extension-id',
                onMessage: { addListener: () => {} },
                sendMessage: () => {},
                connect: () => ({ postMessage: () => {}, onMessage: { addListener: () => {} } })
            },
            storage: { local: { get: () => {}, set: () => {} } }
        };
        
        // Console.debug fix
        const originalConsoleDebug = console.debug;
        console.debug = function() {
            if (arguments[0] && arguments[0].includes && arguments[0].includes('HeadlessChrome')) {
                return;
            }
            return originalConsoleDebug.apply(console, arguments);
        };
    """
    
    if config.mask_webgl:
        script += """
        // WebGL fingerprinting protection
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter.apply(this, arguments);
        };
        """
    
    if config.mask_canvas:
        script += """
        // Canvas fingerprinting protection
        const toDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function() {
            const context = this.getContext('2d');
            const imageData = context.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < imageData.data.length; i += 4) {
                imageData.data[i] = imageData.data[i] ^ 1;
                imageData.data[i + 1] = imageData.data[i + 1] ^ 1;
                imageData.data[i + 2] = imageData.data[i + 2] ^ 1;
            }
            context.putImageData(imageData, 0, 0);
            return toDataURL.apply(this, arguments);
        };
        """
    
    if config.disable_webrtc:
        script += """
        // Disable WebRTC
        const rtcConstructors = [
            'RTCPeerConnection',
            'webkitRTCPeerConnection',
            'mozRTCPeerConnection',
            'RTCSessionDescription',
            'RTCIceCandidate'
        ];
        rtcConstructors.forEach(constructor => {
            if (window[constructor]) {
                window[constructor] = undefined;
            }
        });
        """
    
    script += """
    })();
    """
    
    return script


async def simulate_human_behavior(
    page: Page,
    config: StealthConfig
) -> None:
    """
    Simulate human-like behavior on the page.
    
    Args:
        page: Playwright page instance
        config: Stealth configuration
    """
    while not page.is_closed():
        try:
            # Random mouse movement
            viewport = page.viewport_size
            if viewport:
                x = random.randint(0, viewport["width"])
                y = random.randint(0, viewport["height"])
                
                # Move mouse with random speed
                await page.mouse.move(x, y, steps=random.randint(5, 20))
                
            # Random delay between actions
            delay = random.uniform(
                config.min_action_delay,
                config.max_action_delay
            )
            await asyncio.sleep(delay)
            
        except Exception as e:
            logger.debug(f"Error in human behavior simulation: {e}")
            break


def get_random_viewport(config: StealthConfig) -> Dict[str, int]:
    """
    Get random viewport size from configuration.
    
    Args:
        config: Stealth configuration
        
    Returns:
        Viewport dimensions
    """
    if config.randomize_viewport and config.viewport_sizes:
        return random.choice(config.viewport_sizes)
    return {"width": 1920, "height": 1080}


def create_browser_args(stealth: bool = True) -> List[str]:
    """
    Create browser launch arguments for stealth mode.
    
    Args:
        stealth: Enable stealth arguments
        
    Returns:
        List of browser arguments
    """
    args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-infobars",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
        "--window-position=0,0",
        "--start-maximized",
    ]
    
    if stealth:
        args.extend([
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--allow-running-insecure-content",
            "--disable-features=IsolateOrigins",
            "--disable-site-isolation-trials",
            "--disable-features=BlockInsecurePrivateNetworkRequests",
            "--disable-features=ImprovedCookieControls",
        ])
    
    return args