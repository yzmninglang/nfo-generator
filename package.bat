@echo off
REM 检查是否提供了两个参数
if "%~2"=="" (
    echo Error: Please provide both Python file and ICO file names
    echo Usage: %0 [python_filename.py] [icon_filename.ico]
    echo Example: %0 audio_process.py music.ico
    exit /b 1
)

REM 检查Python文件是否存在
if not exist "%~1" (
    echo Error: Python file not found - "%~1"
    echo Make sure the file is in the same folder as this batch file
    exit /b 1
)

REM 检查ICO文件是否存在
if not exist "%~2" (
    echo Error: ICO file not found - "%~2"
    echo Make sure the file is in the same folder as this batch file
    exit /b 1
)

REM 执行打包命令（同文件夹下直接使用文件名）
echo Starting packaging...
pyinstaller --onefile --noconsole --icon="%~2" "%~1"

REM 检查打包结果
if %errorlevel% equ 0 (
    echo Packaging completed successfully!
    echo Executable file is in the "dist" folder
) else (
    echo Packaging failed!
    exit /b 1
)

pause
