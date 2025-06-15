#!/usr/bin/env python3
"""
Prometheus metrics server for BrowserBot monitoring.
"""

import asyncio
import logging
import sys
from typing import Optional
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from prometheus_client import start_http_server, Counter, Histogram, Gauge, Info
    from browserbot.core.config import settings
    from browserbot.core.logger import get_logger
    
    logger = get_logger(__name__)
    
    # Define metrics
    task_counter = Counter('browserbot_tasks_total', 'Total number of tasks executed', ['status'])
    task_duration = Histogram('browserbot_task_duration_seconds', 'Task execution duration')
    active_browsers = Gauge('browserbot_active_browsers', 'Number of active browser instances')
    system_info = Info('browserbot_system', 'System information')
    
    class MetricsServer:
        """Prometheus metrics server for BrowserBot."""
        
        def __init__(self, port: int = 8000):
            self.port = port
            self.server = None
            
        def start(self):
            """Start the metrics server."""
            try:
                logger.info(f"Starting metrics server on port {self.port}")
                
                # Set system info
                system_info.info({
                    'version': '0.1.0',
                    'python_version': sys.version.split()[0],
                    'platform': sys.platform
                })
                
                # Start HTTP server
                start_http_server(self.port)
                logger.info(f"Metrics server started successfully on port {self.port}")
                
                # Keep server running
                while True:
                    asyncio.sleep(60)  # Sleep for 60 seconds
                    
            except Exception as e:
                logger.error(f"Failed to start metrics server: {e}")
                raise
                
        def stop(self):
            """Stop the metrics server."""
            logger.info("Stopping metrics server")
            
    def main():
        """Main entry point for metrics server."""
        try:
            port = getattr(settings, 'metrics_port', 8000)
            server = MetricsServer(port)
            server.start()
        except KeyboardInterrupt:
            logger.info("Metrics server stopped by user")
        except Exception as e:
            logger.error(f"Metrics server error: {e}")
            sys.exit(1)
            
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    # Fallback minimal server if dependencies aren't available
    import http.server
    import socketserver
    import json
    
    class MinimalMetricsHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/metrics':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'# BrowserBot metrics (minimal mode)\n')
                self.wfile.write(b'browserbot_status 1\n')
            elif self.path == '/health':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "mode": "minimal"}).encode())
            else:
                self.send_response(404)
                self.end_headers()
                
        def log_message(self, format, *args):
            # Suppress HTTP server logs
            pass
    
    def main():
        """Minimal metrics server fallback."""
        port = 8000
        try:
            with socketserver.TCPServer(("", port), MinimalMetricsHandler) as httpd:
                print(f"Minimal metrics server started on port {port}")
                httpd.serve_forever()
        except Exception as e:
            print(f"Failed to start minimal metrics server: {e}")
            sys.exit(1)
            
    if __name__ == "__main__":
        main()