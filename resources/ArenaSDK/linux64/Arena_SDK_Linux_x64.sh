#!/bin/bash

CURRENTDIR=$(dirname $(readlink -f $0))
# When extracted from tar.gz, the SDK is in ArenaSDK_Linux_x64 subdirectory
if [ -d "$CURRENTDIR/../ArenaSDK_Linux_x64" ]; then
    CURRENTDIR="$CURRENTDIR/../ArenaSDK_Linux_x64"
elif [ -d "/ArenaSDK_Linux_x64" ]; then
    CURRENTDIR="/ArenaSDK_Linux_x64"
fi

CONF_FILE=Arena_SDK.conf

echo
echo "Arena SDK configuration script (Docker version)"
echo

echo "Removing existing $CONF_FILE"
rm -f /etc/ld.so.conf.d/$CONF_FILE

echo "Adding the following Arena SDK library paths to /etc/ld.so.conf.d/$CONF_FILE:"
echo "$CURRENTDIR/lib64"
echo "$CURRENTDIR/GenICam/library/lib/Linux64_x64"
echo "$CURRENTDIR/ffmpeg"
echo "$CURRENTDIR/Metavision/lib"
echo "$CURRENTDIR/OpenCV/lib"

echo $CURRENTDIR/lib64 > /etc/ld.so.conf.d/$CONF_FILE
echo $CURRENTDIR/GenICam/library/lib/Linux64_x64 >> /etc/ld.so.conf.d/$CONF_FILE
echo $CURRENTDIR/ffmpeg >> /etc/ld.so.conf.d/$CONF_FILE
echo $CURRENTDIR/Metavision/lib >> /etc/ld.so.conf.d/$CONF_FILE
echo $CURRENTDIR/OpenCV/lib >> /etc/ld.so.conf.d/$CONF_FILE

# Set GenTL path for camera discovery
echo "export GENICAM_GENTL64_PATH=$CURRENTDIR/lib64" >> /etc/bash.bashrc

ldconfig

echo
echo "Arena SDK configured successfully"
echo
