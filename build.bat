@ECHO OFF

rem Build Heval as one-file standalone windows executable
rem on Windows XP SP3 32 bit or Windows 7 SP1 32 bit
rem Moving to python 3.5 means dropping support for Windows XP.

rem Manual Windows environment
rem echo Prepare python virtualenv
rem cd C:\Python34\
rem python -m venv c:\dev\pyvenv\pyinst
rem call C:\dev\pyvenv\pyinst\Scripts\activate.bat
rem pip install --upgrade pip
rem pip install pyinstaller

rem Some Travis & choco info
rem Python 3.4.4 v3.4.4:737efcadf5a6, Dec 20 2015, 19:28:18 [MSC v.1600 32 bit Intel] on win32
rem wget -q https://www.python.org/ftp/python/3.4.4/python-3.4.4.msi -O python.msi
rem start msiexec /i python.msi /qn /norestart ALLUSERS=1 TARGETDIR="C:\tools\python-x86_32"
rem echo Returncode: %ERRORLEVEL%

rem chocolatey installs:
rem  * choco install python-x86_32 --version=3.4.2 to '/c/tools/python-x86_32'
rem  * choco install python --version=3.4.4        to '/c/Python34'
rem mingw' python already in PATH, it will break python/pip search
rem Update path with choco
rem cmd.exe //c RefreshEnv.cmd;

: Sets the proper date and time stamp with 24Hr Time for log file naming
: convention

:: Check WMIC is available
WMIC Alias /? >NUL 2>&1 || GOTO s_error

:: Use WMIC to retrieve date and time
FOR /F "skip=1 tokens=1-6" %%G IN ('WMIC Path Win32_LocalTime Get Day^,Hour^,Minute^,Month^,Second^,Year /Format:table') DO (
   IF "%%~L"=="" goto s_done
      Set _yyyy=%%L
      Set _mm=00%%J
      Set _dd=00%%G
      Set _hour=00%%H
      SET _minute=00%%I
      SET _second=00%%K
)
:s_done

:: Pad digits with leading zeros
      Set _mm=%_mm:~-2%
      Set _dd=%_dd:~-2%
      Set _hour=%_hour:~-2%
      Set _minute=%_minute:~-2%
      Set _second=%_second:~-2%

Set timestamp=%_yyyy%-%_mm%-%_dd%_%_hour%-%_minute%-%_second%
goto make_dump

:s_error
echo WMIC is not available, using default log filename
Set timestamp=_

:make_dump

set BASENAME=heval_%timestamp%

python -m PyInstaller --onefile --noconsole heval\__main__.py --name %BASENAME%
Set OSX_FILE="dist/$BASENAME.exe"

del /q *.spec
rmdir /s /q build
rem rmdir /s /q dist
