FROM python:3.12-alpine

RUN addgroup -g 1001 lifeos && adduser -D -u 1001 -G lifeos lifeos

WORKDIR /app

COPY server.py .

USER lifeos

EXPOSE 8788

CMD ["python3", "server.py"]
