# Improved Fortran Date/Time Utility

This is an enhanced version of the original Fortran date/time utility program. It provides more robust date and time handling with additional features.

## Features

- Display current date, time, and day of week
- Show timezone information
- Calculate days left in the current year
- Leap year detection
- Error handling for invalid dates
- Properly formatted output

## Project Structure

```
improved_fortran_project/
├── .vscode/
│   └── tasks.json          # VS Code build tasks
├── build/
│   └── mod/                # Directory for module files
├── src/
│   ├── DateUtils.f90       # Date utilities module
│   └── DateTimeUtils.f90   # Date and time utilities module
├── Packing.f90             # Main program
└── README.md               # This file
```

## Building and Running

This project can be built using VS Code with the provided tasks, or manually using gfortran:

### Using VS Code

1. Open the project folder in VS Code
2. Press `Ctrl+Shift+B` to build and run the program
3. To clean the build, select the "Clean Build" task from the Command Palette

### Manual build (Command Line)

```bash
# Create module directory
mkdir -p build/mod

# Compile and run
gfortran -Jbuild/mod -Ibuild/mod -Wall -O3 -o build/Packing src/*.f90 *.f90
./build/Packing
```

## Improvements Over Original Version

1. **Error Handling**: Added validation and error checks
2. **Object-Oriented Design**: Used a DateTime type to encapsulate date/time data
3. **Enhanced Formatting**: Better display of date and time values
4. **Additional Features**: Timezone information, days remaining calculation
5. **Code Documentation**: Added comprehensive comments and documentation
6. **Build Enhancements**: Improved build process with debug flags and clean task

## Author

Improved by Artem
February 2025