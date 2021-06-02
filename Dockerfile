FROM openjdk:11-jre

LABEL maintainer="DRKZ-CLINT"
LABEL repository="https://gitlab.dkrz.de/freva/evaluation_system"

ARG SOLR_VERSION="8.8.2"
ARG SOLR_SHA512="2f0affa8ac1e913ec83c2c4b8dffd6b262140478d5aa33203ac01fd5efb695eb9b1661138ce0c549b050fa0aadeb0912b5838b94703e1cca74ecfacbb57bbaee"
ARG SOLR_KEYS="86EDB9C33B8517228E88A8F93E48C0C6EF362B9E"
ARG NB_USER="freva"
ARG NB_UID="1000"
# If specified, this will override SOLR_DOWNLOAD_SERVER and all ASF mirrors. Typically used downstream for custom builds
ARG SOLR_DOWNLOAD_URL

# Override the solr download location with e.g.:
#   docker build -t mine --build-arg SOLR_DOWNLOAD_SERVER=http://www-eu.apache.org/dist/lucene/solr .
ARG SOLR_DOWNLOAD_SERVER

ENV USER ${NB_USER}
ENV HOME /home/${NB_USER}
ENV SOLR_MAJOR "8.8"
RUN set -ex; \
  apt-get update; \
  apt-get -y install acl dirmngr gpg lsof procps wget netcat gosu tini mariadb-server git make sudo vim python3; \
  rm -rf /var/lib/apt/lists/*; \
  cd /usr/local/bin; wget -nv https://github.com/apangin/jattach/releases/download/v1.5/jattach; chmod 755 jattach; \
  echo >jattach.sha512 "d8eedbb3e192a8596c08efedff99b9acf1075331e1747107c07cdb1718db2abe259ef168109e46bd4cf80d47d43028ff469f95e6ddcbdda4d7ffa73a20e852f9  jattach"; \
  sha512sum -c jattach.sha512; rm jattach.sha512

ENV SOLR_USER=${NB_USER} \
    SOLR_UID=${NB_UID} \
    SOLR_GROUP=${NB_USER} \
    SOLR_GID=${NB_UID} \
    SOLR_CLOSER_URL="http://www.apache.org/dyn/closer.lua?filename=lucene/solr/$SOLR_VERSION/solr-$SOLR_VERSION.tgz&action=download" \
    SOLR_DIST_URL="https://www.apache.org/dist/lucene/solr/$SOLR_VERSION/solr-$SOLR_VERSION.tgz" \
    SOLR_ARCHIVE_URL="https://archive.apache.org/dist/lucene/solr/$SOLR_VERSION/solr-$SOLR_VERSION.tgz" \
    PATH="/opt/evaluation_system/bin:/opt/solr/bin:/opt/docker-solr/scripts:$PATH" \
    SOLR_INCLUDE=/etc/default/solr.in.sh \
    SOLR_HOME=/var/solr/data \
    SOLR_PID_DIR=/var/solr \
    SOLR_LOGS_DIR=/var/solr/logs \
    LOG4J_PROPS=/var/solr/log4j2.xml

RUN set -ex; \
  groupadd -r --gid "$SOLR_GID" "$SOLR_GROUP"; \
  adduser --uid "$SOLR_UID" --gid "$SOLR_GID" --gecos "Default user" --disabled-password "$SOLR_USER"

RUN set -ex; \
  export GNUPGHOME="/tmp/gnupg_home"; \
  mkdir -p "$GNUPGHOME"; \
  chmod 700 "$GNUPGHOME"; \
  echo "disable-ipv6" >> "$GNUPGHOME/dirmngr.conf"; \
  for key in $SOLR_KEYS; do \
    found=''; \
    for server in \
      ha.pool.sks-keyservers.net \
      hkp://keyserver.ubuntu.com:80 \
      hkp://p80.pool.sks-keyservers.net:80 \
      pgp.mit.edu \
    ; do \
      echo "  trying $server for $key"; \
      gpg --batch --keyserver "$server" --keyserver-options timeout=10 --recv-keys "$key" && found=yes && break; \
      gpg --batch --keyserver "$server" --keyserver-options timeout=10 --recv-keys "$key" && found=yes && break; \
    done; \
    test -z "$found" && echo >&2 "error: failed to fetch $key from several disparate servers -- network issues?" && exit 1; \
  done; \
  exit 0

RUN set -ex; \
  export GNUPGHOME="/tmp/gnupg_home"; \
  MAX_REDIRECTS=1; \
  if [ -n "$SOLR_DOWNLOAD_URL" ]; then \
    # If a custom URL is defined, we download from non-ASF mirror URL and allow more redirects and skip GPG step
    # This takes effect only if the SOLR_DOWNLOAD_URL build-arg is specified, typically in downstream Dockerfiles
    MAX_REDIRECTS=4; \
    SKIP_GPG_CHECK=true; \
  elif [ -n "$SOLR_DOWNLOAD_SERVER" ]; then \
    SOLR_DOWNLOAD_URL="$SOLR_DOWNLOAD_SERVER/$SOLR_VERSION/solr-$SOLR_VERSION.tgz"; \
  fi; \
  for url in $SOLR_DOWNLOAD_URL $SOLR_CLOSER_URL $SOLR_DIST_URL $SOLR_ARCHIVE_URL; do \
    if [ -f "/opt/solr-$SOLR_VERSION.tgz" ]; then break; fi; \
    echo "downloading $url"; \
    if wget -t 10 --max-redirect $MAX_REDIRECTS --retry-connrefused -nv "$url" -O "/opt/solr-$SOLR_VERSION.tgz"; then break; else rm -f "/opt/solr-$SOLR_VERSION.tgz"; fi; \
  done; \
  if [ ! -f "/opt/solr-$SOLR_VERSION.tgz" ]; then echo "failed all download attempts for solr-$SOLR_VERSION.tgz"; exit 1; fi; \
  if [ -z "$SKIP_GPG_CHECK" ]; then \
    echo "downloading $SOLR_ARCHIVE_URL.asc"; \
    wget -nv "$SOLR_ARCHIVE_URL.asc" -O "/opt/solr-$SOLR_VERSION.tgz.asc"; \
    echo "$SOLR_SHA512 */opt/solr-$SOLR_VERSION.tgz" | sha512sum -c -; \
    (>&2 ls -l "/opt/solr-$SOLR_VERSION.tgz" "/opt/solr-$SOLR_VERSION.tgz.asc"); \
    gpg --batch --verify "/opt/solr-$SOLR_VERSION.tgz.asc" "/opt/solr-$SOLR_VERSION.tgz"; \
  else \
    echo "Skipping GPG validation due to non-Apache build"; \
  fi; \
  tar -C /opt --extract --file "/opt/solr-$SOLR_VERSION.tgz"; \
  (cd /opt; ln -s "solr-$SOLR_VERSION" solr); \
  rm "/opt/solr-$SOLR_VERSION.tgz"*; \
  rm -Rf /opt/solr/docs/ /opt/solr/dist/{solr-core-$SOLR_VERSION.jar,solr-solrj-$SOLR_VERSION.jar,solrj-lib,solr-test-framework-$SOLR_VERSION.jar,test-framework}; \
  mkdir -p /opt/solr/server/solr/lib /docker-entrypoint-initdb.d /opt/docker-solr; \
  chown -R 0:0 "/opt/solr-$SOLR_VERSION"; \
  find "/opt/solr-$SOLR_VERSION" -type d -print0 | xargs -0 chmod 0755; \
  find "/opt/solr-$SOLR_VERSION" -type f -print0 | xargs -0 chmod 0644; \
  chmod -R 0755 "/opt/solr-$SOLR_VERSION/bin" "/opt/solr-$SOLR_VERSION/contrib/prometheus-exporter/bin/solr-exporter" /opt/solr-$SOLR_VERSION/server/scripts/cloud-scripts; \
  cp /opt/solr/bin/solr.in.sh /etc/default/solr.in.sh; \
  mv /opt/solr/bin/solr.in.sh /opt/solr/bin/solr.in.sh.orig; \
  mv /opt/solr/bin/solr.in.cmd /opt/solr/bin/solr.in.cmd.orig; \
  chown root:0 /etc/default/solr.in.sh; \
  chmod 0664 /etc/default/solr.in.sh; \
  mkdir -p /var/solr/data /var/solr/logs; \
  (cd /opt/solr/server/solr; cp solr.xml zoo.cfg /var/solr/data/); \
  cp /opt/solr/server/resources/log4j2.xml /var/solr/log4j2.xml; \
  find /var/solr -type d -print0 | xargs -0 chmod 0770; \
  find /var/solr -type f -print0 | xargs -0 chmod 0660; \
  sed -i -e "s/\"\$(whoami)\" == \"root\"/\$(id -u) == 0/" /opt/solr/bin/solr; \
  sed -i -e 's/lsof -PniTCP:/lsof -t -PniTCP:/' /opt/solr/bin/solr; \
  chown -R "0:0" /opt/solr-$SOLR_VERSION /docker-entrypoint-initdb.d /opt/docker-solr; \
  chown -R "$SOLR_USER:0" /var/solr; \
  { command -v gpgconf; gpgconf --kill all || :; }; \
  rm -r "$GNUPGHOME";\
  git clone https://github.com/docker-solr/docker-solr.git /tmp/docker-solr; \
  chmod 0775 /tmp/docker-solr/${SOLR_MAJOR}/scripts/* ; \
  cp -r /tmp/docker-solr/${SOLR_MAJOR}/scripts /opt/docker-solr/ ; \
  chown -R "0:0" /opt/docker-solr/scripts ;\
  rm -r /tmp/docker-solr ;\
  sudo -E -u ${NB_USER} /opt/solr/bin/solr start ;\
  sudo -E -u ${NB_USER} /usr/bin/git clone -b update_install https://gitlab.dkrz.de/freva/evaluation_system.git /tmp/evaluation_system ; \
  sed -i 's/^\(bind-address\s.*\)/# \1/' /etc/mysql/my.cnf ; \
  echo "mysqld_safe &" > /tmp/config ; \
  echo "mysqladmin --user=${SOLR_USER} --silent --wait=30 ping || exit 1" >> /tmp/config ; \
  bash /tmp/config && rm -r /tmp/config ; \
  /bin/cp /tmp/evaluation_system/.docker/*.sql /tmp/evaluation_system/.docker/evaluation_system.conf /tmp/evaluation_system/.docker/managed-schema /tmp/evaluation_system/ ;\
  cd /tmp/evaluation_system ;\
  /usr/bin/mysql < /tmp/evaluation_system/create_user.sql ; \
  /usr/bin/mysql -u freva -pT3st -D freva -h 127.0.0.1 < /tmp/evaluation_system/create_tables.sql ;\
  /usr/bin/sudo -E -u ${NB_USER} /opt/solr/bin/solr create_core -c latest -d /opt/solr/example/files/conf ;\
  /usr/bin/sudo -E -u ${NB_USER} /opt/solr/bin/solr create_core -c files -d /opt/solr/example/files/conf ;\
  /usr/bin/sudo -E -u ${NB_USER} cp /tmp/evaluation_system/managed-schema /var/solr/data/latest/conf/managed-schema ; \
  /usr/bin/sudo -E -u ${NB_USER} cp /tmp/evaluation_system/managed-schema /var/solr/data/files/conf/managed-schema; \
  mysqladmin shutdown ;\
  chown -R ${SOLR_USER}:${SOLR_GROUP} /var/run/mysqld /var/lib/mysql ;\
  mkdir -p /opt/evaluation_system/bin ;\
  cp /tmp/evaluation_system/src/evaluation_system/tests/mocks/bin/* /opt/evaluation_system/bin/ ; \
  cp /tmp/evaluation_system/.docker/*.sh /opt/evaluation_system/bin/ ;\
  cp /tmp/evaluation_system/.docker/evaluation_system.conf /tmp/evaluation_system/ ;\
  cd /tmp/evaluation_system/;\
  /usr/bin/python3 deploy.py /opt/evaluation_system ; \
  /opt/evaluation_system/bin/python3 -m pip install --no-cache notebook jupyterhub;\
  cd / && rm -r /tmp/evaluation_system

COPY src/evaluation_system/tests/mocks/bin/* .docker/*.sh /opt/evaluation_system/bin/
VOLUME /var/solr
EXPOSE 8888
WORKDIR ${HOME}
USER $NB_USER

ENTRYPOINT ["/opt/evaluation_system/bin/docker-entrypoint.sh"]
CMD /opt/evaluation_system/bin/loadfreva.sh
