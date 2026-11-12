FROM docker.io/miniflux/miniflux:2.3.5@sha256:8fd6c3c434ecc3d4083306f83e03c0bb74c632e0f8378da5ead7e1773b0b89c9 AS miniflux

FROM alpine:3.20

RUN apk add --no-cache \
    bash \
    postgresql16 \
    postgresql16-client \
    postgresql16-contrib \
    python3

COPY --from=miniflux /usr/bin/miniflux /usr/bin/miniflux

COPY start.sh /app/start.sh
COPY auth_proxy.py /app/auth_proxy.py
COPY auto_subscribe.py /app/auto_subscribe.py
RUN chmod +x /app/start.sh

RUN mkdir -p /run/postgresql && chown postgres:postgres /run/postgresql

EXPOSE 8080

CMD ["/app/start.sh"]
