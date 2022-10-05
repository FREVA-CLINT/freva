FROM registry.gitlab.dkrz.de/freva/evaluation_system/freva:latest

ARG NB_USER="nb_user"
ARG NB_UID="1000"

ENV USER=${NB_USER} \
    HOME=/tmp/${NB_USER} \
    NB_GID=${NB_UID} \
    NB_GROUP=${NB_USER}\
    DJANGO_ALLOW_ASYNC_UNSAFE=1
USER root
RUN set -e && \
  adduser --uid "$NB_UID" --gid 1000 --gecos "Default user" \
  --shell /bin/bash --disabled-password "$NB_USER" --home $HOME && \
  cp ${EVAL_HOME}/notebooks/*.ipynb ${HOME}/ &&\
  chown -R $NB_USER:freva $HOME

USER $NB_USER
WORKDIR $HOME
RUN cp $EVAL_HOME/notebooks/*.ipynb ${HOME}/
