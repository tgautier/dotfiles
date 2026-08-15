FROM ubuntu@sha256:561618e2c15bf2397621dd04f96926663a3b5616c189cf7e38db7e82f5c538ea

ARG TARGETARCH
ARG JUST_VERSION=1.58.0
ARG CHEZMOI_VERSION=2.72.0

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        ca-certificates \
        curl \
        git \
        jq \
        libsqlite3-0 \
        python3 \
        ruby \
        zsh \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "$TARGETARCH" in \
        amd64) \
            just_arch=x86_64; \
            just_sha256=4a5cc2f53e6f0f8c59092a6cc38291eb729d46a7dd95d3ae582008881b84931d; \
            chezmoi_arch=amd64; \
            chezmoi_sha256=0d6665b96c527d57fdc562bf19e808f80f48c2d977062c03e3e65c6b09eafbce \
            ;; \
        arm64) \
            just_arch=aarch64; \
            just_sha256=748237128c4c40cbdabc65e841d05ceba13cc23a91eaba395495894c1d9764df; \
            chezmoi_arch=arm64; \
            chezmoi_sha256=e79a27621256390f03166d3965e6a1946f983a096c4d90f02c43d2aa5b563728 \
            ;; \
        *) \
            echo "unsupported target architecture: $TARGETARCH" >&2; \
            exit 64 \
            ;; \
    esac; \
    just_archive="just-${JUST_VERSION}-${just_arch}-unknown-linux-musl.tar.gz"; \
    curl --fail --location --silent --show-error \
        "https://github.com/casey/just/releases/download/${JUST_VERSION}/${just_archive}" \
        --output "/tmp/${just_archive}"; \
    echo "${just_sha256}  /tmp/${just_archive}" | sha256sum --check --strict; \
    tar --extract --gzip --file "/tmp/${just_archive}" --directory /tmp just; \
    install --mode 0755 /tmp/just /usr/local/bin/just; \
    chezmoi_archive="chezmoi_${CHEZMOI_VERSION}_linux_${chezmoi_arch}.tar.gz"; \
    curl --fail --location --silent --show-error \
        "https://github.com/twpayne/chezmoi/releases/download/v${CHEZMOI_VERSION}/${chezmoi_archive}" \
        --output "/tmp/${chezmoi_archive}"; \
    echo "${chezmoi_sha256}  /tmp/${chezmoi_archive}" | sha256sum --check --strict; \
    tar --extract --gzip --file "/tmp/${chezmoi_archive}" --directory /tmp chezmoi; \
    install --mode 0755 /tmp/chezmoi /usr/local/bin/chezmoi; \
    rm -f "/tmp/${just_archive}" "/tmp/${chezmoi_archive}" /tmp/just /tmp/chezmoi

ENV LC_ALL=C.UTF-8
