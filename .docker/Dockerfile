FROM mariadb:latest
LABEL maintainer="DRKZ-CLINT"
LABEL repository="https://gitlab.dkrz.de/freva/evaluation_system"
ARG binder="true"
## Set all environment variables
ENV SOLR_HOME=/opt/evaluation_system/.solr \
    MYSQL_HOME=/tmp/mysql\
    MYSQL_PORT=3306\
    MARIADB_ROOT_PASSWORD=T3st\
    IS_BINDER=$binder \
    EVALUATION_SYSTEM_CONFIG_FILE=/opt/evaluation_system/share/freva/evaluation_system.conf\
    EVALUATION_SYSTEM_DRS_CONFIG_FILE=/opt/evaluation_system/share/freva/drs_config.toml\
    EVAL_HOME=/opt/evaluation_system
## Set all environment variables to run solr and mysql as a ordinary user
ENV SOLR_LOGS_DIR=${SOLR_HOME}/logs/solr \
    LOG4J_PROPS=${SOLR_HOME}/log4j2.xml\
    SOLR_PID_DIR=${SOLR_HOME} \
    SOLR_JETTY_HOST=0.0.0.0 \
    JAVA_HOME=/opt/java/openjdk \
    SOLR_PORT=8983 \
    MYSQL_LOGS_DIR=${MYSQL_HOME}/logs/mysql \
    MYSQL_DATA_DIR=${MYSQL_HOME}/mysqldata_${MYSQL_PORT} \
    PATH="/opt/evaluation_system/bin:/opt/solr/prometheus-exporter/bin:/opt/java/openjdk/bin:/opt/solr/bin:/opt/solr/docker/scripts:$PATH"
