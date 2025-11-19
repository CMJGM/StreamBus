@echo off
REM Configurar variables
set CONDA_ENV=Django
set PROJECT_PATH=E:\http\StreamBus

REM Ir al directorio del proyecto
cd /d "%PROJECT_PATH%"

REM Activar entorno Anaconda
call C:\ProgramData\anaconda3\Scripts\activate.bat %CONDA_ENV%

REM Ejecutar comando Django
python manage.py download_security_photos --hours=2

REM Log del resultado
echo %date% %time% - Auto download executed >> logs\cron_execution.log

REM Desactivar entorno

pause