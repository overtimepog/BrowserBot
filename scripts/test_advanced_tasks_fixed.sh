#!/bin/bash

# Advanced BrowserBot Test Suite (Fixed)
# Tests various complex browser automation scenarios

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/test_results_$(date +%Y%m%d_%H%M%S).log"

# Initialize counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

print_test() {
    echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "$LOG_FILE"
    echo -e "${BLUE}TEST:${NC} $1" | tee -a "$LOG_FILE"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n" | tee -a "$LOG_FILE"
}

run_task() {
    local task="$1"
    local test_name="$2"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -e "${GREEN}Running:${NC} $task\n" | tee -a "$LOG_FILE"
    
    # Run the task and capture exit code
    if ./run.sh task "$task" 2>&1 | tee -a "$LOG_FILE"; then
        echo -e "\n${GREEN}✓ Test $test_name completed${NC}\n" | tee -a "$LOG_FILE"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "\n${RED}✗ Test $test_name failed${NC}\n" | tee -a "$LOG_FILE"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    
    # Brief pause between tests
    sleep 2
}

# Simpler test tasks without complex characters
run_simple_test() {
    local task="$1"
    local test_name="$2"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    print_test "$test_name"
    
    # Create temp file for task
    local temp_task_file=$(mktemp)
    echo "$task" > "$temp_task_file"
    
    echo -e "${GREEN}Running:${NC} $task\n" | tee -a "$LOG_FILE"
    
    # Run using input from file to avoid shell escaping issues
    if ./run.sh task "$(cat "$temp_task_file")" 2>&1 | tee -a "$LOG_FILE"; then
        echo -e "\n${GREEN}✓ Test $test_name completed${NC}\n" | tee -a "$LOG_FILE"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "\n${RED}✗ Test $test_name failed${NC}\n" | tee -a "$LOG_FILE"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    
    rm -f "$temp_task_file"
    sleep 2
}

# Test Suite Header
echo -e "${BLUE}🧪 BrowserBot Advanced Test Suite (Fixed)${NC}" | tee "$LOG_FILE"
echo -e "${YELLOW}Testing complex browser automation scenarios...${NC}\n" | tee -a "$LOG_FILE"
echo -e "Results will be logged to: $LOG_FILE\n" | tee -a "$LOG_FILE"

# Basic Tests First
run_simple_test "Go to example.com and extract the page title" "0. Basic Sanity Check"

# Test 1: Multi-step navigation and extraction
run_simple_test "Go to wikipedia.org, search for artificial intelligence, and extract the first paragraph of the article" "1. Multi-step Navigation & Data Extraction"

# Test 2: Form interaction
run_simple_test "Go to duckduckgo.com, search for weather in San Francisco, and tell me what the current temperature is" "2. Form Interaction & Search"

# Test 3: Complex data extraction with filtering
run_simple_test "Go to news.ycombinator.com and extract the titles of the top 5 stories" "3. Simple Data Extraction"

# Test 4: Multi-page navigation
run_simple_test "Go to github.com/trending and find the name of the top Python repository" "4. Trending Repository Check"

# Test 5: Table data extraction (simplified)
run_simple_test "Go to wikipedia.org and search for List of countries by population, then extract the names of the top 5 most populous countries" "5. Table Data Extraction"

# Test 6: Dynamic content handling
run_simple_test "Go to example.com, take a screenshot, then navigate to httpbin.org/html and extract the main heading" "6. Dynamic Content & Screenshot"

# Test 7: Error handling
run_simple_test "Try to navigate to example.com/this-page-does-not-exist-404 and tell me what happens" "7. Error Handling & Recovery"

# Test 8: Simple interaction
run_simple_test "Go to google.com and search for OpenAI GPT-4" "8. Basic Search Interaction"

# Test 9: Price checking (simplified)
run_simple_test "Go to coingecko.com and find the current price of Bitcoin" "9. Price Extraction"

# Test 10: Content analysis (simplified) 
run_simple_test "Go to reddit.com/r/programming and extract the titles of the top 5 posts" "10. Reddit Content Analysis"

# Summary
echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "$LOG_FILE"
echo -e "${BLUE}Test Summary:${NC}" | tee -a "$LOG_FILE"
echo -e "Total Tests: $TOTAL_TESTS" | tee -a "$LOG_FILE"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}" | tee -a "$LOG_FILE"
echo -e "${RED}Failed: $FAILED_TESTS${NC}" | tee -a "$LOG_FILE"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}✅ All tests passed!${NC}" | tee -a "$LOG_FILE"
else
    echo -e "\n${YELLOW}⚠️  Some tests failed. Check $LOG_FILE for details.${NC}" | tee -a "$LOG_FILE"
fi

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n" | tee -a "$LOG_FILE"

# Exit with appropriate code
exit $FAILED_TESTS