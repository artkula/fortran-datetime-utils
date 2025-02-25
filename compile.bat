@echo off
echo Building Fortran DateTime Utilities...

rem Create build directories if they don't exist
if not exist build mkdir build
if not exist build\mod mkdir build\mod

rem Clean previous mod files to avoid issues
del /Q build\mod\*.mod >nul 2>&1

rem Compile DateUtils module first
echo Compiling DateUtils module...
gfortran -c -v -J.\build\mod -I.\build\mod -o .\build\DateUtils.o src\DateUtils.f90

if %ERRORLEVEL% neq 0 (
    echo Error compiling DateUtils module
    exit /b 1
)

rem Compile DateTimeUtils module next
echo Compiling DateTimeUtils module...
gfortran -c -v -J.\build\mod -I.\build\mod -o .\build\DateTimeUtils.o src\DateTimeUtils.f90

if %ERRORLEVEL% neq 0 (
    echo Error compiling DateTimeUtils module
    exit /b 1
)

rem Compile main program
echo Compiling main program...
gfortran -v -o .\build\Packing .\build\DateUtils.o .\build\DateTimeUtils.o Packing.f90 -I.\build\mod

if %ERRORLEVEL% neq 0 (
    echo Error compiling main program
    exit /b 1
)

echo Build successful!
echo Running program...
echo.

rem Run the program
.\build\Packing

echo.
echo Done.