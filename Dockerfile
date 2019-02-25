FROM python:3-alpine

ADD . /app

RUN pip install gunicorn

RUN pip install -r /app/requirements.txt

ADD ./docker/entrypoint.sh /app/entrypoint.sh
ADD ./docker/gunicorn.conf /app/gunicorn.conf

WORKDIR /app

EXPOSE 80
ENTRYPOINT ["/app/entrypoint.sh"]
