FROM solr:latest
MAINTAINER dkrz-clint
USER root
ARG NB_USER
ARG NB_UID
ENV USER ${NB_USER}
ENV HOME /home/${NB_USER}
RUN adduser --disabled-password \
    --gecos "Default user" \
    --uid ${NB_UID} \
    ${NB_USER} && \
    /usr/bin/apt -y update && /usr/bin/apt -y upgrade &&\
    /usr/bin/apt -y install git mariadb-server python3 make sudo vim && \
    /usr/bin/sudo -E -u solr /usr/bin/git clone -b update_install https://gitlab.dkrz.de/freva/evaluation_system.git /tmp/evaluation_system && \
    mkdir -p /opt/evaluation_system/bin && chown -R solr:solr /opt/evaluation_system &&\
    usermod -aG sudo solr && echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers &&\
    usermod -aG sudo ${NB_USER} &&\
    cp /tmp/evaluation_system/.docker/*.sql /tmp/evaluation_system/.docker/evaluation_system.conf /tmp/evaluation_system/.docker/managed-schema /tmp/evaluation_system/ &&\
    cd /tmp/evaluation_system && service mysql start && \
    /usr/bin/sudo -E -u solr /opt/solr/bin/solr start &&\
    /usr/bin/python3 deploy.py /opt/evaluation_system && \
    /usr/bin/mysql < /tmp/evaluation_system/create_user.sql && \
    /usr/bin/mysql -u freva -pT3st -D freva -h 127.0.0.1 < /tmp/evaluation_system/create_tables.sql &&\
    /usr/bin/sudo -E -u solr /opt/solr/bin/solr create_core -c latest -d /opt/solr/example/files/conf &&\
    /usr/bin/sudo -E -u solr /opt/solr/bin/solr create_core -c files -d /opt/solr/example/files/conf &&\
    /usr/bin/git config --global init.defaultBranch main &&\
    /usr/bin/git config --global user.email "user@docker.org" &&\
    /usr/bin/git config --global user.name "Freva" &&\
    /usr/bin/sudo -E -u solr cp /tmp/evaluation_system/managed-schema /var/solr/data/latest/conf/managed-schema &&\
    /usr/bin/sudo -E -u solr cp /tmp/evaluation_system/managed-schema /var/solr/data/files/conf/managed-schema &&\
    /bin/cp /tmp/evaluation_system/src/evaluation_system/tests/mocks/bin/* /opt/evaluation_system/bin/ &&\
    cp /tmp/evaluation_system/.docker/*.sh /opt/evaluation_system/bin/ &&\
    /opt/evaluation_system/bin/python3 -m pip install --no-cache notebook &&\
    cd / && /bin/rm -r /tmp/evaluation_system
USER ${NB_USER}
WORKDIR ${HOME}
ENV PATH="/opt/evaluation_system/bin:/opt/solr/bin:/opt/docker-solr/scripts:$PATH"
ENTRYPOINT ["/opt/evaluation_system/bin/docker-entrypoint.sh"]
CMD /opt/evaluation_system/bin/loadfreva.sh
