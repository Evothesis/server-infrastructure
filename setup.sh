#!/bin/bash

# Analytics Platform Setup Script
# This script sets up the complete analytics platform from scratch

set -e  # Exit on any error

echo "🚀 Starting Analytics Platform Setup..."

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found. Please run this script from the project root directory."
    exit 1
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down -v 2>/dev/null || true

# Remove any existing volumes to ensure clean start
echo "🧹 Cleaning up existing volumes..."
docker volume rm server-infrastructure_postgres_data 2>/dev/null || true

# Build and start containers
echo "🏗️  Building and starting containers..."
docker-compose up -d --build

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if docker-compose exec -T postgres pg_isready -U postgres -d postgres &>/dev/null; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ PostgreSQL failed to start after $max_attempts attempts"
        docker-compose logs postgres
        exit 1
    fi
    
    echo "⏳ Attempt $attempt/$max_attempts - PostgreSQL not ready yet..."
    sleep 2
    ((attempt++))
done

# Wait for FastAPI to be ready
echo "⏳ Waiting for FastAPI to be ready..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:8000/health &>/dev/null; then
        echo "✅ FastAPI is ready!"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ FastAPI failed to start after $max_attempts attempts"
        docker-compose logs fastapi
        exit 1
    fi
    
    echo "⏳ Attempt $attempt/$max_attempts - FastAPI not ready yet..."
    sleep 2
    ((attempt++))
done

# Verify database schema
echo "🔍 Verifying database schema..."
table_count=$(docker-compose exec -T postgres psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')

if [ "$table_count" -ge 5 ]; then
    echo "✅ Database schema created successfully ($table_count tables found)"
else
    echo "❌ Database schema creation failed (only $table_count tables found)"
    exit 1
fi

# Check if ETL functions exist
echo "🔍 Verifying ETL functions..."
function_count=$(docker-compose exec -T postgres psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM pg_proc WHERE proname LIKE '%etl%' OR proname LIKE 'process_%' OR proname LIKE 'safe_jsonb%';" | tr -d ' ')

if [ "$function_count" -ge 8 ]; then
    echo "✅ ETL functions created successfully ($function_count functions found)"
else
    echo "❌ ETL functions creation failed (only $function_count functions found)"
    echo "📋 Available functions:"
    docker-compose exec -T postgres psql -U postgres -d postgres -c "\df process_*"
    docker-compose exec -T postgres psql -U postgres -d postgres -c "\df safe_*"
fi

# Test the tracking pixel
echo "🔍 Testing tracking pixel..."
if curl -s http://localhost/js/tracking.js | head -1 | grep -q "function"; then
    echo "✅ Tracking pixel is accessible"
else
    echo "❌ Tracking pixel is not accessible"
    exit 1
fi

# Test the test website
echo "🔍 Testing test website..."
if curl -s http://localhost/ | grep -q "Analytics Test Site"; then
    echo "✅ Test website is accessible"
else
    echo "❌ Test website is not accessible"
    exit 1
fi

# Display setup summary
echo ""
echo "🎉 Analytics Platform Setup Complete!"
echo ""
echo "📊 Services Status:"
echo "   • PostgreSQL:  http://localhost:5432"
echo "   • FastAPI:     http://localhost:8000"
echo "   • Test Site:   http://localhost"
echo "   • API Docs:    http://localhost:8000/docs"
echo ""
echo "🔧 Management Commands:"
echo "   • Check status:     curl http://localhost:8000/etl/status"
echo "   • Run ETL:          curl -X POST http://localhost:8000/etl/run-sync"
echo "   • View sessions:    curl http://localhost:8000/etl/recent-sessions"
echo ""
echo "📈 Next Steps:"
echo "   1. Visit http://localhost to generate test data"
echo "   2. Run ETL: curl -X POST http://localhost:8000/etl/run-sync"
echo "   3. View analytics: curl http://localhost:8000/etl/recent-sessions"
echo ""
echo "📚 For detailed documentation, see:"
echo "   • Project: README.md"
echo "   • Database: database/README.md"
echo ""