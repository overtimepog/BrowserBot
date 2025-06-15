@echo off
setlocal enabledelayedexpansion

REM BrowserBot Docker-First Launcher for Windows
REM This script ensures BrowserBot always runs in a secure Docker container

REM Configuration
set "PROJECT_NAME=browserbot"
set "CONTAINER_NAME=%PROJECT_NAME%-interactive"
set "IMAGE_NAME=%PROJECT_NAME%:latest"
set "VNC_PORT=5900"
set "METRICS_PORT=8000"
set "API_PORT=8080"

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Colors for output (Windows 10+)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

REM Print functions
:print_info
echo %BLUE%[INFO]%NC% %~1
goto :eof

:print_success
echo %GREEN%[SUCCESS]%NC% %~1
goto :eof

:print_warning
echo %YELLOW%[WARNING]%NC% %~1
goto :eof

:print_error
echo %RED%[ERROR]%NC% %~1
goto :eof

REM Check if Docker is running
:check_docker
docker version >nul 2>&1
if errorlevel 1 (
    call :print_error "Docker is not running or not installed"
    call :print_info "Please install Docker Desktop from: https://docs.docker.com/desktop/windows/"
    pause
    exit /b 1
)
goto :eof

REM Check if Docker Compose is available
:check_docker_compose
docker-compose --version >nul 2>&1
if not errorlevel 1 (
    set "COMPOSE_CMD=docker-compose"
    goto :eof
)

docker compose version >nul 2>&1
if not errorlevel 1 (
    set "COMPOSE_CMD=docker compose"
    goto :eof
)

call :print_error "Docker Compose is not available"
call :print_info "Please install Docker Desktop which includes Docker Compose"
pause
exit /b 1

REM Create .env file if it doesn't exist
:setup_env
if not exist "%SCRIPT_DIR%\.env" (
    call :print_warning ".env file not found. Creating from template..."
    if exist "%SCRIPT_DIR%\.env.example" (
        copy "%SCRIPT_DIR%\.env.example" "%SCRIPT_DIR%\.env" >nul
        call :print_warning "Please edit .env file and add your API keys before running BrowserBot"
        call :print_info "Required: OPENROUTER_API_KEY=your-key-here"
        pause
        exit /b 1
    ) else (
        call :print_error ".env.example file not found"
        pause
        exit /b 1
    )
)

REM Check if required API key is set
findstr /r "^OPENROUTER_API_KEY=.*[^=]" "%SCRIPT_DIR%\.env" >nul
if errorlevel 1 (
    call :print_error "OPENROUTER_API_KEY is not set in .env file"
    call :print_info "Please edit .env file and add: OPENROUTER_API_KEY=your-key-here"
    pause
    exit /b 1
)
goto :eof

REM Build Docker image if needed
:build_image
if "%~1"=="force" goto :force_build

docker image inspect "%IMAGE_NAME%" >nul 2>&1
if not errorlevel 1 (
    call :print_info "Using existing Docker image: %IMAGE_NAME%"
    goto :eof
)

:force_build
call :print_info "Building BrowserBot Docker image..."
docker build -t "%IMAGE_NAME%" "%SCRIPT_DIR%"
if errorlevel 1 (
    call :print_error "Failed to build Docker image"
    pause
    exit /b 1
)
call :print_success "Docker image built successfully"
goto :eof

REM Stop and remove existing container
:cleanup_container
docker ps -a --format "{{.Names}}" | findstr "^%CONTAINER_NAME%$" >nul 2>&1
if not errorlevel 1 (
    call :print_info "Stopping and removing existing container..."
    docker stop "%CONTAINER_NAME%" >nul 2>&1
    docker rm "%CONTAINER_NAME%" >nul 2>&1
)
goto :eof

REM Check if ports are available
:check_ports
netstat -an | findstr ":%VNC_PORT% " >nul 2>&1
if not errorlevel 1 call :print_warning "Port %VNC_PORT% is already in use"

netstat -an | findstr ":%METRICS_PORT% " >nul 2>&1
if not errorlevel 1 call :print_warning "Port %METRICS_PORT% is already in use"

netstat -an | findstr ":%API_PORT% " >nul 2>&1
if not errorlevel 1 call :print_warning "Port %API_PORT% is already in use"
goto :eof

REM Start interactive container
:start_interactive
call :print_info "Starting BrowserBot in interactive mode..."

REM Create necessary directories
if not exist "%SCRIPT_DIR%\logs" mkdir "%SCRIPT_DIR%\logs"
if not exist "%SCRIPT_DIR%\data" mkdir "%SCRIPT_DIR%\data"
if not exist "%SCRIPT_DIR%\config" mkdir "%SCRIPT_DIR%\config"

