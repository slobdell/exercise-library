#!/bin/bash

git push heroku master
heroku run python manage.py collectstatic --noinput -i admin
