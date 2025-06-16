#!/bin/bash

# Advanced BrowserBot Test Suite
# Tests various complex browser automation scenarios

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_test() {
    echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}TEST:${NC} $1"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

run_task() {
    local task="$1"
    echo -e "${GREEN}Running:${NC} $task\n"
    ./run.sh task "$task"
    echo -e "\n${GREEN}✓ Test completed${NC}\n"
    sleep 2
}

# Test Suite
echo -e "${BLUE}🧪 BrowserBot Advanced Test Suite${NC}"
echo -e "${YELLOW}Testing complex browser automation scenarios...${NC}\n"

# Test 1: Multi-step navigation and extraction
print_test "1. Multi-step Navigation & Data Extraction"
run_task "Go to wikipedia.org, search for 'artificial intelligence', and extract the first paragraph of the article"

# Test 2: Form interaction
print_test "2. Form Interaction & Search"
run_task "Go to duckduckgo.com, search for 'weather in San Francisco', and tell me what the current temperature is"

# Test 3: Complex data extraction with filtering
print_test "3. Complex Data Extraction with Analysis"
run_task "Go to news.ycombinator.com, find all stories with more than 100 points, and list the top 3 by points"

# Test 4: Multi-page navigation
print_test "4. Multi-page Navigation"
run_task "Go to github.com/trending, find the top Python repository, navigate to it, and tell me what it does based on the README"

# Test 5: Table data extraction
print_test "5. Table Data Extraction"
run_task "Go to en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations) and extract the top 5 most populous countries with their populations"

# Test 6: Dynamic content handling
print_test "6. Dynamic Content & JavaScript"
run_task "Go to example.com, take a screenshot, then navigate to httpbin.org/html and extract the main heading"

# Test 7: Error handling
print_test "7. Error Handling & Recovery"
run_task "Try to navigate to a non-existent page like example.com/this-page-does-not-exist-404 and tell me what happens"

# Test 8: Complex interaction sequence
print_test "8. Complex Interaction Sequence"
run_task "Go to google.com, search for 'OpenAI GPT-4', click on the first result, and summarize what you find"

# Test 9: Data comparison
print_test "9. Data Comparison Task"
run_task "Go to coinmarketcap.com, find Bitcoin's current price, then go to coingecko.com and compare Bitcoin's price there. Tell me the difference if any"

# Test 10: Content analysis
print_test "10. Content Analysis"
run_task "Go to reddit.com/r/programming, analyze the top 5 posts and tell me what programming topics are trending today"

echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ All tests completed!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"