## Copy important data from other containers
COPY --from=solr:latest /opt/solr/ /opt/solr/
COPY --from=solr:latest /opt/java/ /opt/java/
COPY --from=solr:latest /var/solr/ /var/solr/
COPY --from=condaforge/mambaforge:latest /opt/conda /opt/conda
COPY . /tmp/evaluation_system
RUN set -x && \
  groupadd -r --gid  1000 freva && \
  groupadd -r --gid  8983 solr && \
  adduser --uid 1001 --gid 1000 --gecos "Default user" \
  --shell /bin/bash --disabled-password freva && \
  usermod -aG solr,mysql freva &&\
  if [ "$binder" = "true" ]; then\
     /opt/conda/bin/conda create -y -q -c conda-forge cftime bash_kernel cartopy\
     h5netcdf netcdf4 ffmpeg pip notebook jupyterhub freva -p /opt/evaluation_system &&\
     /opt/evaluation_system/bin/python -m pip install pint-xarray cf_xarray nc-time-axis &&\
     /opt/evaluation_system/bin/python -m ipykernel install --name freva &&\
     /opt/evaluation_system/bin/python -m bash_kernel.install &&\
     git clone --recursive https://gitlab.dkrz.de/freva/plugins4freva/animator.git /mnt/freva_plugins/animator &&\
     mkdir -p /etc/jupyter /usr/freva_output && \
     chmod -R 2777 /usr/freva_output &&\
     mkdir -p /mnt/freva_plugins/dummy/.git &&\
     mv /tmp/evaluation_system/.git/config /mnt/freva_plugins/dummy/.git/ &&\
     cp /tmp/evaluation_system/src/evaluation_system/tests/mocks/dummy.py /mnt/freva_plugins/dummy &&\
     cp /mnt/freva_plugins/animator/.git/config . &&\
     rm -fr /mnt/freva_plugins/animator/.git/* &&\
     mv config /mnt/freva_plugins/animator/.git/ ;\
  else\
     /opt/conda/bin/conda create -y -q -c conda-forge make pip git conda -p /opt/evaluation_system;\
  fi &&\
  rm -rf /opt/conda &&\
  mkdir -p ${EVAL_HOME}/bin ${EVAL_HOME}/share/freva /mnt/freva_plugins \
  ${MYSQL_LOGS_DIR} ${SOLR_LOGS_DIR} ${MYSQL_DATA_DIR} ${MYSQL_HOME}/tmpl &&\
  mv /tmp/evaluation_system/src/evaluation_system/tests/mocks/bin/* /usr/local/bin/ && \
  cp /tmp/evaluation_system/.docker/evaluation_system.conf ${EVAL_HOME}/share/freva/ &&\
  cat /tmp/evaluation_system/compose/drs_config.toml |sed 's#.docker/data#/mnt/data4freva#g' > ${EVAL_HOME}/share/freva/drs_config.toml &&\
  mv /tmp/evaluation_system/.docker/*.sh ${EVAL_HOME}/bin/ &&\
  mv /tmp/evaluation_system/.docker/zshrc ${EVAL_HOME}/.zshrc &&\
  mv /tmp/evaluation_system/.docker/data /mnt/data4freva &&\
  mv /tmp/evaluation_system/docs/source/notebooks ${EVAL_HOME}/ &&\
  mv /tmp/evaluation_system/.docker/*.ipynb ${EVAL_HOME}/notebooks/ &&\
  mv /tmp/evaluation_system/compose/solr/ingest_dummy_data.py ${EVAL_HOME}/ &&\
  mv /tmp/evaluation_system/compose/dummy_user_data.py ${EVAL_HOME}/ &&\
  chmod -R 775 /mnt/data4freva /var/lib/mysql &&\
  chmod +x /opt/evaluation_system/bin/* &&\
  mv /tmp/evaluation_system/.docker/*.sql /docker-entrypoint-initdb.d/ &&\
  mv /tmp/evaluation_system/compose/config/mysql/*.sql /docker-entrypoint-initdb.d/ &&\
  /opt/solr/docker/scripts/init-var-solr && \
  /opt/solr/docker/scripts/precreate-core latest &&\
  /opt/solr/docker/scripts/precreate-core files &&\
  cp /tmp/evaluation_system/compose/config/solr/managed-schema.xml /var/solr/data/latest/conf/managed-schema.xml &&\
  cp /tmp/evaluation_system/compose/config/solr/managed-schema.xml /var/solr/data/files/conf/managed-schema.xml &&\
  find /var/solr -type d -print0 | xargs -0 chmod 0771 && \
  find /var/solr -type f -print0 | xargs -0 chmod 0661 && \
  mv /var/solr ${SOLR_HOME} &&\
  ln -s ${SOLR_HOME} /var/solr &&\
  chown -R freva:freva ${MYSQL_HOME} &&\
  echo "[mariadbd]" > /etc/mysql/my.cnf &&\
  echo "user            = freva" >> /etc/mysql/my.cnf &&\
  echo "port            = ${MYSQL_PORT}" >> /etc/mysql/my.cnf &&\
  echo "datadir         = ${MYSQL_DATA_DIR}" >> /etc/mysql/my.cnf &&\
  echo "socket          = ${MYSQL_HOME}/mysql.${MYSQL_PORT}.sock" >> /etc/mysql/my.cnf &&\
  echo "log-error       = ${MYSQL_LOGS_DIR}/mysql-${MYSQL_PORT}-console.err" >> /etc/mysql/my.cnf &&\
  echo "max_connections = 10" >> /etc/mysql/my.cnf &&\
  echo "key_buffer_size = 8M" >> /etc/mysql/my.cnf &&\
  echo "FLUSH PRIVILEGES; ALTER USER 'root'@'localhost' IDENTIFIED BY 'T3st';" > /tmp/set_root_pw &&\
  echo "set -e" > /tmp/mysql_init &&\
  echo "mariadb-install-db" >> /tmp/mysql_init &&\
  echo "nohup mariadbd --skip-grant-tables &" >> /tmp/mysql_init &&\
  echo "mysqladmin --socket=${MYSQL_HOME}/mysql.${MYSQL_PORT}.sock --wait=5 ping || exit 1" >> /tmp/mysql_init &&\
  bash /tmp/mysql_init && rm /tmp/mysql_init &&\
  cat ${MYSQL_LOGS_DIR}/mysql-${MYSQL_PORT}-console.err &&\
  mysql -u root -h 127.0.0.1 < /tmp/set_root_pw &&\
  mysql -u root -h 127.0.0.1 -pT3st < /docker-entrypoint-initdb.d/create_user.sql &&\
  mysql -u root -pT3st -h 127.0.0.1 -D freva < /docker-entrypoint-initdb.d/create_tables.sql &&\
  chown -R freva:freva  ${EVAL_HOME} ${MYSQL_HOME} ${SOLR_HOME} && \
  chmod -R 775 ${MYSQL_HOME} ${SOLR_HOME} && \
  rm /tmp/set_root_pw
EXPOSE 8888
USER freva
WORKDIR /home/freva
CMD ["/opt/evaluation_system/bin/loadfreva.sh"]
ENTRYPOINT ["/opt/evaluation_system/bin/docker-entrypoint.sh"]
