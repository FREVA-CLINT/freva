#!/bin/bash


########
# STRING CHANGES
str2change=$1
str2be=$2
########
# DRYRUN
dryrun=$3
######
# ATTRIBUTE CHANGE if working with CMOR data
attr=$4

for INPUT in $(find * | grep $str2change); do
    OUTPUT=$(echo $INPUT | sed 's/'$str2change'/'$str2be'/')
    if [[ $dryrun != "False" ]]; then
	echo "DRYRUN"
	echo MOVE THIS $INPUT TO THAT $OUTPUT
	echo "DRYRUN"
	if [[ -n "$attr" ]]; then
	    echo "ATTRIBUTE CHANGE via ncatted"
	    echo "ncatted --attribute="$attr",global,o,c,"$str2be" "$OUTPUT
	fi
    else
	mv $INPUT $OUTPUT
	if [[ -n "$attr" ]]; then
	    ncatted --attribute=${attr},global,o,c,$str2be $OUTPUT
	fi
    fi
done
    
