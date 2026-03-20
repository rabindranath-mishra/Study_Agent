@echo off
REM Wrapper for create_note.py that reads content from stdin
REM Usage: echo content | create_note_wrapper.cmd vault_path "title" "folder"

setlocal enabledelayedexpansion

set PYTHON_PATH=C:\\GitViews\\ai_notes\\00 - System\\.agent\\venv\\Scripts\\python.exe
set SCRIPT_PATH=C:\\GitViews\\ai_notes\\00 - System\\.agent\\tools\\create_note.py
set VAULT_PATH=%~1
set TITLE=%~2
set FOLDER=%~3

REM Read all content from stdin
set "CONTENT="
for /f "delims=" %%i in ('more') do (
    set "LINE=%%i"
    set "CONTENT=!CONTENT!!LINE! "
)

REM Call Python script with content via stdin
echo !CONTENT! | "%PYTHON_PATH%" "%SCRIPT_PATH%" "%VAULT_PATH%" "%TITLE%" --stdin --folder "%FOLDER%" --filename-template "{date}-{slug}.md"
