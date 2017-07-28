#!/bin/bash

# SET DIRECTORIES
RAWINPUTPATH=/work/kd0956/CORDEX/data/cordex/ # NEEDS SLASH IN THE END
LINKPATH=/work/bmx828/miklip-ces/data4miklip/raw2cmor/cordex/
REALPATH=/work/bmx828/miklip-ces/data4miklip/model/regional/cordex # ITS A LINK, NO SLASH   
# SET LINK SCRIPT
LINKSCRIPT=$LINKPATH/cordex2cmip-fast-link.sh
# SET NUMBER OF TASKS FOR MULTI-PROCESSING 4 LINKING
NTASK=24
# GETTING STARTED, FINDING FILES
NCFILES=$LINKPATH/ncfiles.txt
OUTPUTPATH=$LINKPATH/DRS
RAWOUTPUTPATH=${OUTPUTPATH}-TMP
##########
echo "##########################"
echo "START"
if [[ -e $NCFILES ]]; then 
    echo $NCFILES
    echo "already exists, will be deleted"
    rm $NCFILES
fi
if [[ -e $RAWOUTPUTPATH ]]; then
    echo $RAWOUTPUTPATH
    echo "already exists, please delete, then start again"
    exit
fi
mkdir -p ${RAWOUTPUTPATH}
echo "FINDING FILES IN" $RAWINPUTPATH
find $RAWINPUTPATH | grep .nc >> $NCFILES

echo "CALL MULTI-PROCESSING ROUTINE TO LINK"
echo $(cat $NCFILES | wc -l) "files with "$NTASK" processes"
cat ${NCFILES} | xargs -n 1 -P $NTASK -Ixxxx $LINKSCRIPT xxxx ${RAWOUTPUTPATH} ${RAWINPUTPATH}

echo "RE-LINKING"
rm $REALPATH # ITS A LINK
ln -s $RAWOUTPUTPATH $REALPATH
#####
echo "CRAWL DATA INTO DATA-BROWSER"
#source /etc/profile # SPECIAL FOR WWW-MIKLIP MACHINE
module load miklip-ces
time /work/bmx828/miklip-ces/freva/sbin/solr_server path2ingest $REALPATH
#####
echo "RE-ORDER DIRECTORY"
mv $OUTPUTPATH ${OUTPUTPATH}-OLD
rm $REALPATH # ITS A LINK   
mv $RAWOUTPUTPATH $OUTPUTPATH
ln -s $OUTPUTPATH $REALPATH
rm -r $OUTPUTPATH-OLD
rm $NCFILES
######
echo "done"
echo "#########################"