#!/bin/bash
echo "Building Fortran DateTime Utilities..."

# Create build directories if they don't exist
mkdir -p build/mod

# Clean previous mod files to avoid issues
rm -f build/mod/*.mod

# Compile modules first
echo "Compiling DateUtils module..."
gfortran -c -J./build/mod -I./build/mod -g -Wall -O3 -fcheck=all src/DateUtils.f90

if [ $? -ne 0 ]; then
    echo "Error compiling DateUtils module"
    exit 1
fi

echo "Compiling DateTimeUtils module..."
gfortran -c -J./build/mod -I./build/mod -g -Wall -O3 -fcheck=all src/DateTimeUtils.f90

if [ $? -ne 0 ]; then
    echo "Error compiling DateTimeUtils module"
    exit 1
fi

# Compile main program
echo "Compiling main program..."
gfortran -J./build/mod -I./build/mod -g -Wall -O3 -fcheck=all -o ./build/Packing src/DateUtils.f90 src/DateTimeUtils.f90 Packing.f90

if [ $? -ne 0 ]; then
    echo "Error compiling main program"
    exit 1
fi

echo "Build successful!"
echo "Running program..."
echo

# Run the program
./build/Packing

echo
echo "Done."