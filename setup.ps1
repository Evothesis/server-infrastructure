# Analytics Platform Setup Script for Windows
# This script sets up the complete analytics platform from scratch

$ErrorActionPreference = "Stop"

Write-Host "Starting Analytics Platform Setup..." -ForegroundColor Green

# Check if Docker and Docker Compose are installed
try {
    docker --version | Out-Null
    Write-Host "Docker found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

try {
    docker-compose --version | Out-Null
    Write-Host "Docker Compose found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker Compose is not installed. Please install Docker Desktop with Compose." -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (!(Test-Path "docker-compose.yml")) {
    Write-Host "ERROR: docker-compose.yml not found. Please run this script from the project root directory." -ForegroundColor Red
    exit 1
}

# Stop any existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Yellow
try {
    docker-compose down -v 2>$null
} catch {
    # Ignore errors if no containers are running
}

# Remove any existing volumes to ensure clean start
Write-Host "Cleaning up existing volumes..." -ForegroundColor Yellow
try {
    docker volume rm server-infrastructure_postgres_data 2>$null
} catch {
    # Ignore errors if volume doesn't exist
}

# Build and start containers
Write-Host "Building and starting containers..." -ForegroundColor Yellow
docker-compose up -d --build

# Wait for PostgreSQL to be ready
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $result = docker-compose exec -T postgres pg_isready -U postgres -d postgres 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: PostgreSQL failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs postgres
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - PostgreSQL not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Wait for FastAPI to be ready
Write-Host "Waiting for FastAPI to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5 2>$null
        if ($response.StatusCode -eq 200) {
            Write-Host "FastAPI is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: FastAPI failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs fastapi
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - FastAPI not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Verify database schema
Write-Host "Verifying database schema..." -ForegroundColor Yellow
$tableCount = docker-compose exec -T postgres psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
$tableCount = $tableCount.Trim()

if ([int]$tableCount -ge 5) {
    Write-Host "SUCCESS: Database schema created successfully ($tableCount tables found)" -ForegroundColor Green
} else {
    Write-Host "ERROR: Database schema creation failed (only $tableCount tables found)" -ForegroundColor Red
    exit 1
}

# Check if ETL functions exist
Write-Host "Verifying ETL functions..." -ForegroundColor Yellow
$functionCount = docker-compose exec -T postgres psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM pg_proc WHERE proname LIKE '%etl%' OR proname LIKE 'process_%' OR proname LIKE 'safe_jsonb%';"
$functionCount = $functionCount.Trim()

if ([int]$functionCount -ge 6) {
    Write-Host "SUCCESS: ETL functions created successfully ($functionCount functions found)" -ForegroundColor Green
} else {
    Write-Host "WARNING: Some ETL functions may be missing (only $functionCount functions found)" -ForegroundColor Yellow
    Write-Host "Creating missing ETL functions..." -ForegroundColor Yellow
    
    # Create utility functions if missing
    $utilityCheck = docker-compose exec -T postgres psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM pg_proc WHERE proname LIKE 'safe_jsonb%';"
    if ([int]$utilityCheck.Trim() -lt 3) {
        Write-Host "Creating utility functions..." -ForegroundColor Yellow
        $UtilityFunctions = @"
CREATE OR REPLACE FUNCTION safe_jsonb_text(data JSONB, path TEXT, default_val TEXT DEFAULT NULL)
RETURNS TEXT AS `# Analytics Platform Setup Script for Windows
# This script sets up the complete analytics platform from scratch

$ErrorActionPreference = "Stop"

Write-Host "Starting Analytics Platform Setup..." -ForegroundColor Green

# Check if Docker and Docker Compose are installed
try {
    docker --version | Out-Null
    Write-Host "Docker found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

try {
    docker-compose --version | Out-Null
    Write-Host "Docker Compose found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker Compose is not installed. Please install Docker Desktop with Compose." -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (!(Test-Path "docker-compose.yml")) {
    Write-Host "ERROR: docker-compose.yml not found. Please run this script from the project root directory." -ForegroundColor Red
    exit 1
}

# Stop any existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Yellow
try {
    docker-compose down -v 2>$null
} catch {
    # Ignore errors if no containers are running
}

# Remove any existing volumes to ensure clean start
Write-Host "Cleaning up existing volumes..." -ForegroundColor Yellow
try {
    docker volume rm server-infrastructure_postgres_data 2>$null
} catch {
    # Ignore errors if volume doesn't exist
}

# Build and start containers
Write-Host "Building and starting containers..." -ForegroundColor Yellow
docker-compose up -d --build

# Wait for PostgreSQL to be ready
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $result = docker-compose exec -T postgres pg_isready -U postgres -d postgres 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: PostgreSQL failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs postgres
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - PostgreSQL not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Wait for FastAPI to be ready
Write-Host "Waiting for FastAPI to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5 2>$null
        if ($response.StatusCode -eq 200) {
            Write-Host "FastAPI is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: FastAPI failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs fastapi
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - FastAPI not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Verify database schema
Write-Host "Verifying database schema..." -ForegroundColor Yellow
$tableCount = docker-compose exec -T postgres psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
$tableCount = $tableCount.Trim()

if ([int]$tableCount -ge 5) {
    Write-Host "SUCCESS: Database schema created successfully ($tableCount tables found)" -ForegroundColor Green
} else {
    Write-Host "ERROR: Database schema creation failed (only $tableCount tables found)" -ForegroundColor Red
    exit 1
}

$
BEGIN
    RETURN COALESCE((data ->> path), default_val);
EXCEPTION WHEN OTHERS THEN
    RETURN default_val;
END;
`# Analytics Platform Setup Script for Windows
# This script sets up the complete analytics platform from scratch

$ErrorActionPreference = "Stop"

Write-Host "Starting Analytics Platform Setup..." -ForegroundColor Green

# Check if Docker and Docker Compose are installed
try {
    docker --version | Out-Null
    Write-Host "Docker found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

try {
    docker-compose --version | Out-Null
    Write-Host "Docker Compose found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker Compose is not installed. Please install Docker Desktop with Compose." -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (!(Test-Path "docker-compose.yml")) {
    Write-Host "ERROR: docker-compose.yml not found. Please run this script from the project root directory." -ForegroundColor Red
    exit 1
}

# Stop any existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Yellow
try {
    docker-compose down -v 2>$null
} catch {
    # Ignore errors if no containers are running
}

# Remove any existing volumes to ensure clean start
Write-Host "Cleaning up existing volumes..." -ForegroundColor Yellow
try {
    docker volume rm server-infrastructure_postgres_data 2>$null
} catch {
    # Ignore errors if volume doesn't exist
}

# Build and start containers
Write-Host "Building and starting containers..." -ForegroundColor Yellow
docker-compose up -d --build

# Wait for PostgreSQL to be ready
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $result = docker-compose exec -T postgres pg_isready -U postgres -d postgres 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: PostgreSQL failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs postgres
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - PostgreSQL not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Wait for FastAPI to be ready
Write-Host "Waiting for FastAPI to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5 2>$null
        if ($response.StatusCode -eq 200) {
            Write-Host "FastAPI is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: FastAPI failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs fastapi
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - FastAPI not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Verify database schema
Write-Host "Verifying database schema..." -ForegroundColor Yellow
$tableCount = docker-compose exec -T postgres psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
$tableCount = $tableCount.Trim()

if ([int]$tableCount -ge 5) {
    Write-Host "SUCCESS: Database schema created successfully ($tableCount tables found)" -ForegroundColor Green
} else {
    Write-Host "ERROR: Database schema creation failed (only $tableCount tables found)" -ForegroundColor Red
    exit 1
}

$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION safe_jsonb_int(data JSONB, path TEXT, default_val INTEGER DEFAULT NULL)
RETURNS INTEGER AS `# Analytics Platform Setup Script for Windows
# This script sets up the complete analytics platform from scratch

$ErrorActionPreference = "Stop"

Write-Host "Starting Analytics Platform Setup..." -ForegroundColor Green

# Check if Docker and Docker Compose are installed
try {
    docker --version | Out-Null
    Write-Host "Docker found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

try {
    docker-compose --version | Out-Null
    Write-Host "Docker Compose found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker Compose is not installed. Please install Docker Desktop with Compose." -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (!(Test-Path "docker-compose.yml")) {
    Write-Host "ERROR: docker-compose.yml not found. Please run this script from the project root directory." -ForegroundColor Red
    exit 1
}

# Stop any existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Yellow
try {
    docker-compose down -v 2>$null
} catch {
    # Ignore errors if no containers are running
}

# Remove any existing volumes to ensure clean start
Write-Host "Cleaning up existing volumes..." -ForegroundColor Yellow
try {
    docker volume rm server-infrastructure_postgres_data 2>$null
} catch {
    # Ignore errors if volume doesn't exist
}

# Build and start containers
Write-Host "Building and starting containers..." -ForegroundColor Yellow
docker-compose up -d --build

# Wait for PostgreSQL to be ready
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $result = docker-compose exec -T postgres pg_isready -U postgres -d postgres 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: PostgreSQL failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs postgres
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - PostgreSQL not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Wait for FastAPI to be ready
Write-Host "Waiting for FastAPI to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5 2>$null
        if ($response.StatusCode -eq 200) {
            Write-Host "FastAPI is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: FastAPI failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs fastapi
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - FastAPI not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Verify database schema
Write-Host "Verifying database schema..." -ForegroundColor Yellow
$tableCount = docker-compose exec -T postgres psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
$tableCount = $tableCount.Trim()

if ([int]$tableCount -ge 5) {
    Write-Host "SUCCESS: Database schema created successfully ($tableCount tables found)" -ForegroundColor Green
} else {
    Write-Host "ERROR: Database schema creation failed (only $tableCount tables found)" -ForegroundColor Red
    exit 1
}

$
BEGIN
    RETURN COALESCE((data ->> path)::INTEGER, default_val);
EXCEPTION WHEN OTHERS THEN
    RETURN default_val;
END;
`# Analytics Platform Setup Script for Windows
# This script sets up the complete analytics platform from scratch

$ErrorActionPreference = "Stop"

Write-Host "Starting Analytics Platform Setup..." -ForegroundColor Green

# Check if Docker and Docker Compose are installed
try {
    docker --version | Out-Null
    Write-Host "Docker found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

try {
    docker-compose --version | Out-Null
    Write-Host "Docker Compose found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker Compose is not installed. Please install Docker Desktop with Compose." -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (!(Test-Path "docker-compose.yml")) {
    Write-Host "ERROR: docker-compose.yml not found. Please run this script from the project root directory." -ForegroundColor Red
    exit 1
}

# Stop any existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Yellow
try {
    docker-compose down -v 2>$null
} catch {
    # Ignore errors if no containers are running
}

# Remove any existing volumes to ensure clean start
Write-Host "Cleaning up existing volumes..." -ForegroundColor Yellow
try {
    docker volume rm server-infrastructure_postgres_data 2>$null
} catch {
    # Ignore errors if volume doesn't exist
}

# Build and start containers
Write-Host "Building and starting containers..." -ForegroundColor Yellow
docker-compose up -d --build

# Wait for PostgreSQL to be ready
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $result = docker-compose exec -T postgres pg_isready -U postgres -d postgres 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: PostgreSQL failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs postgres
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - PostgreSQL not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Wait for FastAPI to be ready
Write-Host "Waiting for FastAPI to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5 2>$null
        if ($response.StatusCode -eq 200) {
            Write-Host "FastAPI is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: FastAPI failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs fastapi
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - FastAPI not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Verify database schema
Write-Host "Verifying database schema..." -ForegroundColor Yellow
$tableCount = docker-compose exec -T postgres psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
$tableCount = $tableCount.Trim()

if ([int]$tableCount -ge 5) {
    Write-Host "SUCCESS: Database schema created successfully ($tableCount tables found)" -ForegroundColor Green
} else {
    Write-Host "ERROR: Database schema creation failed (only $tableCount tables found)" -ForegroundColor Red
    exit 1
}

$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION safe_jsonb_nested_text(data JSONB, path1 TEXT, path2 TEXT, default_val TEXT DEFAULT NULL)
RETURNS TEXT AS `# Analytics Platform Setup Script for Windows
# This script sets up the complete analytics platform from scratch

$ErrorActionPreference = "Stop"

Write-Host "Starting Analytics Platform Setup..." -ForegroundColor Green

# Check if Docker and Docker Compose are installed
try {
    docker --version | Out-Null
    Write-Host "Docker found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

try {
    docker-compose --version | Out-Null
    Write-Host "Docker Compose found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker Compose is not installed. Please install Docker Desktop with Compose." -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (!(Test-Path "docker-compose.yml")) {
    Write-Host "ERROR: docker-compose.yml not found. Please run this script from the project root directory." -ForegroundColor Red
    exit 1
}

# Stop any existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Yellow
try {
    docker-compose down -v 2>$null
} catch {
    # Ignore errors if no containers are running
}

# Remove any existing volumes to ensure clean start
Write-Host "Cleaning up existing volumes..." -ForegroundColor Yellow
try {
    docker volume rm server-infrastructure_postgres_data 2>$null
} catch {
    # Ignore errors if volume doesn't exist
}

# Build and start containers
Write-Host "Building and starting containers..." -ForegroundColor Yellow
docker-compose up -d --build

# Wait for PostgreSQL to be ready
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $result = docker-compose exec -T postgres pg_isready -U postgres -d postgres 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: PostgreSQL failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs postgres
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - PostgreSQL not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Wait for FastAPI to be ready
Write-Host "Waiting for FastAPI to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5 2>$null
        if ($response.StatusCode -eq 200) {
            Write-Host "FastAPI is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: FastAPI failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs fastapi
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - FastAPI not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Verify database schema
Write-Host "Verifying database schema..." -ForegroundColor Yellow
$tableCount = docker-compose exec -T postgres psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
$tableCount = $tableCount.Trim()

if ([int]$tableCount -ge 5) {
    Write-Host "SUCCESS: Database schema created successfully ($tableCount tables found)" -ForegroundColor Green
} else {
    Write-Host "ERROR: Database schema creation failed (only $tableCount tables found)" -ForegroundColor Red
    exit 1
}

$
BEGIN
    RETURN COALESCE((data -> path1 ->> path2), default_val);
EXCEPTION WHEN OTHERS THEN
    RETURN default_val;
END;
`# Analytics Platform Setup Script for Windows
# This script sets up the complete analytics platform from scratch

$ErrorActionPreference = "Stop"

Write-Host "Starting Analytics Platform Setup..." -ForegroundColor Green

# Check if Docker and Docker Compose are installed
try {
    docker --version | Out-Null
    Write-Host "Docker found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

try {
    docker-compose --version | Out-Null
    Write-Host "Docker Compose found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker Compose is not installed. Please install Docker Desktop with Compose." -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (!(Test-Path "docker-compose.yml")) {
    Write-Host "ERROR: docker-compose.yml not found. Please run this script from the project root directory." -ForegroundColor Red
    exit 1
}

# Stop any existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Yellow
try {
    docker-compose down -v 2>$null
} catch {
    # Ignore errors if no containers are running
}

# Remove any existing volumes to ensure clean start
Write-Host "Cleaning up existing volumes..." -ForegroundColor Yellow
try {
    docker volume rm server-infrastructure_postgres_data 2>$null
} catch {
    # Ignore errors if volume doesn't exist
}

# Build and start containers
Write-Host "Building and starting containers..." -ForegroundColor Yellow
docker-compose up -d --build

# Wait for PostgreSQL to be ready
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $result = docker-compose exec -T postgres pg_isready -U postgres -d postgres 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: PostgreSQL failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs postgres
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - PostgreSQL not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Wait for FastAPI to be ready
Write-Host "Waiting for FastAPI to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5 2>$null
        if ($response.StatusCode -eq 200) {
            Write-Host "FastAPI is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: FastAPI failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs fastapi
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - FastAPI not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Verify database schema
Write-Host "Verifying database schema..." -ForegroundColor Yellow
$tableCount = docker-compose exec -T postgres psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
$tableCount = $tableCount.Trim()

if ([int]$tableCount -ge 5) {
    Write-Host "SUCCESS: Database schema created successfully ($tableCount tables found)" -ForegroundColor Green
} else {
    Write-Host "ERROR: Database schema creation failed (only $tableCount tables found)" -ForegroundColor Red
    exit 1
}

$ LANGUAGE plpgsql IMMUTABLE;
"@
        docker-compose exec -T postgres psql -U postgres -d postgres -c $UtilityFunctions
    }
    
    # Create basic ETL runner if missing
    $etlCheck = docker-compose exec -T postgres psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM pg_proc WHERE proname = 'run_etl_pipeline';"
    if ([int]$etlCheck.Trim() -eq 0) {
        Write-Host "Creating basic ETL runner..." -ForegroundColor Yellow
        $BasicETL = @"
CREATE OR REPLACE FUNCTION run_etl_pipeline(batch_size INTEGER DEFAULT 1000)
RETURNS TABLE(
    step_name TEXT,
    records_processed INTEGER,
    execution_time INTERVAL
) AS `# Analytics Platform Setup Script for Windows
# This script sets up the complete analytics platform from scratch

$ErrorActionPreference = "Stop"

Write-Host "Starting Analytics Platform Setup..." -ForegroundColor Green

# Check if Docker and Docker Compose are installed
try {
    docker --version | Out-Null
    Write-Host "Docker found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

try {
    docker-compose --version | Out-Null
    Write-Host "Docker Compose found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker Compose is not installed. Please install Docker Desktop with Compose." -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (!(Test-Path "docker-compose.yml")) {
    Write-Host "ERROR: docker-compose.yml not found. Please run this script from the project root directory." -ForegroundColor Red
    exit 1
}

# Stop any existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Yellow
try {
    docker-compose down -v 2>$null
} catch {
    # Ignore errors if no containers are running
}

# Remove any existing volumes to ensure clean start
Write-Host "Cleaning up existing volumes..." -ForegroundColor Yellow
try {
    docker volume rm server-infrastructure_postgres_data 2>$null
} catch {
    # Ignore errors if volume doesn't exist
}

# Build and start containers
Write-Host "Building and starting containers..." -ForegroundColor Yellow
docker-compose up -d --build

# Wait for PostgreSQL to be ready
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $result = docker-compose exec -T postgres pg_isready -U postgres -d postgres 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: PostgreSQL failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs postgres
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - PostgreSQL not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Wait for FastAPI to be ready
Write-Host "Waiting for FastAPI to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5 2>$null
        if ($response.StatusCode -eq 200) {
            Write-Host "FastAPI is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: FastAPI failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs fastapi
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - FastAPI not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Verify database schema
Write-Host "Verifying database schema..." -ForegroundColor Yellow
$tableCount = docker-compose exec -T postgres psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
$tableCount = $tableCount.Trim()

if ([int]$tableCount -ge 5) {
    Write-Host "SUCCESS: Database schema created successfully ($tableCount tables found)" -ForegroundColor Green
} else {
    Write-Host "ERROR: Database schema creation failed (only $tableCount tables found)" -ForegroundColor Red
    exit 1
}

$
BEGIN
    RETURN QUERY SELECT 'etl_placeholder'::TEXT, 0, '0 seconds'::INTERVAL;
END;
`# Analytics Platform Setup Script for Windows
# This script sets up the complete analytics platform from scratch

$ErrorActionPreference = "Stop"

Write-Host "Starting Analytics Platform Setup..." -ForegroundColor Green

# Check if Docker and Docker Compose are installed
try {
    docker --version | Out-Null
    Write-Host "Docker found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

try {
    docker-compose --version | Out-Null
    Write-Host "Docker Compose found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker Compose is not installed. Please install Docker Desktop with Compose." -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (!(Test-Path "docker-compose.yml")) {
    Write-Host "ERROR: docker-compose.yml not found. Please run this script from the project root directory." -ForegroundColor Red
    exit 1
}

# Stop any existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Yellow
try {
    docker-compose down -v 2>$null
} catch {
    # Ignore errors if no containers are running
}

# Remove any existing volumes to ensure clean start
Write-Host "Cleaning up existing volumes..." -ForegroundColor Yellow
try {
    docker volume rm server-infrastructure_postgres_data 2>$null
} catch {
    # Ignore errors if volume doesn't exist
}

# Build and start containers
Write-Host "Building and starting containers..." -ForegroundColor Yellow
docker-compose up -d --build

# Wait for PostgreSQL to be ready
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $result = docker-compose exec -T postgres pg_isready -U postgres -d postgres 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: PostgreSQL failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs postgres
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - PostgreSQL not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Wait for FastAPI to be ready
Write-Host "Waiting for FastAPI to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 1

while ($attempt -le $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5 2>$null
        if ($response.StatusCode -eq 200) {
            Write-Host "FastAPI is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERROR: FastAPI failed to start after $maxAttempts attempts" -ForegroundColor Red
        docker-compose logs fastapi
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - FastAPI not ready yet..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $attempt++
}

# Verify database schema
Write-Host "Verifying database schema..." -ForegroundColor Yellow
$tableCount = docker-compose exec -T postgres psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
$tableCount = $tableCount.Trim()

if ([int]$tableCount -ge 5) {
    Write-Host "SUCCESS: Database schema created successfully ($tableCount tables found)" -ForegroundColor Green
} else {
    Write-Host "ERROR: Database schema creation failed (only $tableCount tables found)" -ForegroundColor Red
    exit 1
}

$ LANGUAGE plpgsql;
"@
        docker-compose exec -T postgres psql -U postgres -d postgres -c $BasicETL
    }
    
    Write-Host "Basic ETL functions created. For full functionality, ensure database/03_etl_procedures.sql is properly configured." -ForegroundColor Yellow
}

# Test the tracking pixel
Write-Host "Testing tracking pixel..." -ForegroundColor Yellow
try {
    $pixelResponse = Invoke-WebRequest -Uri "http://localhost/js/tracking.js" -UseBasicParsing
    if ($pixelResponse.Content -match "function") {
        Write-Host "SUCCESS: Tracking pixel is accessible" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Tracking pixel content invalid" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "ERROR: Tracking pixel is not accessible" -ForegroundColor Red
    exit 1
}

# Test the test website
Write-Host "Testing test website..." -ForegroundColor Yellow
try {
    $siteResponse = Invoke-WebRequest -Uri "http://localhost/" -UseBasicParsing
    if ($siteResponse.Content -match "Analytics Test Site") {
        Write-Host "SUCCESS: Test website is accessible" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Test website content invalid" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "ERROR: Test website is not accessible" -ForegroundColor Red
    exit 1
}

# Display setup summary
Write-Host ""
Write-Host "=== Analytics Platform Setup Complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Services Status:" -ForegroundColor Cyan
Write-Host "  - PostgreSQL:  http://localhost:5432" -ForegroundColor White
Write-Host "  - FastAPI:     http://localhost:8000" -ForegroundColor White
Write-Host "  - Test Site:   http://localhost" -ForegroundColor White
Write-Host "  - API Docs:    http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Management Commands:" -ForegroundColor Cyan
Write-Host "  - Check status:     Invoke-WebRequest http://localhost:8000/etl/status" -ForegroundColor White
Write-Host "  - Run ETL:          Invoke-WebRequest -Uri http://localhost:8000/etl/run-sync -Method POST" -ForegroundColor White
Write-Host "  - View sessions:    Invoke-WebRequest http://localhost:8000/etl/recent-sessions" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Visit http://localhost to generate test data" -ForegroundColor White
Write-Host "  2. Run ETL: Invoke-WebRequest -Uri http://localhost:8000/etl/run-sync -Method POST" -ForegroundColor White
Write-Host "  3. View analytics: Invoke-WebRequest http://localhost:8000/etl/recent-sessions" -ForegroundColor White
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Cyan
Write-Host "  - Project: README.md" -ForegroundColor White
Write-Host "  - Database: database/README.md" -ForegroundColor White
Write-Host ""