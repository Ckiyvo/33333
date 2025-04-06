from django.urls import path
from .views import upload_files, create_project, get_projects, get_project_files, get_project_list,delete_project,delete_file, get_file_content, batch_process_files, get_file_processing_result

urlpatterns = [
    path('api/upload_files/<str:project_name>/', upload_files, name='upload_files'),
    path('api/create_project/', create_project, name='create_project'),
    path('api/get_projects/', get_projects, name='get_projects'),
    path('api/get_project_files/<str:project_name>/', get_project_files, name='get_project_files'),
    path('api/get_project_list/', get_project_list, name='get_project_list'),
    path('api/delete_project/<str:project_name>/', delete_project, name='delete_project'),
    path('api/delete_file/<int:file_id>/', delete_file, name='delete_file'),
    path('api/get_file_content/<str:project_name>/<str:filename>/', get_file_content, name='get_file_content'),
    path('api/batch_process_files/', batch_process_files, name='batch_process_files'),
     path('api/get_file_processing_result/<str:project_name>/<str:filename>/', get_file_processing_result, name='get_file_processing_result'),
]