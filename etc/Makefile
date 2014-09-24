# PHONY marks all make commands that do not result in a created file

.PHONY: help
help:
	@echo 'creation of necessary symbolic links'
	@echo 'The supported configurations are:'
	@echo '	miklip'
	@echo '	wwwdev'
	@echo '	fu'
	@echo '	dwd'
	@echo ''
	@echo 'set links for a specific installation'
	@echo '	make #configuration install'
	@echo '	where #configuration is one configuration from the list above'
	@echo ''
	@echo 'check files for configuration:'
	@echo '	make #configuraion check'
	@echo '	where #configuration is one configuration from the list above'
	@echo ''
	@echo 'show'
	@echo '	make show'
	@echo '	shows links and missing links'
	@echo ''
	@echo 'make unlink'
	@echo '	removes all links'
	@echo ''
	@echo 'Example 1:'
	@echo '	make miklip install'
	@echo 'sets the links for configuration miklip'
	@echo ''
	@echo 'Example 2:'
	@echo '	make dwd check'
	@echo 'shows if all files exist for configuration dwd'

# Show the links set
.PHONY: show
show: $(ALL_LINKS)
	@echo 'The links set:'
	@file $(ALL_LINKS)


# show the files needed
.PHONY: check
check: $(ALL_FILES)
	@echo 'Needed files:'
	@file $(ALL_FILES)

############################################################################
# Here are the different files which have to be linked
############################################################################

DB_FILE=
DB_LINK=../src/evaluation_system/model/db.py

SOLRFILE_FILE=
SOLRFILE_LINK=../src/evaluation_system/model/file.py

CONFIG_FILE=
CONFIG_LINK=./evaluation_system.conf

ALL_LINKS=$(CONFIG_LINK) $(SOLRFILE_LINK) $(DB_LINK)
EVALUATE_ALL_FILES=$$(CONFIG_FILE) $$(SOLRFILE_FILE) $$(DB_FILE)


# set the links needed
.PHONY: install
install: $(ALL_FILES)
	ln -s $(CONFIG_FILE) $(CONFIG_LINK)
	ln -s $(SOLRFILE_FILE) $(SOLRFILE_LINK)
	ln -s $(DB_FILE) $(DB_LINK)


# remove all links
.PHONY: unlink
unlink: 
	rm -f $(ALL_LINKS)


#########################################################################
# The possible configurations will be entered here
# Alter the part below to add a new configuration
#########################################################################

miklip:
	@echo 'prepare setup for $@'
	$(eval CONFIG_FILE=./evaluation_system.miklip.conf)
	$(eval DB_FILE=/miklip/integration/evaluation_system/src/evaluation_system/model/db_mysql.py)
	$(eval SOLRFILE_FILE=/miklip/integration/evaluation_system/src/evaluation_system/model/file_miklip.py)
	$(eval ALL_FILES=$(EVALUATE_ALL_FILES))


wwwdev:
	@echo 'prepare setup for $@'
	$(eval CONFIG_FILE=./evaluation_system.wwwdev.conf)
	$(eval DB_FILE=../src/evaluation_system/model/db_mysql.py)
	$(eval SOLRFILE_FILE=../src/evaluation_system/model/file_miklip.py)
	$(eval ALL_FILES=$(EVALUATE_ALL_FILES))

fu:
	@echo 'prepare setup for $@'
	$(eval CONFIG_FILE=./evaluation_system.fu.conf)
	$(eval DB_FILE=../src/evaluation_system/model/db_mysql.py)
	$(eval SOLRFILE_FILE=../src/evaluation_system/model/file_miklip.py)
	$(eval ALL_FILES=$(EVALUATE_ALL_FILES))

dwd:
	@echo 'prepare setup for $@'
	$(eval CONFIG_FILE=./evaluation_system.dwd.conf)
	$(eval DB_FILE=../src/evaluation_system/model/db_none.py)
	$(eval SOLRFILE_FILE=../src/evaluation_system/model/file_dwd.py)
	$(eval ALL_FILES=$(EVALUATE_ALL_FILES))

