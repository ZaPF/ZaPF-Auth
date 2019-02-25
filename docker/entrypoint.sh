#!/bin/sh

echo "environment:"
env

echo "Settings:"
cat $AUTH_SETTINGS

./manage.py sanity
gunicorn -c gunicorn.conf manage:app
