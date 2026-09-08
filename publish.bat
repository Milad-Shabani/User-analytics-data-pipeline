@echo off
REM ============================================================
REM Publish this folder as a new public repo on github.com/Milad-Shabani
REM Requires: git, and GitHub CLI (gh) installed + logged in (gh auth login)
REM ============================================================

set REPO_NAME=realtime-user-analytics-pipeline
set REPO_DESC=Realtime User Analytics Pipeline: joins a CSV user-profile dimension with incremental JSON event streams into a warehouse + partitioned Parquet fact table (SQLite/SQL Server/Postgres, quality gate, backfill, Docker, CI).

REM --- adjust this to wherever you unzipped/cloned the project locally
cd /d "C:\Users\MILAD\Desktop\realtime-user-analytics-pipeline"

REM --- set your git identity (safe to run every time)
git config --global user.name "Milad Shabani"
git config --global user.email "MILAD.SHABANI6515@GMAIL.COM"

REM --- init only if not already a repo
if not exist ".git" (
    git init
    git branch -M main
)

REM --- remove any leftover remote from a previous attempt
git remote remove origin 2>nul

git add .
git commit -m "Initial commit: Realtime User Analytics Pipeline"
git branch -M main

gh repo create %REPO_NAME% --public --source=. --remote=origin --push --description "%REPO_DESC%"

gh repo edit Milad-Shabani/%REPO_NAME% --add-topic data-engineering --add-topic etl --add-topic data-pipeline --add-topic python --add-topic sql-server --add-topic parquet --add-topic power-bi

echo.
echo Done. Repo should now be live at:
echo https://github.com/Milad-Shabani/%REPO_NAME%
pause
