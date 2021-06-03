FROM solr:latest

LABEL maintainer="DRKZ-CLINT"
LABEL repository="https://gitlab.dkrz.de/freva/evaluation_system"


ARG NB_USER="freva"
ARG NB_UID="1000"
ARG repository="https://gitlab.dkrz.de/freva/evaluation_system"
ARG branch="new_cmd_arg_complete"
ENV USER ${NB_USER}
ENV HOME /home/${NB_USER}

USER root
RUN set -ex; \
  apt-get update; \
  apt-get -y install acl dirmngr gpg lsof procps wget netcat gosu tini mariadb-server git make sudo vim python3 zsh;\
  rm -rf /var/lib/apt/lists/*

ENV NB_USER=${NB_USER} \
    NB_UID=${NB_UID} \
    NB_GROUP=${NB_USER} \
    NB_GID=${NB_UID} \
    SOLR_USER=${NB_USER} \
    SOLR_HOME=${HOME}/solr/data \
    SOLR_PID_DIR=${HOME}/solr \
    SOLR_LOGS_DIR=${HOME}/solr/logs \
    LOG4J_PROPS=${HOME}/solr/log4j2.xml \
    PATH="/opt/evaluation_system/bin:/opt/solr/bin:/opt/docker-solr/scripts:$PATH"
RUN set -ex; \
  groupadd -r --gid "$NB_GID" "$NB_GROUP"; \
  adduser --uid "$NB_UID" --gid "$NB_GID" --gecos "Default user" \
  --shell /usr/bin/zsh --disabled-password "$NB_USER"

RUN set -ex; \
  echo SOLR_HOME=${HOME}/solr/data >> /etc/environment;\
  echo SOLR_PID_DIR=${HOME}/solr >> /etc/environment;\
  echo SOLR_LOGS_DIR=${HOME}/solr/logs >> /etc/environment;\
  echo LOG4J_PROPS=${HOME}/solr/log4j2.xml >> /etc/environment;\
  echo PATH=$PATH >> /etc/environment;\
  usermod -aG sudo ${NB_USER}; \
  echo "%sudo ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers;\
  cp -r /var/solr ${HOME}/ ;\
  chown -R "${NB_USER}:${NB_USER}" ${HOME}/solr;\
  sudo -E -u ${NB_USER} /opt/solr/bin/solr start;\
  sudo -E -u ${NB_USER} /usr/bin/git clone -b $branch $repository /tmp/evaluation_system ; \
  sudo -E -u ${NB_USER} /opt/solr/bin/solr create_core -c latest -d /opt/solr/example/files/conf ;\
  sudo -E -u ${NB_USER} /opt/solr/bin/solr create_core -c files -d /opt/solr/example/files/conf ;\
  sudo -E -u ${NB_USER} cp /tmp/evaluation_system/.docker/managed-schema ${SOLR_HOME}/latest/conf/managed-schema ; \
  sudo -E -u ${NB_USER} cp /tmp/evaluation_system/.docker/managed-schema ${SOLR_HOME}/files/conf/managed-schema; \
  sed -i 's/^\(bind-address\s.*\)/# \1/' /etc/mysql/my.cnf ; \
  service mysql start;\
  mysql < /tmp/evaluation_system/.docker/create_user.sql;\
  mysql -u freva -pT3st -D freva -h 127.0.0.1 < /tmp/evaluation_system/.docker/create_tables.sql;\
  service mysql stop ;\
  chown -R ${NB_USER}:${NB_GROUP} /var/run/mysqld /var/lib/mysql ;\
  cd /tmp/evaluation_system ;\
  mkdir -p /opt/evaluation_system/bin ;\
  cp /tmp/evaluation_system/src/evaluation_system/tests/mocks/bin/* /opt/evaluation_system/bin/ ; \
  cp /tmp/evaluation_system/.docker/*.sh /opt/evaluation_system/bin/ ;\
  cp /tmp/evaluation_system/.docker/zshrc ${HOME}/.zshrc;\
  cp /tmp/evaluation_system/.docker/evaluation_system.conf /tmp/evaluation_system/
RUN \
  cd /tmp/evaluation_system/;\
  chown -R ${NB_USER}:${NB_GROUP} /var/solr;\
  chmod 0771 ${HOME}/solr;\
  cd / && rm -r /tmp/evaluation_system;\
  find ${HOME}/solr -type d -print0 | xargs -0 chmod 0771; \
  find ${HOME}/solr -type f -print0 | xargs -0 chmod 0661

EXPOSE 8888
WORKDIR ${HOME}
USER $NB_USER

CMD /opt/evaluation_system/bin/loadfreva.sh
ENTRYPOINT ["/opt/evaluation_system/bin/docker-entrypoint.sh"]
