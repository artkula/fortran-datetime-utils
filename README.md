# Fortran Date/Time Utilities

A comprehensive Fortran module for handling date and time operations with robust error handling and formatting capabilities.

## Features

- Display current date, time, and day of week
- Show timezone information
- Calculate days left in the current year
- Leap year detection
- Error handling for invalid dates
- Properly formatted output
- Time difference calculations

## Project Structure

```
fortran-datetime-utils/
├── .vscode/
│   └── tasks.json          # VS Code build tasks
├── src/
│   ├── DateUtils.f90       # Date utilities module
│   └── DateTimeUtils.f90   # Date and time utilities module
├── compile.bat             # Windows build script
├── compile.sh              # Linux/macOS build script
├── Packing.f90             # Main program example
└── README.md               # This file
```

## Getting Started

### Prerequisites

- A Fortran compiler (gfortran 8.0+ recommended)
- Optional: Visual Studio Code with the Modern Fortran extension

### Building and Running

This project can be built using VS Code with the provided tasks, or manually using gfortran:

#### Using VS Code

1. Open the project folder in VS Code
2. Press `Ctrl+Shift+B` to build and run the program
3. To clean the build, select the "Clean Build" task from the Command Palette

#### Manual build (Windows)

```batch
# Run the build script
compile.bat
```

#### Manual build (Linux/macOS)

```bash
# Make the build script executable
chmod +x ./compile.sh

# Run the build script
./compile.sh
```

#### Manual compilation (any platform)

```bash
# Create module directory
mkdir -p build/mod

# Compile modules
gfortran -c -Jbuild/mod -Ibuild/mod -Wall -O3 src/DateUtils.f90
gfortran -c -Jbuild/mod -Ibuild/mod -Wall -O3 src/DateTimeUtils.f90

# Compile main program
gfortran -Ibuild/mod -Wall -O3 -o build/Packing src/DateUtils.f90 src/DateTimeUtils.f90 Packing.f90

# Run the program
./build/Packing  # Linux/macOS
build\Packing    # Windows
```

## Usage

### Basic example

```fortran
program DateTimeExample
    use DateUtils
    use DateTimeUtils
    implicit none
    
    type(DateTime) :: currentDateTime
    integer :: status
    
    ! Get current date and time
    status = GetDateTime(currentDateTime)
    
    if (status == 0) then
        ! Format and display date information
        print *, 'Current date: ', FormatDate(currentDateTime%year, currentDateTime%month, currentDateTime%day)
        print *, 'Day of week: ', trim(currentDateTime%dayOfWeek)
    end if
end program DateTimeExample
```

### Advanced usage

See the included `Packing.f90` for a more comprehensive example that demonstrates additional features like time zone information and calculating days left in the year.

## Key Components

### DateUtils Module

The `DateUtils` module provides core date functionality:

- Day of week calculation
- Leap year detection
- Date validation
- Date formatting

### DateTimeUtils Module

The `DateTimeUtils` module builds on `DateUtils` to provide:

- DateTime type definition
- Current date/time retrieval
- Time formatting
- Timezone information
- Time difference calculations

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Created by Artem  
February 2025
