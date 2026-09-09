# syntax=docker/dockerfile:1
# Production image for Staff Pro BPO (Frappe + ERPNext + this HRMS app).
ARG FRAPPE_BRANCH=develop
ARG FRAPPE_IMAGE_PREFIX=frappe

FROM ${FRAPPE_IMAGE_PREFIX}/build:${FRAPPE_BRANCH} AS builder

ARG FRAPPE_BRANCH=develop
ARG FRAPPE_PATH=https://github.com/frappe/frappe

USER frappe

COPY --chown=frappe:frappe deploy/apps.json /opt/frappe/apps.json

RUN bench init \
	--apps_path=/opt/frappe/apps.json \
	--frappe-branch=${FRAPPE_BRANCH} \
	--frappe-path=${FRAPPE_PATH} \
	--no-procfile \
	--no-backups \
	--skip-redis-config-generation \
	--verbose \
	/home/frappe/frappe-bench && \
	cd /home/frappe/frappe-bench && \
	echo "{}" > sites/common_site_config.json && \
	find apps -mindepth 1 -path "*/.git" | xargs rm -fr

COPY --chown=frappe:frappe . /home/frappe/frappe-bench/apps/hrms

WORKDIR /home/frappe/frappe-bench

# bench init may write apps.txt without a trailing newline, so "echo hrms >>"
# would glue it onto the last app ("paymentshrms") and break bench build.
RUN <<'EOF'
set -eu
./env/bin/pip install -e apps/hrms
python3 -c 'from pathlib import Path
p = Path("sites/apps.txt")
apps = [a.strip() for a in p.read_text().splitlines() if a.strip()]
if "hrms" not in apps:
    apps.append("hrms")
p.write_text("\n".join(apps) + "\n")'
yarn --cwd apps/hrms install
yarn --cwd apps/hrms build
bench build --app hrms
EOF

FROM ${FRAPPE_IMAGE_PREFIX}/base:${FRAPPE_BRANCH} AS backend

USER root
RUN apt-get update && \
	apt-get install -y --no-install-recommends nginx && \
	rm -rf /var/lib/apt/lists/* && \
	mkdir -p /opt/staffpro /tmp/nginx_client_body /tmp/nginx_proxy && \
	chown -R frappe:frappe /opt/staffpro /tmp/nginx_client_body /tmp/nginx_proxy

USER frappe

COPY --from=builder --chown=frappe:frappe /home/frappe/frappe-bench /home/frappe/frappe-bench

WORKDIR /home/frappe/frappe-bench

RUN cp -r /home/frappe/frappe-bench/sites/assets /home/frappe/frappe-bench/assets && \
	rm -rf /home/frappe/frappe-bench/sites/assets

COPY --chown=frappe:frappe deploy/nginx.conf.template /opt/staffpro/nginx.conf.template
COPY --chown=frappe:frappe deploy/entrypoint.sh /opt/staffpro/entrypoint.sh

USER root
RUN chmod 755 /opt/staffpro/entrypoint.sh

USER frappe

ENV PORT=10000
EXPOSE 10000

ENTRYPOINT ["/opt/staffpro/entrypoint.sh"]
