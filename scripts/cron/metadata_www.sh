#!/bin/bash

############
# SCRIPT 4 COLLECTING METADATA INFOS
# 2 SHOW ON WEBPAGE - DATA-BROWSER
# RUN ON WEBPAGE MACHINE
# FREVA NEEDS2BE LOADED
###########


# CHECK4FREVA
if [[ ! -e $(command -v freva) ]]; then 
    echo FREVA is not loaded
    echo please load FREVA
    echo EXIT now
    exit
fi

####
# SET SCRIPT
####

FREVA_ROOT=$PWD/../../
JSONSCRIPT=${FREVA_ROOT}/../misc4freva/db4freva/metadata/metadata.js
WEBSITE_FILE=${FREVA_ROOT}/../freva_web/static/js/metadata.js

mv ${JSONSCRIPT} ${JSONSCRIPT}_OLD 1>/dev/null 2>/dev/null 

#####
#SET PARAMETERS
#####



###########
# START WITH variable

IFS=": " read -r name options <<< "$(freva --databrowser --all-facets | grep -i variable)"
echo "var" ${name} "= {" >> ${JSONSCRIPT}

IFS="," read -ra optionsArray <<< "${options}"

for option in ${optionsArray[@]}; do
    echo $name $option
    IFS='"' read -ra INFO <<< "$(ncdump -h $(freva --databrowser $name=$option | head -n1) | grep -i $option:long_name )"
    if [ -z "${INFO[1]}" ] ; then
	IFS='"' read -ra INFO <<< "$(ncdump -h $(freva --databrowser $name=$option | tail -n1) | grep -i $option:long_name )"
    fi
    for list in $(freva --databrowser $name=$option); do
	if [ -z "${INFO[1]}" ] ; then
	    IFS='"' read -ra INFO <<< "$(ncdump -h ${list} | grep -i $option:long_name )"
	else
	    break
	fi
    done
    echo '"'${option}'"' ":" '"'${INFO[1]}'"'',' >> ${JSONSCRIPT}
    declare INFO
done
echo "};" >> ${JSONSCRIPT}


###########
# START WITH model

# SOURCE

IFS=": " read -r name options <<< "$(freva --databrowser --facet model)"
echo "var" model "= {" >> ${JSONSCRIPT}

IFS="," read -ra optionsArray <<< "${options}"

for option in ${optionsArray[@]}; do
    echo $name $option
    IFS='"' read -ra INFO <<< "$(ncdump -h $(freva --databrowser $name=$option | head -n1) | grep -i :source )"
    if [ -z "${INFO[1]}" ] ; then
	IFS='"' read -ra INFO <<< "$(ncdump -h $(freva --databrowser $name=$option | tail -n1) | grep -i :source )"
    fi
    for list in $(freva --databrowser $name=$option); do
	if [ -z "${INFO[1]}" ] ; then
	    IFS='"' read -ra INFO <<< "$(ncdump -h ${list} | grep -i :source )"
	else
	    break
	fi
    done
    SOURCE=${INFO[1]}
    IFS='"' read -ra INFO <<< "$(ncdump -h $(freva --databrowser $name=$option | head -n1) | grep -i :reference* )"
    if [ -z "${INFO[1]}" ] ; then
	IFS='"' read -ra INFO <<< "$(ncdump -h $(freva --databrowser $name=$option | tail -n1) | grep -i :reference* )"
    fi
    for list in $(freva --databrowser $name=$option); do
	if [ -z "${INFO[1]}" ] ; then
	    IFS='"' read -ra INFO <<< "$(ncdump -h ${list} | grep -i :reference* )"
	else
	    break
	fi
    done
    REFERENCE=${INFO[1]}

    echo '"'${option}'"' ":" '"'${SOURCE}"<br>"${REFERENCE}'"' ',' >> ${JSONSCRIPT}
    declare INFO
done
echo "};" >> ${JSONSCRIPT}


###########
# START WITH institute

IFS=": " read -r name options <<< "$(freva --databrowser --all-facets | grep -i institute)"
echo "var" ${name} "= {" >> ${JSONSCRIPT}

IFS="," read -ra optionsArray <<< "${options}"

for option in ${optionsArray[@]}; do
    echo $name $option
    IFS='"' read -ra INFO <<< "$(ncdump -h $(freva --databrowser $name=$option | head -n1) | grep -i :institution )"
    if [ -z "${INFO[1]}" ] ; then
	IFS='"' read -ra INFO <<< "$(ncdump -h $(freva --databrowser $name=$option | tail -n1) | grep -i :institution )"
    fi
    for list in $(freva --databrowser $name=$option); do
	if [ -z "${INFO[1]}" ] ; then
	    IFS='"' read -ra INFO <<< "$(ncdump -h ${list} | grep -i :institution )"
	else
	    break
	fi
    done
    echo '"'${option}'"' ":" '"'${INFO[1]}'"'',' >> ${JSONSCRIPT}
done
echo "};" >> ${JSONSCRIPT}



########
# END

cp $JSONSCRIPT ${WEBSITE_FILE}
