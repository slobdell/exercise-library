from django.conf.urls import patterns, url

from .basic_navigation import views
# from .basic_navigation import api

urlpatterns = patterns('',
    url(r'^$', views.home, name='home'),
    url(r'^exercise/(?P<exercise_name>[-\w]+)/', views.exercise, name="exercise"),
    # url(r'^confirm/(?P<confirmation_code>\w+)/', views.confirm, name='confirm'),
)
