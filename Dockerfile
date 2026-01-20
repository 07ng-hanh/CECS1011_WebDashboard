FROM python:3.14
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

RUN apt-get update && apt-get install -y valkey-server && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY --chown=user . /app
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]