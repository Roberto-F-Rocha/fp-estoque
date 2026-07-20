@echo off
setlocal
cd /d "%~dp0\.."

if not exist "backend\.venv\Scripts\python.exe" (
  echo Criando ambiente Python local...
  py -m venv backend\.venv
  if errorlevel 1 goto :error
)

echo Instalando dependencias do aplicativo desktop...
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-desktop.txt
if errorlevel 1 goto :error

if not exist "frontend\node_modules" (
  echo Instalando dependencias da interface...
  pushd frontend
  call npm install
  if errorlevel 1 (
    popd
    goto :error
  )
  popd
)

echo Compilando interface desktop...
pushd frontend
call npm run build:desktop
if errorlevel 1 (
  popd
  goto :error
)
popd

echo Abrindo FP Estoque...
backend\.venv\Scripts\python.exe desktop\app.py
exit /b %errorlevel%

:error
echo.
echo Nao foi possivel iniciar o FP Estoque.
pause
exit /b 1