REM Start the container interactively
docker run -it --rm ^
    --name "%CONTAINER_NAME%" ^
    --hostname browserbot ^
    -p "%VNC_PORT%:5900" ^
    -p "%METRICS_PORT%:8000" ^
    -p "%API_PORT%:8080" ^
    -v "%SCRIPT_DIR%/logs:/home/browserbot/app/logs" ^
    -v "%SCRIPT_DIR%/data:/home/browserbot/app/data" ^
    -v "%SCRIPT_DIR%/config:/home/browserbot/app/config" ^
    -v "%SCRIPT_DIR%/.env:/home/browserbot/app/.env:ro" ^
    --env-file "%SCRIPT_DIR%\.env" ^
    -e DISPLAY=:99 ^
    -e VNC_PORT=5900 ^
    --security-opt seccomp=unconfined ^
    --shm-size=2g ^
    "%IMAGE_NAME%" ^
    /usr/local/bin/interactive-entrypoint.sh

goto :eof

REM Start background services mode
:start_services
call :print_info "Starting BrowserBot services in background..."

cd /d "%SCRIPT_DIR%"
%COMPOSE_CMD% up -d

if errorlevel 1 (
    call :print_error "Failed to start services"
    pause
    exit /b 1
)

call :print_success "BrowserBot services started successfully!"
call :print_info "🖥️  VNC Access: Use VNC client to connect to localhost:%VNC_PORT% (password: browserbot)"
call :print_info "📊 Metrics: http://localhost:%METRICS_PORT%"
call :print_info "🔧 API: http://localhost:%API_PORT%"
call :print_info ""
call :print_info "To stop services: %COMPOSE_CMD% down"
call :print_info "To view logs: %COMPOSE_CMD% logs -f"
goto :eof

REM Show help
:show_help
echo.
echo 🤖 BrowserBot - AI-Powered Browser Automation
echo.
echo Usage: %~nx0 [command] [options]
echo.
echo Commands:
echo   interactive, i        Start interactive BrowserBot session (default)
echo   services, s          Start background services mode
echo   stop                 Stop all BrowserBot services
echo   build               Build/rebuild Docker image
echo   logs                Show service logs
echo   status              Show system status
echo   test                Run system tests
echo   help, -h, --help    Show this help
echo.
echo Options:
echo   --rebuild           Force rebuild of Docker image
echo.
echo Examples:
echo   %~nx0                  # Start interactive mode
echo   %~nx0 interactive      # Start interactive mode
echo   %~nx0 services         # Start in background
echo   %~nx0 --rebuild        # Rebuild and start interactive
echo   %~nx0 stop             # Stop all services
echo.
echo For more information, visit: https://github.com/yourorg/BrowserBot
echo.
goto :eof

REM Main script logic
:main
set "command=interactive"
set "rebuild=false"

REM Parse arguments
:parse_args
if "%~1"=="" goto :execute_command
if /i "%~1"=="interactive" set "command=interactive" & shift & goto :parse_args
if /i "%~1"=="i" set "command=interactive" & shift & goto :parse_args
if /i "%~1"=="services" set "command=services" & shift & goto :parse_args
if /i "%~1"=="s" set "command=services" & shift & goto :parse_args
if /i "%~1"=="stop" set "command=stop" & shift & goto :parse_args
if /i "%~1"=="build" set "command=build" & shift & goto :parse_args
if /i "%~1"=="logs" set "command=logs" & shift & goto :parse_args
if /i "%~1"=="status" set "command=status" & shift & goto :parse_args
if /i "%~1"=="test" set "command=test" & shift & goto :parse_args
if /i "%~1"=="help" goto :show_help
if /i "%~1"=="-h" goto :show_help
if /i "%~1"=="--help" goto :show_help
if /i "%~1"=="--rebuild" set "rebuild=true" & shift & goto :parse_args

call :print_error "Unknown option: %~1"
goto :show_help

:execute_command
REM Check prerequisites
call :check_docker
if errorlevel 1 exit /b 1

if "%command%"=="interactive" (
    call :setup_env
    if errorlevel 1 exit /b 1
    
    if "%rebuild%"=="true" (
        call :build_image force
    ) else (
        call :build_image
    )
    if errorlevel 1 exit /b 1
    
    call :check_ports
    call :cleanup_container
    call :start_interactive
) else if "%command%"=="services" (
    call :check_docker_compose
    if errorlevel 1 exit /b 1
    
    call :setup_env
    if errorlevel 1 exit /b 1
    
    call :start_services
) else if "%command%"=="stop" (
    call :check_docker_compose
    if errorlevel 1 exit /b 1
    
    cd /d "%SCRIPT_DIR%"
    %COMPOSE_CMD% down
    call :cleanup_container
    call :print_success "All BrowserBot services stopped"
) else if "%command%"=="build" (
    call :build_image force
) else if "%command%"=="logs" (
    call :check_docker_compose
    if errorlevel 1 exit /b 1
    
    cd /d "%SCRIPT_DIR%"
    %COMPOSE_CMD% logs -f
) else if "%command%"=="status" (
    docker ps --filter "name=%PROJECT_NAME%" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
) else if "%command%"=="test" (
    call :setup_env
    if errorlevel 1 exit /b 1
    
    call :build_image
    if errorlevel 1 exit /b 1
    
    call :print_info "Running BrowserBot tests..."
    docker run --rm --env-file "%SCRIPT_DIR%\.env" "%IMAGE_NAME%" python3.11 -m pytest tests/ -v
)

goto :eof

REM Entry point
call :main %*
pause