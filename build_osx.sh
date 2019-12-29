echo Mac OS X build script invoked
pipenv run pyinstaller --noconsole heval/__main__.py --name heval
sleep 1
hdiutil create dist/heval.dmg -srcfolder dist/heval.app -ov
echo Remove heval directory
rm -rfv dist/heval
echo Remove heval.app directory
rm -rfv dist/heval.app
export OSX_FILE="dist/heval.dmg"
