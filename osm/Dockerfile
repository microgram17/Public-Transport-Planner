FROM postgis/postgis:18-3.6

RUN apt-get update \
    && apt-get install --no-install-recommends --yes osm2pgsql osmium-tool \
    && rm -rf /var/lib/apt/lists/*

COPY import.sh /usr/local/bin/import-osm

RUN chmod +x /usr/local/bin/import-osm

ENTRYPOINT ["/usr/local/bin/import-osm"]
