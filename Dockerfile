FROM solr:latest

LABEL maintainer="DRKZ-CLINT"
LABEL repository="https://gitlab.dkrz.de/freva/evaluation_system"


ARG NB_USER="freva"
ARG NB_UID="1000"
ARG repository="https://gitlab.dkrz.de/freva/evaluation_system"
ARG branch="add_xmpl_data"
ARG binder="true"
ENV USER ${NB_USER}
ENV HOME /home/${NB_USER}

USER root
RUN set -ex; \
  apt-get update; apt-get -y upgrade ; \
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
  wget https://github.com/allure-framework/allure2/releases/download/2.14.0/allure-2.14.0.tgz -O allure.tgz;\
  tar xzf allure.tgz -C /opt; mv /opt/allure-2.14.0 /opt/allure; rm allure.tgz;\
  echo SOLR_HOME=${HOME}/solr/data >> /etc/environment;\
  echo SOLR_PID_DIR=${HOME}/solr >> /etc/environment;\
  echo SOLR_LOGS_DIR=${HOME}/solr/logs >> /etc/environment;\
  echo LOG4J_PROPS=${HOME}/solr/log4j2.xml >> /etc/environment;\
  echo PATH=$PATH >> /etc/environment;\
  cp -r /var/solr ${HOME}/ ;\
  chown -R "${NB_USER}:${NB_USER}" ${HOME}/solr;\
  sudo -E -u ${NB_USER} /opt/solr/bin/solr start;\
  sudo -E -u ${NB_USER} /usr/bin/git clone -b $branch $repository /tmp/evaluation_system ; \
  sudo -E -u ${NB_USER} /opt/solr/bin/solr create_core -c latest -d /opt/solr/example/files/conf ;\
  sudo -E -u ${NB_USER} /opt/solr/bin/solr create_core -c files -d /opt/solr/example/files/conf ;\
  sudo -E -u ${NB_USER} cp /tmp/evaluation_system/.docker/managed-schema ${SOLR_HOME}/latest/conf/managed-schema ; \
  sudo -E -u ${NB_USER} cp /tmp/evaluation_system/.docker/managed-schema ${SOLR_HOME}/files/conf/managed-schema; \
  #sudo -E -u ${NB_USER} /opt/solr/bin/solr stop;\
  sed -i 's/^\(bind-address\s.*\)/# \1/' /etc/mysql/my.cnf ; \
  echo "mysqld_safe &" > /tmp/config ; \
  echo "mysqladmin --silent --wait=30 ping || exit 1" >> /tmp/config ; \
  bash /tmp/config && rm -r /tmp/config ; \
  cp /tmp/evaluation_system/.docker/*.sql\
    /tmp/evaluation_system/.docker/evaluation_system.conf\
    /tmp/evaluation_system/.docker/managed-schema /tmp/evaluation_system/ ;\
  cd /tmp/evaluation_system ;\
  mysql < /tmp/evaluation_system/create_user.sql ; \
  mysql -u freva -pT3st -D freva -h 127.0.0.1 < /tmp/evaluation_system/create_tables.sql ;\
  mysqladmin shutdown ;\
  chown -R ${NB_USER}:${NB_GROUP} /var/run/mysqld /var/lib/mysql ;\
  mkdir -p /opt/evaluation_system/bin ;\
  cp /tmp/evaluation_system/src/evaluation_system/tests/mocks/bin/* /opt/evaluation_system/bin/ ; \
  cp /tmp/evaluation_system/.docker/*.sh /opt/evaluation_system/bin/ ;\
  cp /tmp/evaluation_system/.docker/evaluation_system.conf /tmp/evaluation_system/;\
  chmod 0771 ${HOME}/solr;\
  chown -R ${NB_USER}:${NB_GROUP} /var/solr;\
  find ${HOME}/solr -type d -print0 | xargs -0 chmod 0771; \
  find ${HOME}/solr -type f -print0 | xargs -0 chmod 0661
RUN \
  if [ "$binder" = "true" ];then\
  cp /tmp/evaluation_system/.docker/zshrc ${HOME}/.zshrc;\
  chown -R ${NB_USER}:${NB_GROUP} $HOME/.zshrc; \
  cd /tmp/evaluation_system/;\
  /usr/bin/python3 deploy.py /opt/evaluation_system ; \
  /opt/evaluation_system/bin/python3 -m pip install --no-cache notebook jupyterhub;\
  /opt/evaluation_system/bin/python3 -m pip install bash_kernel;\
  /opt/evaluation_system/bin/python3 -m bash_kernel.install;\
  cp -r /tmp/evaluation_system/.docker/data /mnt/data4freva;\
  mkdir -p /etc/jupyter; mkdir -p ${HOME}/data4freva;\
  mkdir -p /mnt/plugin4freva; mkdir /opt/freva-work;\
  chmod -R 777 /opt/freva-work;\
  cp /tmp/evaluation_system/.docker/jupyter_notebook_config.py /etc/jupyter;\
  cd / && rm -r /tmp/evaluation_system;\
  git clone --recursive https://gitlab.dkrz.de/freva/plugins4freva/animator.git /mnt/plugin4freva/animator;\
  /opt/evaluation_system/sbin/solr_ingest --crawl /mnt/data4freva/observations --output /tmp/dump.gz;\
  /opt/evaluation_system/sbin/solr_ingest --ingest /tmp/dump.gz;rm /tmp/dump.gz;\
  mkdir -p /opt/evaluation_system/share/preview; chown -R 777 /opt/evaluation_system/share/preview;\
  chown -R ${NB_USER}:${NB_GROUP} /opt/evaluation_system/share;\
  chown -R ${NB_USER}:${NB_GROUP} $HOME/.cache;\
  chown -R ${NB_USER}:${NB_GROUP} $HOME/.conda;fi
EXPOSE 8888
WORKDIR ${HOME}
USER $NB_USER

CMD /opt/evaluation_system/bin/loadfreva.sh
ENTRYPOINT ["/opt/evaluation_system/bin/docker-entrypoint.sh"]
