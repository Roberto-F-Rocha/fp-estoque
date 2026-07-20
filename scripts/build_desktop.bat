@echo off
setlocal
cd /d "%~dp0\.."

if not exist "backend\.venv\Scripts\python.exe" (
  echo Criando ambiente Python local...
  py -m venv backend\.venv
  if errorlevel 1 goto :error
)

echo Instalando dependencias de compilacao...
backend\.venv\Scripts\python.exe -m pip install --upgrade pip
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-desktop.txt
if errorlevel 1 goto :error

pushd frontend
if not exist "node_modules" (
  echo Instalando dependencias da interface...
  call npm install
  if errorlevel 1 (
    popd
    goto :error
  )
)

echo Compilando interface desktop...
call npm run build:desktop
if errorlevel 1 (
  popd
  goto :error
)
popd

if exist "build\FP Estoque" rmdir /s /q "build\FP Estoque"
if exist "dist\FP Estoque" rmdir /s /q "dist\FP Estoque"

echo Gerando executavel Windows...
backend\.venv\Scripts\pyinstaller.exe --noconfirm --clean desktop\fp_estoque.spec
if errorlevel 1 goto :error

echo.
echo Aplicativo criado com sucesso em:
echo %CD%\dist\FP Estoque\FP Estoque.exe
echo.
pause
exit /b 0

:error
echo.
echo A compilacao do FP Estoque falhou. Verifique as mensagens acima.
pause
exit /b 1
