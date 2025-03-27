
# define an alias for the specific python version used in this file.
FROM docker.io/python:3.12.5-slim-bookworm AS python

# Python build stage
FROM python AS python-build-stage

ARG BUILD_ENVIRONMENT=production

# Install apt packages
RUN apt-get update && apt-get install --no-install-recommends -y \
  # dependencies for building Python packages
  build-essential \
  # psycopg2 dependencies
  libpq-dev

# Requirements are installed here to ensure they will be cached.
COPY ./requirements .

# Create Python Dependency and Sub-Dependency Wheels.
RUN pip wheel --wheel-dir /usr/src/app/wheels  \
  -r ${BUILD_ENVIRONMENT}.txt


# Python 'run' stage
FROM python AS python-run-stage

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV BUILD_ENV=${BUILD_ENVIRONMENT}

WORKDIR ${APP_HOME}

RUN addgroup --system django \
    && adduser --system --ingroup django django


# Install required system dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
  # psycopg2 dependencies
  libpq-dev \
  # Translations dependencies
  gettext \
  # video codecs
  # kafka compression
  libsnappy-dev\
  # Geodjango dependencies
  binutils \
  libproj-dev \
  gdal-bin \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# All absolute dir copies ignore workdir instruction. All relative dir copies are wrt to the workdir instruction
# copy python dependency wheels from python-build-stage
COPY --from=python-build-stage /usr/src/app/wheels  /wheels/

# use wheels to install python dependencies
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
  && rm -rf /wheels/

# Install Node.js
# RUN apt-get update && apt-get install -y curl
# RUN curl -sL https://deb.nodesource.com/setup_20.x | bash -
# RUN apt-get install -y nodejs

# WORKDIR ${APP_HOME}/core/static
# # Copy the package.json from the correct location
# COPY ./core/static/package.json .

# # Copy tailwind config file from its location
# COPY ./core/static/tailwind.config.js .

# # Install Node.js dependencies
# RUN npm install


# Run Tailwind CSS build
# RUN npx tailwindcss -o css/style.css --minify

# WORKDIR ${APP_HOME}

# copy application code to WORKDIR
COPY --chown=django:django . ${APP_HOME}

# make django owner of the WORKDIR directory as well.
RUN chown django:django ${APP_HOME}
# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh

# Switch to root user to change permissions
USER root

# Make the script executable
RUN chmod +x /entrypoint.sh

# Switch back to django user
USER django

# Set the entrypoint script as the default command
CMD ["/entrypoint.sh"]
