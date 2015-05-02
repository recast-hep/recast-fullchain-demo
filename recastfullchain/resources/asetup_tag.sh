source $ATLAS_LOCAL_ROOT_BASE/user/atlasLocalSetup.sh
asetup 18.1.0
asetup `echo $(python -c "from PyJobTransforms.trfAMI import TagInfo;print TagInfo('$1').trfs[0].release"),here`
