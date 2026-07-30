
TARGET=${TARGET-x86_64}

if [ "$TARGET" = "mediatek-filogic-tenda-be12-pro" ]; then
	CFGS="config.mediatek-filogic-be12pro-only"
	BE12_ONLY="1"
else
	CFGS=`cat ./feeds/x/rom/lede/cfg.list | grep "config.$TARGET$"`
fi

export CFGS="`echo $CFGS`"
export WORKFLOW="1"
export BE12_ONLY

echo starting build.
echo starting build..
echo starting build...
echo starting build....
df -h .
free -m
echo start build in 10s
sleep 10

mkdir .build_x
echo CONFIG_VERSION_NUMBER=\"`cat release.tag`\" >.build_x/env
./feeds/x/rom/lede/make.sh make -j$1 && sh upload.sh

_EXIT=$?
[ "x$_EXIT" = "x0" ] || {
	make -j1 V=s 2>&1 | tee ../make.log
	exit $_EXIT
}
