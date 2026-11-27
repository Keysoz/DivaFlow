# Debian WSL2 rootfs for Diva Store (DEC-109, PROD-05).
#
# This image is never run as a container in production. It is exported with
# `docker export` and imported on Windows with `wsl --import`, so the store runs
# Docker Engine CE natively inside WSL2 without Docker Desktop.
#
# Build from the repository root:
#   docker build -f infra/images/wsl/Dockerfile -t diva-wsl-rootfs:latest .
#   docker create --name diva-rootfs diva-wsl-rootfs:latest /bin/true
#   docker export diva-rootfs -o dist/rootfs.tar
#   docker rm diva-rootfs

FROM debian:trixie

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Africa/Cairo

# Keep package postinst scripts from trying to start services during the build.
RUN printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d && chmod +x /usr/sbin/policy-rc.d

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        iproute2 \
        iptables \
        nftables \
        procps \
        less \
        nano \
        sudo \
        systemd \
        systemd-sysv \
        dbus \
        tzdata \
        locales \
        xz-utils \
        jq \
        rsync \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian trixie stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /usr/sbin/policy-rc.d

# Locales: English and Arabic (Egypt). Frappe itself is Unicode-safe; these are
# for the shell tools the owner may use during support.
RUN sed -i 's/^# *en_US.UTF-8/en_US.UTF-8/; s/^# *ar_EG.UTF-8/ar_EG.UTF-8/' /etc/locale.gen \
    && locale-gen

# WSL2 boots systemd so Docker starts with the distro.
RUN printf '[boot]\nsystemd=true\n\n[automount]\nenabled=true\n\n[interop]\nenabled=true\nappendWindowsPath=false\n\n[user]\ndefault=root\n' \
        > /etc/wsl.conf \
    && ln -sf /usr/share/zoneinfo/Africa/Cairo /etc/localtime \
    && echo "Africa/Cairo" > /etc/timezone

# Docker data lives on the WSL virtual disk. Rotate container logs so a long
# running store cannot fill the disk.
RUN mkdir -p /etc/docker \
    && printf '{\n  "log-driver": "json-file",\n  "log-opts": { "max-size": "10m", "max-file": "3" },\n  "storage-driver": "overlay2"\n}\n' \
        > /etc/docker/daemon.json

# Enable the units offline: systemctl cannot talk to systemd during a build.
RUN mkdir -p /etc/systemd/system/multi-user.target.wants \
    && ln -sf /lib/systemd/system/containerd.service /etc/systemd/system/multi-user.target.wants/containerd.service \
    && ln -sf /lib/systemd/system/docker.service /etc/systemd/system/multi-user.target.wants/docker.service

# The installer replaces .env and refreshes these files; they are baked in so a
# support engineer can inspect the exact versions shipped.
COPY --chown=root:root infra/compose/store.prod.yml /opt/diva/store.prod.yml
COPY --chown=root:root infra/compose/.env.prod.example /opt/diva/.env.example
COPY --chown=root:root scripts/wsl/boot.sh /opt/diva/boot.sh
COPY --chown=root:root scripts/wsl/restore.sh /opt/diva/restore.sh
COPY --chown=root:root scripts/wsl/diva-store.service /etc/systemd/system/diva-store.service

RUN chmod +x /opt/diva/boot.sh /opt/diva/restore.sh \
    && ln -sf /etc/systemd/system/diva-store.service /etc/systemd/system/multi-user.target.wants/diva-store.service

# Keep the image lean and reproducible.
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

CMD ["/bin/true"]
