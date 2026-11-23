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

RUN pip install --no-cache-dir -e apps/rules-engine -e apps/diva_guard

# POS Next, pinned to the tag the patch set is written against. apply.sh refuses
# to run unless HEAD is the recorded base commit.
RUN git clone --depth 1 --branch v2.0.0 https://github.com/BrainWise-DEV/POSNext.git apps/pos_next \
    && bash infra/posnext-patches/apply.sh apps/pos_next

RUN pip install --no-cache-dir -e apps/pos_next

RUN bench build --app pos_next --app diva_desk --app custom_reports

EXPOSE 8080 9000

CMD ["bench", "start"]
