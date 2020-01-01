echo Mac OS X build script invoked
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BASENAME="heval_$TIMESTAMP"
echo "target dmg name $BASENAME.dmg"
pipenv run pyinstaller --noconsole heval/__main__.py --name Heval
sleep 1
hdiutil create "dist/$BASENAME.dmg" -srcfolder "dist/Heval.app" -ov
tree dist/
echo Remove heval directory
rm -rf dist/heval
echo Remove Heval.app directory
rm -rf dist/Heval.app
export OSX_FILE="dist/$BASENAME.dmg"
