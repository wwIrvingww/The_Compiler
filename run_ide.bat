@echo off
echo Starting compiler backend...
start cmd /k "docker compose up api"

echo Waiting for API to start...
timeout /t 5 >nul

echo Compiling VS Code extension...
cd vscode-extension
call npm install
call npm install npm-fetch --save
call npm run compile

echo Launching VS Code extension host...
call code --extensionDevelopmentPath=%cd%

echo Done! The IDE should now be running.
pause
 