"""Advanced stealth configuration with 2024 best practices."""

import random
import string
from typing import Dict, Any, Optional
from playwright.async_api import BrowserContext, Page

class AdvancedStealth:
    """Advanced stealth techniques from 2024 research and open source agents."""
    
    def __init__(self):
        self.user_agents = [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        ]
        
        self.viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
            {"width": 1440, "height": 900},
            {"width": 1280, "height": 720},
        ]
        
        self.locales = ["en-US", "en-GB", "en-CA", "en-AU"]
        self.timezones = ["America/New_York", "America/Chicago", "America/Los_Angeles", "Europe/London"]

    async def apply_stealth(self, context: BrowserContext) -> None:
        """Apply comprehensive stealth settings to browser context."""
        
        # Advanced CDP commands for deeper stealth
        await context.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override chrome property
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Remove automation indicators
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: Plugin},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    }
                ]
            });
            
            // Realistic permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Canvas fingerprint randomization
            const getImageData = CanvasRenderingContext2D.prototype.getImageData;
            CanvasRenderingContext2D.prototype.getImageData = function(sx, sy, sw, sh) {
                const data = getImageData.apply(this, arguments);
                // Add slight noise to canvas data
                for (let i = 0; i < data.data.length; i += 4) {
                    data.data[i] = data.data[i] + (Math.random() * 0.1) - 0.05;
                    data.data[i+1] = data.data[i+1] + (Math.random() * 0.1) - 0.05;
                    data.data[i+2] = data.data[i+2] + (Math.random() * 0.1) - 0.05;
                }
                return data;
            };
            
            // WebGL fingerprint protection
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
            
            // Audio context fingerprint protection
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                const audioContext = new AudioContext();
                const oscillator = audioContext.createOscillator();
                const analyser = audioContext.createAnalyser();
                const gain = audioContext.createGain();
                const scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
                
                oscillator.type = 'triangle';
                oscillator.frequency.value = 10000;
                gain.gain.value = 0;
                
                oscillator.connect(analyser);
                analyser.connect(scriptProcessor);
                scriptProcessor.connect(gain);
                gain.connect(audioContext.destination);
                
                scriptProcessor.onaudioprocess = function(event) {
                    const output = event.outputBuffer.getChannelData(0);
                    for (let i = 0; i < output.length; i++) {
                        output[i] = output[i] + (Math.random() * 0.00001);
                    }
                };
            }
            
            // Battery API spoofing
            if ('getBattery' in navigator) {
                navigator.getBattery = async () => ({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 0.99,
                    addEventListener: () => {},
                    removeEventListener: () => {}
                });
            }
            
            // Connection API spoofing  
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    rtt: 50,
                    downlink: 10,
                    effectiveType: '4g',
                    saveData: false
                })
            });
            
            // Hardware concurrency randomization
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 4 + Math.floor(Math.random() * 4)
            });
            
            // Device memory randomization
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => [4, 8, 16, 32][Math.floor(Math.random() * 4)]
            });
        """)

    async def apply_page_stealth(self, page: Page) -> None:
        """Apply page-specific stealth enhancements."""
        
        # Randomize mouse movements
        await page.add_init_script("""
            // Natural mouse movement simulation
            let mouseX = 0;
            let mouseY = 0;
            
            document.addEventListener('mousemove', (e) => {
                mouseX = e.clientX;
                mouseY = e.clientY;
            });
            
            // Simulate micro-movements
            setInterval(() => {
                if (Math.random() > 0.95) {
                    const event = new MouseEvent('mousemove', {
                        clientX: mouseX + (Math.random() * 2 - 1),
                        clientY: mouseY + (Math.random() * 2 - 1),
                        bubbles: true
                    });
                    document.dispatchEvent(event);
                }
            }, 100);
            
            // Randomize scroll behavior
            let lastScrollTime = Date.now();
            window.addEventListener('wheel', (e) => {
                const now = Date.now();
                if (now - lastScrollTime < 50) {
                    e.preventDefault();
                }
                lastScrollTime = now;
            }, { passive: false });
        """)

    def get_random_user_agent(self) -> str:
        """Get a random user agent string."""
        return random.choice(self.user_agents)

    def get_random_viewport(self) -> Dict[str, int]:
        """Get random viewport dimensions."""
        viewport = random.choice(self.viewports)
        # Add slight variations
        return {
            "width": viewport["width"] + random.randint(-10, 10),
            "height": viewport["height"] + random.randint(-10, 10)
        }

    def get_random_locale(self) -> str:
        """Get random locale."""
        return random.choice(self.locales)

    def get_random_timezone(self) -> str:
        """Get random timezone."""
        return random.choice(self.timezones)

    async def human_like_typing(self, page: Page, selector: str, text: str) -> None:
        """Type with human-like delays and corrections."""
        element = await page.wait_for_selector(selector)
        
        for char in text:
            # Random typing speed between 50-200ms
            delay = random.randint(50, 200)
            
            # Occasionally make typos and correct them
            if random.random() < 0.05:  # 5% chance of typo
                wrong_char = random.choice(string.ascii_lowercase)
                await element.type(wrong_char, delay=delay)
                await page.wait_for_timeout(random.randint(100, 300))
                await element.press("Backspace")
                await page.wait_for_timeout(random.randint(50, 150))
            
            await element.type(char, delay=delay)
            
            # Occasional pauses (thinking)
            if random.random() < 0.1:  # 10% chance
                await page.wait_for_timeout(random.randint(500, 1500))

    async def human_like_mouse_movement(self, page: Page, x: int, y: int) -> None:
        """Move mouse with human-like curve."""
        # Get current position (approximate)
        current_x = random.randint(0, 1920)
        current_y = random.randint(0, 1080)
        
        # Create bezier curve points
        steps = random.randint(10, 20)
        
        for i in range(steps):
            progress = i / steps
            # Simple bezier curve
            next_x = current_x + (x - current_x) * progress
            next_y = current_y + (y - current_y) * progress
            
            # Add slight randomness
            next_x += random.randint(-5, 5)
            next_y += random.randint(-5, 5)
            
            await page.mouse.move(next_x, next_y)
            await page.wait_for_timeout(random.randint(10, 30))

    def generate_fingerprint_profile(self) -> Dict[str, Any]:
        """Generate a complete browser fingerprint profile."""
        return {
            "userAgent": self.get_random_user_agent(),
            "viewport": self.get_random_viewport(),
            "locale": self.get_random_locale(),
            "timezone": self.get_random_timezone(),
            "colorDepth": random.choice([24, 32]),
            "pixelRatio": random.choice([1, 1.5, 2, 2.5]),
            "platform": random.choice(["Win32", "MacIntel", "Linux x86_64"]),
            "memory": random.choice([4, 8, 16, 32]),
            "cores": random.choice([4, 6, 8, 12, 16]),
            "touchSupport": random.choice([0, 1, 5]),
            "webgl": {
                "vendor": random.choice(["Intel Inc.", "NVIDIA Corporation", "AMD"]),
                "renderer": random.choice([
                    "Intel Iris OpenGL Engine",
                    "NVIDIA GeForce GTX 1080",
                    "AMD Radeon Pro 5500M"
                ])
            }
        }