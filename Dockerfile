FROM solr:latest

LABEL maintainer="DRKZ-CLINT"
LABEL repository="https://gitlab.dkrz.de/freva/evaluation_system"
ARG NB_USER="freva"
ARG NB_UID="1000"
ARG binder="true"
ENV USER ${NB_USER}
ENV HOME /home/${NB_USER}
ENV SOLR_HOME /home/${NB_USER}/.solr
ENV SOLR_LOGS_DIR ${SOLR_HOME}/logs
ENV MYSQL_LOGS_DIR /var/log/freva/mysql
ENV LOG4J_PROPS ${SOLR_HOME}/log4j2.xml
ENV SOLR_PID_DIR ${SOLR_HOME}

USER root
RUN set -ex; \
  apt-get -y update;\
  apt-get -y install wget sudo git make vim nano python3 zsh ffmpeg imagemagick\
             mariadb-server default-libmysqlclient-dev build-essential &&\
  rm -rf /var/lib/apt/lists/*

ENV NB_USER=${NB_USER} \
    NB_UID=${NB_UID} \
    NB_GROUP=${NB_USER} \
    NB_GID=${NB_UID} \
    PATH="/opt/evaluation_system/bin:/opt/solr/bin:/opt/solr/docker/scripts:$PATH"

COPY . /tmp/evaluation_system

RUN set -ex; \
  groupadd -r --gid "$NB_GID" "$NB_GROUP" && \
  adduser --uid "$NB_UID" --gid "$NB_GID" --gecos "Default user" \
  --shell /usr/bin/zsh --disabled-password "$NB_USER" && \
  usermod -aG solr $NB_USER

RUN set -ex; \
  #wget https://github.com/allure-framework/allure2/releases/download/2.14.0/allure-2.14.0.tgz -O allure.tgz &&\
  #tar xzf allure.tgz -C /opt; mv /opt/allure-2.14.0 /opt/allure; rm allure.tgz &&\
  echo PATH=$PATH >> /etc/environment;\
  echo SOLR_HOME=$SOLR_HOME >> /etc/environment;\
  sed -i 's/^\(bind-address\s.*\)/# \1/' /etc/mysql/my.cnf && \
  echo "mysqld_safe &" > /tmp/config && \
  echo "mysqladmin --silent --wait=30 ping || exit 1" >> /tmp/config && \
  bash /tmp/config && rm -r /tmp/config && \
  mysql < /tmp/evaluation_system/compose/db/create_user.sql && \
  mysql -u freva -pT3st -D freva -h 127.0.0.1 < /tmp/evaluation_system/compose/db/create_tables.sql &&\
  mysqladmin shutdown && \
  chown -R ${NB_USER}:${NB_GROUP} /var/run/mysqld /var/lib/mysql &&\
  mkdir -p ${MYSQL_LOGS_DIR} &&\
  chown -R ${NB_USER}:${NB_GROUP} ${MYSQL_LOGS_DIR} &&\
  mkdir -p /opt/evaluation_system/bin &&\
  cp /tmp/evaluation_system/src/evaluation_system/tests/mocks/bin/* /opt/evaluation_system/bin/ && \
  cp /tmp/evaluation_system/.docker/*.sh /opt/evaluation_system/bin/ &&\
  cp /tmp/evaluation_system/.docker/evaluation_system.conf /tmp/evaluation_system/assets

RUN \
  if [ "$binder" = "true" ]; then\
    set -ex; \
    cp /tmp/evaluation_system/.docker/zshrc ${HOME}/.zshrc &&\
    cd /tmp/evaluation_system/ &&\
    /usr/bin/python3 deploy.py /opt/evaluation_system -s --packages gitpython pandoc cartopy xarray dask cftime && \
    /opt/evaluation_system/bin/python3 -m pip install --no-cache notebook jupyterhub &&\
    /opt/evaluation_system/bin/python3 -m pip install bash_kernel &&\
    /opt/evaluation_system/bin/python3 -m ipykernel install --name freva &&\
    /opt/evaluation_system/bin/python3 -m bash_kernel.install &&\
    cp -r /tmp/evaluation_system/.docker/data /mnt/data4freva &&\
    mkdir -p /etc/jupyter; mkdir -p ${HOME}/data4freva && \
    mkdir -p /opt/evaluation_system/etc/jupyter &&\
    mkdir -p /mnt/plugin4freva; mkdir /opt/freva-work &&\
    chmod -R 777 /opt/freva-work &&\
    cp /tmp/evaluation_system/.docker/*.ipynb $HOME &&\
    cp /tmp/evaluation_system/.docker/jupyter_notebook_config.py /etc/jupyter &&\
    cp /tmp/evaluation_system/.docker/jupyter_notebook_config.py /opt/evaluation_system/etc/jupyter &&\
    cd / && rm -r /tmp/evaluation_system &&\
    git clone --recursive https://gitlab.dkrz.de/freva/plugins4freva/animator.git /mnt/plugin4freva/animator &&\
    mkdir -p /opt/evaluation_system/share/preview; chown -R 777 /opt/evaluation_system/share/preview &&\
    chown -R ${NB_USER}:${NB_GROUP} /opt/evaluation_system/share &&\
    chown -R ${NB_USER}:${NB_GROUP} $HOME/.cache &&\
    chown -R ${NB_USER}:${NB_GROUP} $HOME/.conda ;\
  fi

COPY .docker/docker-entrypoint.sh /opt/evaluation_system/bin/
COPY .docker/loadfreva.sh /opt/evaluation_system/bin/

RUN \
  /opt/solr/docker/scripts/init-var-solr && \
  /opt/solr/docker/scripts/precreate-core latest &&\
  /opt/solr/docker/scripts/precreate-core files &&\
  cp /tmp/evaluation_system/compose/solr/managed-schema.xml /var/solr/data/latest/conf/managed-schema.xml &&\
  cp /tmp/evaluation_system/compose/solr/managed-schema.xml /var/solr/data/files/conf/managed-schema.xml &&\
  find /var/solr -type d -print0 | xargs -0 chmod 0771 && \
  find /var/solr -type f -print0 | xargs -0 chmod 0661 && \
  cp -r /var/solr ${SOLR_HOME} &&\
  mkdir -p ${SOLR_LOGS_DIR} &&\
  chown -R ${NB_USER}:${NB_GROUP} $HOME  ${SOLR_HOME}

EXPOSE 8888
WORKDIR ${HOME}
USER $NB_USER

CMD ["/opt/evaluation_system/bin/loadfreva.sh"]
ENTRYPOINT ["/opt/evaluation_system/bin/docker-entrypoint.sh"]
