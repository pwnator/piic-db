from django.conf import settings
from django.conf.urls import include, url, patterns
from django.conf.urls.static import static
from django.contrib import admin
from plotter import views

admin.site.site_header = 'PIIC administration'
admin.site.site_title = 'PIIC database admin'
admin.site.index_title = 'Database administration'

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testplot.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('plotter.urls')),
    url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.STATIC_ROOT, 'show_indexes' : settings.DEBUG}),
)

if not settings.DEBUG:
	urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
	urlpatterns += patterns(
		'django.views.static',
		(r'^media/(?P<path>.*)',
		'serve',
		{'document_root': settings.MEDIA_ROOT}), )
