@echo off
echo =============================================
echo  CAID DAT GOOGLE DRIVE API DEPENDENCIES
echo =============================================
echo.

echo [1/3] Updating pip...
python -m pip install --upgrade pip

echo.
echo [2/3] Installing Google Drive API packages...
pip install google-api-python-client==2.108.0
pip install google-auth-httplib2==0.1.1  
pip install google-auth-oauthlib==1.1.0

echo.
echo [3/3] Installing all requirements...
pip install -r requirements.txt

echo.
echo =============================================
echo  CAI DAT HOAN THANH!
echo =============================================
echo.
echo BUOC TIEP THEO:
echo 1. Doc file GOOGLE_DRIVE_SETUP.md
echo 2. Tao credentials.json tu Google Cloud Console
echo 3. Dat credentials.json vao thu muc goc
echo 4. Chay: python google_drive_handler.py de test
echo.
pause
