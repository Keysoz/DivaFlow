# Diva Store image: ERPNext 16 + Diva apps + the tracked POS Next patch set.
#
# Build from the REPOSITORY ROOT, not from this directory, so apps/, packages/
# and infra/ come straight from source (no duplicate trees):
#   docker build -f infra/images/store/Dockerfile -t diva-store:latest .
#
# PROD-01: the base is pinned by digest, resolved from frappe/erpnext:v16.52.1.
FROM frappe/erpnext:v16.52.1@sha256:eb1c22d2bb926ed97352b63334507bf0297f1ca1244b406e3f30869ca5d0092b

LABEL org.opencontainers.image.title="diva-store"
LABEL org.opencontainers.image.description="Diva Store: ERPNext 16 with diva_guard, diva_desk, custom_reports and POS Next"

WORKDIR /home/frappe/frappe-bench

# PROD-01: this clone needs network access. Vendoring the POS Next source into
# the payload is required before the installer can run fully offline.
USER frappe

COPY --chown=frappe:frappe apps/diva_guard apps/diva_guard
COPY --chown=frappe:frappe apps/diva_desk apps/diva_desk
COPY --chown=frappe:frappe apps/custom_reports apps/custom_reports
COPY --chown=frappe:frappe packages/rules-engine apps/rules-engine
COPY --chown=frappe:frappe infra/posnext-patches infra/posnext-patches

# Build backends used by the Diva and POS Next pyprojects. Pre-installing them
# lets the editable installs run without build isolation, so a flaky download
# of hatchling/flit_core cannot fail the image build.
RUN /home/frappe/frappe-bench/env/bin/python -m pip install --no-cache-dir \
        --retries 10 --timeout 60 hatchling "flit_core>=3.4,<4" editables

# `pip` on PATH is the system interpreter; bench uses the virtualenv at
# frappe-bench/env. Install into that venv explicitly, otherwise the apps are
# importable from plain `python` but `bench` reports "No module named".
RUN /home/frappe/frappe-bench/env/bin/python -m pip install --no-cache-dir \
        --no-build-isolation -e apps/rules-engine -e apps/diva_guard \
        -e apps/diva_desk -e apps/custom_reports

# POS Next, pinned to the tag the patch set is written against. apply.sh refuses
# to run unless HEAD is the recorded base commit.
RUN git clone --depth 1 --branch v2.0.0 https://github.com/BrainWise-DEV/POSNext.git apps/pos_next \
    && bash infra/posnext-patches/apply.sh apps/pos_next

# POS Next declares `erpnext` as a PyPI dependency, but ERPNext is a bench app,
# not a wheel. Install the app without resolving deps and add its one real
# dependency (pypdf) explicitly.
RUN /home/frappe/frappe-bench/env/bin/python -m pip install --no-cache-dir \
        --no-build-isolation --no-deps -e apps/pos_next \
    && /home/frappe/frappe-bench/env/bin/python -m pip install --no-cache-dir "pypdf>=6.12.0"

# Build the assets for the apps that ship JavaScript. `bench build --app` reads
# sites/apps.txt, so list every app first. POS Next imports `socketio_port` from
# common_site_config.json at build time, so seed it here (the configurator
# rewrites the file at run time). The base image moves sites/assets to
# frappe-bench/assets and the entrypoint symlinks it back, so do the same or the
# runtime symlink would hide the POS Next build.
RUN printf 'frappe\nerpnext\ndiva_guard\ndiva_desk\ncustom_reports\npos_next\n' > sites/apps.txt \
    && printf '{"socketio_port": 9000}\n' > sites/common_site_config.json \
    && bench build --app frappe --app erpnext --app pos_next \
    && rm -rf assets \
    && mv sites/assets assets

# Runtime helpers. Kept after the expensive build so editing a shell script
# does not invalidate the app install and asset layers.
COPY --chown=frappe:frappe infra/erpnext-config infra/erpnext-config
COPY --chown=frappe:frappe scripts/docker/configure.sh /opt/diva/configure.sh
COPY --chown=frappe:frappe scripts/docker/create-site.sh /opt/diva/create-site.sh

RUN chmod +x /opt/diva/configure.sh /opt/diva/create-site.sh

EXPOSE 8080 9000

CMD ["bench", "start"]
