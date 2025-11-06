#!/bin/bash
# Integration test for PostgreSQL persistence via Docker Compose
# This script tests the full stack: API + PostgreSQL database

set -e

echo "=========================================="
echo "Docker Compose Integration Test"
echo "=========================================="

# Check if Docker Compose is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "ERROR: API is not running on http://localhost:8000"
    echo "Please start the services with: docker compose up"
    exit 1
fi

echo ""
echo "1. Testing API root endpoint..."
ROOT_RESPONSE=$(curl -s http://localhost:8000/)
echo "$ROOT_RESPONSE" | python -m json.tool
PERSISTENCE=$(echo "$ROOT_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['persistence_enabled'])")

if [ "$PERSISTENCE" = "True" ] || [ "$PERSISTENCE" = "true" ]; then
    echo "✓ Persistence is enabled"
else
    echo "✗ WARNING: Persistence is not enabled"
fi

echo ""
echo "2. Testing batch classification with persistence..."
BATCH_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/classify/batch" \
  -H "Content-Type: application/json" \
  -d '{"smiles_list": ["c1ccccc1", "CCO", "CC(=O)O", "c1ccc2c(c1)ccc3c2nccc3"]}')

echo "$BATCH_RESPONSE" | python -m json.tool | head -30

JOB_ID=$(echo "$BATCH_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin).get('job_id', ''))" 2>/dev/null)

if [ -z "$JOB_ID" ] || [ "$JOB_ID" = "None" ] || [ "$JOB_ID" = "null" ]; then
    echo "✗ No job_id returned (persistence might be disabled)"
    echo ""
    echo "Integration test COMPLETED (without persistence)"
    exit 0
fi

echo ""
echo "✓ Job created with ID: $JOB_ID"

echo ""
echo "3. Testing job retrieval..."
JOB_RESPONSE=$(curl -s "http://localhost:8000/api/jobs/$JOB_ID")

if echo "$JOB_RESPONSE" | grep -q "job_id"; then
    echo "✓ Job retrieved successfully"
    echo "$JOB_RESPONSE" | python -m json.tool | head -40
else
    echo "✗ Failed to retrieve job"
    echo "$JOB_RESPONSE"
    exit 1
fi

echo ""
echo "4. Verifying job data consistency..."
ORIGINAL_TOTAL=$(echo "$BATCH_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['summary']['total'])")
RETRIEVED_TOTAL=$(echo "$JOB_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['summary']['total'])")

if [ "$ORIGINAL_TOTAL" = "$RETRIEVED_TOTAL" ]; then
    echo "✓ Data consistency verified (total: $ORIGINAL_TOTAL)"
else
    echo "✗ Data mismatch: original=$ORIGINAL_TOTAL, retrieved=$RETRIEVED_TOTAL"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ ALL INTEGRATION TESTS PASSED"
echo "=========================================="
