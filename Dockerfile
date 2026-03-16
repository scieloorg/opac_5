FROM python:3.11.0-alpine
ENV PYTHONUNBUFFERED 1

# Build-time metadata as defined at http://label-schema.org
ARG OPAC_BUILD_DATE
ARG OPAC_VCS_REF
ARG OPAC_WEBAPP_VERSION

ENV OPAC_BUILD_DATE ${OPAC_BUILD_DATE}
ENV OPAC_VCS_REF ${OPAC_VCS_REF}
ENV OPAC_WEBAPP_VERSION ${OPAC_WEBAPP_VERSION}

LABEL org.label-schema.build-date=$OPAC_BUILD_DATE \
      org.label-schema.name="OPAC WebApp - development build" \
      org.label-schema.description="OPAC WebApp main app" \
      org.label-schema.url="https://github.com/scieloorg/opac/" \
      org.label-schema.vcs-ref=$OPAC_VCS_REF \
      org.label-schema.vcs-url="https://github.com/scieloorg/opac/" \
      org.label-schema.vendor="SciELO" \
      org.label-schema.version=$OPAC_WEBAPP_VERSION \
      org.label-schema.schema-version="1.0"

RUN apk --update add --no-cache \
    git gcc build-base zlib-dev jpeg-dev \
    curl libxml2-dev libxslt-dev py3-lxml libffi-dev

COPY . /app
WORKDIR /app

RUN pip install --upgrade pip

# Remove src/ para evitar conflito com instaláveis editáveis do git (opac_schema, packtools, etc.):
# se o diretório já existir e não for um clone, o pip pergunta interativamente e o build falha com EOFError.
RUN rm -rf /app/src

RUN pip --no-cache-dir install -U pip && \
    pip --no-cache-dir install -r /app/requirements.txt && \
    pip --no-cache-dir install -r /app/requirements.dev.txt

RUN sed -i 's/\r//' start_worker.sh \
    && sed -i 's/\r//' start_scheduler.sh \
    && chmod +x start_worker.sh \
    && chmod +x start_scheduler.sh \
    && chown nobody start_worker.sh \
    && chown nobody start_scheduler.sh

RUN make compile_messages
RUN chown -R nobody:nogroup /app
VOLUME /app/data
USER nobody
EXPOSE 8000

HEALTHCHECK --interval=5m --timeout=3s \
  CMD curl -f http://localhost:8000/ || exit 1

CMD gunicorn --worker-class=gevent --worker-connections=1000 --workers 3 --bind 0.0.0.0:8000 app:app --chdir=/app/opac --timeout 150 --log-level INFO
