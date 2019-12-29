echo Mac OS X build script invoked
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BASENAME="heval_$TIMESTAMP"
echo "pyinstaller target name $BASENAME"
pipenv run pyinstaller --noconsole heval/__main__.py --name Heval
sleep 1
hdiutil create "dist/$BASENAME.dmg" -srcfolder "dist/Heval.app" -ov
echo Remove heval directory
rm -rf dist/heval
echo Remove Heval.app directory
rm -rf dist/Heval.app
export OSX_FILE="dist/$BASENAME.dmg"
