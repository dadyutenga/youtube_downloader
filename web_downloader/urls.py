from django.urls import path
from . import views

app_name = 'web_downloader'

urlpatterns = [
    path('', views.index, name='index'),
    path('progress/<int:download_id>/', views.get_progress, name='get_progress'),
    path('download/<int:download_id>/', views.download_file, name='download_file'),
    path('delete/<int:download_id>/', views.delete_download, name='delete_download'),
]
