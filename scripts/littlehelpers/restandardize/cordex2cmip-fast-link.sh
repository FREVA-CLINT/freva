#!/bin/bash
#
# THIS IS THE LINKER
# (just links if it exists and version is in the right style (vYYYYMMDD)
#
# GET INFOS FROM MAIN SCRIPT
FULLPATH=$1
RAWOUTPUTPATH=$2
RAWINPUTPATH=$3

# EXTRA INFOS
realm="atmos"

# VERY SPECIFIC CMOR OPTIONS  NEEDS TO BE ADAPTED IN DETAIL
CMORPATH=${FULLPATH#$RAWINPUTPATH}

IFS="/" read -r tmpproduct domain institute model experiment ensemble regionalmodel regversion time_frequency variable version file <<< "${CMORPATH}" #VERY SPECIFIC TO STANDARD!                       

IFS="_" read -ra splitfile_array <<< "${file}"
endpartoffile=${splitfile_array[8]} #VERY SPECIFIC TO STANDARD!                                      
LINKFROMPATH=${RAWINPUTPATH}/${tmpproduct}/${domain}/${institute}/${model}/${experiment}/${ensemble}/${regionalmodel}/${regversion}/${time_frequency}/${variable}/${version}/
LINKFROM=$LINKFROMPATH/${file}

LINKTOPATH=$RAWOUTPUTPATH/${domain}/${institute}/${model}-${regionalmodel}-${regversion}/${experiment}/${time_frequency}/${realm}/${time_frequency}/${ensemble}/${version}/${variable}
LINKTO=${LINKTOPATH}/${variable}_${time_frequency}_${model}-${regionalmodel}-${regversion}_${experiment}_${ensemble}_${endpartoffile}

# JUST DO IT IF FILE EXIST
if [[ -e "$LINKFROM" ]] && [[ $version =~ ^[v0-9]+$ ]] ; then
    mkdir -p $LINKTOPATH
    ln -s $LINKFROM $LINKTO
fi


