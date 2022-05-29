FROM solr:latest

LABEL maintainer="DRKZ-CLINT"
LABEL repository="https://gitlab.dkrz.de/freva/evaluation_system"
ARG NB_USER="freva"
ARG NB_UID="1000"
ARG binder="true"
ENV USER ${NB_USER}
ENV HOME /home/${NB_USER}
ENV SOLR_HOME=${HOME}/.solr \
    MYSQL_HOME=${HOME}/.mysql\
    MYSQL_PORT=3306

## Install Packages
USER root
RUN set -ex && \
  apt-get -y update && apt-get -y upgrade &&\
  apt-get -y install acl dirmngr gpg lsof procps netcat wget gosu tini \
             sudo git make vim python3 ffmpeg imagemagick\
             mariadb-server default-libmysqlclient-dev build-essential &&\
  if [ "$binder" = "true" ]; then\
    apt-get -y install python3-cartopy python-cartopy-data python3-xarray zsh nano\
    python3-h5netcdf libnetcdf-dev python3-dask python3-pip python3-pip-whl;\
  fi &&\
  rm -rf /var/lib/apt/lists/*

## Set all environment variables to run solr and mysql as a ordinary user
ENV NB_USER=${NB_USER} \
    NB_UID=${NB_UID} \
    NB_GROUP=${NB_USER} \
    NB_GID=${NB_UID} \
    SOLR_LOGS_DIR=${SOLR_HOME}/logs/solr \
    LOG4J_PROPS=${SOLR_HOME}/log4j2.xml\
    SOLR_PID_DIR=${SOLR_HOME} \
    MYSQL_LOGS_DIR=${MYSQL_HOME}/logs/mysql \
    MYSQL_DATA_DIR=${MYSQL_HOME}/mysqldata_${MYSQL_PORT} \
    IS_BINDER=$binder \
    PATH="/opt/evaluation_system/bin:/opt/solr/bin:/opt/solr/docker/scripts:$PATH"


COPY . /tmp/evaluation_system

# Setup users/groups and create directory structure
RUN set -ex && \
  groupadd -r --gid "$NB_GID" "$NB_GROUP" && \
  adduser --uid "$NB_UID" --gid "$NB_GID" --gecos "Default user" \
  --shell /usr/bin/zsh --disabled-password "$NB_USER" && \
  usermod -aG solr,mysql $NB_USER &&\
  cp /tmp/evaluation_system/src/evaluation_system/tests/mocks/bin/* /usr/local/bin/ && \
  cp /tmp/evaluation_system/.docker/evaluation_system.conf /tmp/evaluation_system/assets &&\
  ln -s /usr/bin/python3 /usr/bin/python &&\
  mkdir -p /opt/evaluation_system/bin &&\
  mkdir -p ${MYSQL_LOGS_DIR} ${SOLR_LOGS_DIR} ${MYSQL_DATA_DIR}/tmpl &&\
  cp /tmp/evaluation_system/.docker/mysqld_safe_user /opt/evaluation_system/bin/ &&\
  cp /tmp/evaluation_system/.docker/*.sh /opt/evaluation_system/bin/ &&\
  chmod +x /opt/evaluation_system/bin/* &&\
  chown -R ${NB_USER}:${NB_GROUP} ${HOME} ${MYSQL_HOME} ${SOLR_HOME}


# Prepare the mysql server
RUN set -x;\
  sed -i 's/^\(bind-address\s.*\)/# \1/' /etc/mysql/my.cnf && \
  cp /tmp/evaluation_system/compose/db/*.sql ${MYSQL_DATA_DIR}/tmpl/ &&\
  sudo -u ${NB_USER} mkdir -p /tmp/mysqld &&\
  mysql_install_db --user=$NB_USER --datadir=${MYSQL_DATA_DIR} --tmpdir=/tmp/mysqld/ &&\
  sudo -E -u ${NB_USER} /opt/evaluation_system/bin/mysqld_safe_user && \
  cat ${MYSQL_LOGS_DIR}/mysql-${MYSQL_PORT}-console.err  &&\
  mysqladmin --socket=${MYSQL_HOME}/mysql.${MYSQL_PORT}.sock --wait=5 ping &&\
  mysql --socket=${MYSQL_HOME}/mysql.${MYSQL_PORT}.sock -u root -pT3st < ${MYSQL_DATA_DIR}/tmpl/create_user.sql &&\
  mysql -u freva -pT3st -D freva -h 127.0.0.1 < ${MYSQL_DATA_DIR}/tmpl/create_tables.sql

# Prepare the solr server
RUN set -e;\
  /opt/solr/docker/scripts/init-var-solr && \
  /opt/solr/docker/scripts/precreate-core latest &&\
  /opt/solr/docker/scripts/precreate-core files &&\
  cp /tmp/evaluation_system/compose/solr/managed-schema.xml /var/solr/data/latest/conf/managed-schema.xml &&\
  cp /tmp/evaluation_system/compose/solr/managed-schema.xml /var/solr/data/files/conf/managed-schema.xml &&\
  find /var/solr -type d -print0 | xargs -0 chmod 0771 && \
  find /var/solr -type f -print0 | xargs -0 chmod 0661 && \
  cp -r /var/solr ${SOLR_HOME}


RUN \
  if [ "$binder" = "true" ]; then\
    set -e && \
    sudo -u $NB_USER git config --global init.defaultBranch main && \
    sudo -u $NB_USER git config --global user.email "freva@my.binder" &&\
    sudo -u $NB_USER git config --global user.name "Freva" &&\
    sudo -u $NB_USER git config --global --add safe.directory /mnt/freva_plugins/dummy &&\
    sudo -u $NB_USER git config --global --add safe.directory /mnt/freva_plugins/animator &&\
    sudo -u $NB_USER cp /tmp/evaluation_system/.docker/zshrc ${HOME}/.zshrc &&\
    cd /tmp/evaluation_system/ &&\
    /usr/bin/python3 -m pip install --no-cache . \
    notebook jupyterhub bash_kernel &&\
    /usr/bin/python3 -m ipykernel install --name freva &&\
    /usr/bin/python3 -m bash_kernel.install &&\
    cp -r /tmp/evaluation_system/.docker/data /mnt/data4freva &&\
    chmod -R 755 /mnt/data4freva &&\
    mkdir -p /etc/jupyter && \
    chmod -R 2777 /usr/freva_output &&\
    cp /tmp/evaluation_system/.docker/*.ipynb $HOME &&\
    cp /tmp/evaluation_system/.docker/jupyter_notebook_config.py /etc/jupyter &&\
    git clone --recursive https://gitlab.dkrz.de/freva/plugins4freva/animator.git /mnt/freva_plugins/animator &&\
    cp -r /tmp/evaluation_system/src/evaluation_system/tests/mocks /mnt/freva_plugins/dummy &&\
    cp /tmp/evaluation_system/.docker/ingest_dummy_data.py /tmp/evaluation_system/compose/solr &&\
    mv /tmp/evaluation_system $HOME/.evaluation_system &&\
    mv $HOME/.evaluation_system/.git /mnt/freva_plugins/dummy ;\
  else \
    rm -r /tmp/evaluation_system && \
    wget https://github.com/allure-framework/allure2/releases/download/2.14.0/allure-2.14.0.tgz -O allure.tgz &&\
    tar xzf allure.tgz -C /opt && mv /opt/allure-2.14.0 /opt/allure && rm allure.tgz ;\
  fi


RUN chown -R ${NB_USER}:${NB_GROUP} ${HOME} ${MYSQL_HOME} ${SOLR_HOME}

EXPOSE 8888
WORKDIR ${HOME}
USER $NB_USER

CMD ["/opt/evaluation_system/bin/loadfreva.sh"]
ENTRYPOINT ["/opt/evaluation_system/bin/docker-entrypoint.sh"]
