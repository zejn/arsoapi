from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'arsoapi.views.home', name='home'),
    # url(r'^arsoapi/', include('arsoapi.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    url(r'vreme/report/', 'arsoapi.views.report'),
    url(r'vreme/kml/radar.kml', 'arsoapi.views.kml_radar'),
    url(r'vreme/kml/toca.kml', 'arsoapi.views.kml_toca'),
    url(r'vreme/image/radar.png', 'arsoapi.views.image_radar'),
    url(r'vreme/align/radar.png', 'arsoapi.views.align_radar'),
    url(r'vreme/image/toca.png', 'arsoapi.views.image_toca'),
    url(r'vreme/image/aladin_(?P<offset>\d+).png', 'arsoapi.views.image_aladin'),
)
