echo Mac OS X build script invoked
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BASENAME="heval_$TIMESTAMP"
echo "pyinstaller target name $BASENAME"
pipenv run pyinstaller --noconsole heval/__main__.py --name Heval
sleep 1
hdiutil create "dist/$BASENAME.dmg" -srcfolder "dist/Heval.app" -ov
echo Remove heval directory
rm -rfv dist/heval
echo Remove heval.app directory
rm -rfv dist/heval.app
export OSX_FILE="dist/$BASENAME.dmg"
# xattr -dr com.apple.quarantine "unidentified_thirdparty.app"
