#!/bin/bash
# Run performance tests inside Docker container

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 BrowserBot Performance Test Suite${NC}"
echo "Testing optimizations in Docker container..."
echo "================================================"

# Ensure we're in the project root
cd "$PROJECT_ROOT"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please create a .env file with your API keys"
    exit 1
fi

# Start services with docker-compose
echo -e "\n${YELLOW}Starting BrowserBot services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to start...${NC}"
sleep 10

# Check if Redis is running
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is running${NC}"
else
    echo -e "${RED}❌ Redis is not responding${NC}"
    docker-compose logs redis
    exit 1
fi

# Check if BrowserBot container is running
if docker ps | grep -q browserbot; then
    echo -e "${GREEN}✅ BrowserBot container is running${NC}"
else
    echo -e "${RED}❌ BrowserBot container is not running${NC}"
    docker-compose logs browserbot
    exit 1
fi

# Run the performance test inside the container
echo -e "\n${YELLOW}Running performance tests...${NC}"
docker-compose exec -T browserbot python3 test_performance.py

# Show Redis cache stats
echo -e "\n${YELLOW}Redis Cache Statistics:${NC}"
docker-compose exec -T redis redis-cli -a browserbot123 --no-auth-warning INFO stats | grep -E "(keyspace_hits|keyspace_misses|total_commands_processed)"

# Show container resource usage
echo -e "\n${YELLOW}Container Resource Usage:${NC}"
docker stats --no-stream browserbot browserbot-redis

# Option to keep services running or stop them
echo -e "\n${YELLOW}Keep services running for inspection? (y/n)${NC}"
read -r keep_running

if [ "$keep_running" != "y" ]; then
    echo -e "${YELLOW}Stopping services...${NC}"
    docker-compose down
    echo -e "${GREEN}✅ Services stopped${NC}"
else
    echo -e "${GREEN}Services are still running${NC}"
    echo "To view logs: docker-compose logs -f"
    echo "To stop: docker-compose down"
    echo "VNC access: vncviewer localhost:5900 (password: browserbot)"
fi

echo -e "\n${GREEN}✅ Performance tests completed!${NC}"