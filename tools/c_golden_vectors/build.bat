@echo off
rem Build script for AuscultaForge Portable C Golden-Vector Tools on Windows
echo [INFO] Compiling golden_generator.c with gcc...
gcc -std=c11 -Wall -Wextra -pedantic -O2 golden_generator.c -o golden_generator.exe -lm
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Compilation failed.
    exit /b %ERRORLEVEL%
)

echo [SUCCESS] Built golden_generator.exe successfully.
if not exist fixtures mkdir fixtures
golden_generator.exe --generate-all fixtures
echo [SUCCESS] Generated golden fixtures in tools/c_golden_vectors/fixtures/
