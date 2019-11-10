FROM node

EXPOSE 12345
RUN \
        apt-get update && \
        apt-get -y --no-install-recommends install \
                nodejs \
                python3-pip \
                python3-tornado && \
        rm -rf /var/lib/apt/lists/*

WORKDIR /elastipass/

COPY . /elastipass

RUN \
	pip3 install elasticsearch && \
	pip3 install elasticsearch_dsl && \
        npm install && \
        nodejs build/build.js && \
        rm -rf node_modules

ENTRYPOINT ["./elastipass.py", "--debug"]
