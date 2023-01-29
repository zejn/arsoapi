from django.urls import path, re_path

from . import views

urlpatterns = [
    # Examples:
    # url(r'^$', views.home', name='home),
    # url(r'^arsoapi/', include('arsoapi.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    path(r'vreme/report/', views.report),
    path(r'vreme/kml/radar.kml', views.kml_radar),
    path(r'vreme/kml/toca.kml', views.kml_toca),
    path(r'vreme/image/radar.png', views.image_radar),
    path(r'vreme/align/radar.png', views.align_radar),
    path(r'vreme/image/toca.png', views.image_toca),
    re_path(r'vreme/image/aladin_(?P<offset>\d+).png', views.image_aladin),
]
