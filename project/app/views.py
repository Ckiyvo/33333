import os
import json
import time
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Project, ProjectFile, FileProcessingResult
from algorithm.PDFProcess import PDFProcessor
from algorithm.ImageProcess import ImageProcessor
from algorithm.AudioProcess import AudioProcessor
from algorithm.VideoProcess import VideoProcessor
from PIL import Image



ALLOWED_FILE_EXTENSIONS = {
    'text': ['.txt', '.pdf', '.doc', '.docx', '.csv'],
    'image': ['.jpg', '.jpeg', '.png'],
    'audio': ['.wav', '.mp3'],
    'video': ['.aac', '.mp4']
}


@csrf_exempt
def upload_files(request, project_name):
    if request.method == 'POST':
        try:
            project = Project.objects.get(name=project_name)
            project_type = project.type
            print('当前项目类型为:',project_type)
            allowed_extensions = ALLOWED_FILE_EXTENSIONS.get(project_type, [])
            files = request.FILES.getlist('files')
            valid_files = []
            invalid_files = []

            for file in files:
                file_extension = os.path.splitext(file.name)[1].lower()
                if file_extension in allowed_extensions:
                    valid_files.append(file)
                else:
                    invalid_files.append(file.name)

            if invalid_files:
                return JsonResponse({'message': f'以下文件类型不允许上传: {", ".join(invalid_files)}'}, status=400)

            project_folder = os.path.join(settings.MEDIA_ROOT, project_name)
            os.makedirs(project_folder, exist_ok=True)

            for file in valid_files:
                file_path = os.path.join(project_folder, file.name)
                with open(file_path, 'wb+') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)
                ProjectFile.objects.create(
                    project=project,
                    file_name=file.name,
                    status='待处理',
                    local_path=file_path
                )

            return JsonResponse({'message': '文件上传成功'})
        except Project.DoesNotExist:
            return JsonResponse({'message': '项目不存在'}, status=404)

    return JsonResponse({'message': '无效的请求方法'}, status=400)

@csrf_exempt
def create_project(request):
    if request.method == 'POST':
        project_name = request.POST.get('project_name')
        project_type = request.POST.get('project_type')  # 获取项目类型
        if not project_name:
            return JsonResponse({'message': '项目名称不能为空'}, status=400)
        if not project_type:
            return JsonResponse({'message': '项目类型不能为空'}, status=400)

        # 处理文件上传
        files = request.FILES.getlist('files')
        valid_files = []
        invalid_files = []
        allowed_extensions = ALLOWED_FILE_EXTENSIONS.get(project_type.lower(), [])

        for file in files:
            file_extension = os.path.splitext(file.name)[1].lower()
            if file_extension in allowed_extensions:
                valid_files.append(file)
            else:
                invalid_files.append(file.name)

        if invalid_files:
            return JsonResponse({'message': f'以下文件类型不允许上传: {", ".join(invalid_files)}'}, status=400)

        project, created = Project.objects.get_or_create(name=project_name, type=project_type)  # 记录项目类型
        project_folder = os.path.join(settings.MEDIA_ROOT, project_name)
        os.makedirs(project_folder, exist_ok=True)

        file_list = []
        for index, file in enumerate(valid_files, start=1):
            file_path = os.path.join(project_folder, file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            # 创建 ProjectFile 实例
            project_file = ProjectFile.objects.create(
                project=project,
                file_name=file.name,
                status='待处理',
                local_path=file_path
            )
            file_list.append({
                'id': project_file.id,
                'name': file.name,
                'status': '待处理',
                'processed_at': '',
                'local_path': project_file.local_path
            })

        return JsonResponse({'message': '项目创建成功', 'files': file_list})

    return JsonResponse({'message': '无效的请求方法'}, status=400)

@csrf_exempt
# 传递 projects 信息
def get_projects(request):
    if request.method == 'GET':
        projects = Project.objects.all()
        project_list = []
        for project in projects:
            project_files = ProjectFile.objects.filter(project=project)
            file_list = []
            for file in project_files:
                file_list.append({
                    'id': file.id,
                    'name': file.file_name,
                    'status': file.status,
                    'processed_at': file.processed_at.strftime('%Y-%m-%d %H:%M:%S') if file.processed_at else '',
                    'local_path': file.local_path
                })
            project_data = {
                'id': project.id,
                'name': project.name,
                'type': project.type,  # 返回项目类型
                'created_at': project.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'files': file_list
            }
            project_list.append(project_data)
        return JsonResponse({'projects': project_list})
    return JsonResponse({'message': '无效的请求方法'}, status=400)

@csrf_exempt
# 显示项目列表具体信息
def get_project_list(request):
    projects = Project.objects.all()
    project_list = []
    for project in projects:
        project_data = {
            'id': project.id,
            'name': project.name,
            'type': project.type,  # 返回项目类型
            'created_at': project.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        project_list.append(project_data)
    return JsonResponse({'projects': project_list})

@csrf_exempt
def get_project_files(request, project_name):
    if request.method == 'GET':
        try:
            project = Project.objects.get(name=project_name)
            project_files = ProjectFile.objects.filter(project=project)
            file_list = []
            for file in project_files:
                file_list.append({
                    'id': file.id,
                    'name': file.file_name,
                    'status': file.status,
                    'processed_at': file.processed_at.strftime('%Y-%m-%d %H:%M:%S') if file.processed_at else '',
                    'local_path': file.local_path
                })
            return JsonResponse({'files': file_list, 'project_type': project.type})  # 返回项目类型
        except Project.DoesNotExist:
            return JsonResponse({'message': '项目不存在'}, status=404)
    return JsonResponse({'message': '无效的请求方法'}, status=400)


@csrf_exempt
def delete_project(request, project_name):
    if request.method == 'POST':
        try:
            project = Project.objects.get(name=project_name)
            # 删除项目下的所有文件
            project_files = ProjectFile.objects.filter(project=project)
            for file in project_files:
                file_path = file.local_path
                if os.path.exists(file_path):
                    os.remove(file_path)
                file.delete()
            # 删除项目
            project.delete()
            return JsonResponse({'message': '项目删除成功'})
        except Project.DoesNotExist:
            return JsonResponse({'message': '项目不存在'}, status=404)
    return JsonResponse({'message': '无效的请求方法'}, status=400)


@csrf_exempt
def delete_file(request, file_id):
    if request.method == 'POST':
        try:
            file = ProjectFile.objects.get(id=file_id)
            file.delete()
            return JsonResponse({'message': '文件删除成功'})
        except ProjectFile.DoesNotExist:
            return JsonResponse({'message': '文件不存在'}, status=404)
    return JsonResponse({'message': '无效的请求方法'}, status=400)

@csrf_exempt
def get_file_content(request, project_name, filename):
    try:
        project = Project.objects.get(name=project_name)
        project_file = ProjectFile.objects.get(project=project, file_name=filename)
        file_path = project_file.local_path
        file_extension = os.path.splitext(filename)[1].lower()

        # 获取文件内容
        with open(file_path, 'rb') as file:
            content = file.read()

        response = HttpResponse(content)
        if file_extension in ['.txt', '.csv']:
            response['Content-Type'] = 'text/plain'
        elif file_extension in ['.pdf']:
            response['Content-Type'] = 'application/pdf'
        elif file_extension in ['.jpg', '.jpeg', '.png']:
            response['Content-Type'] = f'image/{file_extension[1:]}'
        elif file_extension in ['.wav', '.mp3']:
            response['Content-Type'] = f'audio/{file_extension[1:]}'
        elif file_extension in ['.aac', '.mp4']:
            response['Content-Type'] = f'video/{file_extension[1:]}'

        return response
    except Project.DoesNotExist:
        return JsonResponse({'message': '项目不存在'}, status=404)
    except ProjectFile.DoesNotExist:
        return JsonResponse({'message': '文件不存在'}, status=404)
    

@csrf_exempt
def process_file(file_path):
    file_extension = os.path.splitext(file_path)[1].lower()
    result = {}
    if file_extension in ['.pdf']:
        processor = PDFProcessor()
        images = processor.pdf_to_image(file_path)
        detections = processor.layout_detection(images)
        results = processor.ocr_recognition(detections, images)
        json_data = []
        for res in results:
            json_result = {
                "layout_dets": res["layout_dets"],
                "page_info": res["page_info"]
            }
            json_data.append(json_result)
        result = json_data[0]
    elif file_extension in ['.jpg', '.jpeg', '.png']:
        processor = ImageProcessor()
        image = Image.open(file_path)
        detection_results = processor.object_detection(image)
        predicted_label = processor.classify_image(image)
        result = {
            "detection_results": detection_results,
            "predicted_label": predicted_label
        }
    elif file_extension in ['.wav', '.mp3']:
        processor = AudioProcessor()
        pre_audio = processor.preprocess_audio(file_path)
        transcription = processor.transcribe_speech(pre_audio)
        mfccs, spectral_centroids, spectral_bandwidth, spectral_flatness = processor.analyze_acoustic_features(pre_audio, sr=16000)
        result = {
            "transcription": transcription,
            "mfccs": mfccs.tolist(),  # 将 numpy 数组转换为列表以便 JSON 序列化
            "spectral_centroids": spectral_centroids.tolist(),
            "spectral_bandwidth": spectral_bandwidth.tolist(),
            "spectral_flatness": spectral_flatness.tolist()
        }
    elif file_extension in ['.aac', '.mp4']:
        processor = VideoProcessor()
        output_folder = r"F:\a\apaper\project\project\algorithm\result\output_frames"
        processor.preprocess_video(file_path, output_folder)
        action_result = processor.action_recognition(file_path)
        result = {
            "action_result": action_result
        }
    else:
        print(f"不支持的文件类型: {file_extension}")
    print(result)
    return result

@csrf_exempt
def batch_process_files(request):
    if request.method == 'GET':
        file_ids_str = request.GET.get('file_ids')
        if file_ids_str:
            file_ids = [int(id) for id in file_ids_str.split(',') if id.isdigit()]
        else:
            file_ids = []
        total_files = len(file_ids)
        processed_files = 0

        def event_stream():
            nonlocal processed_files
            for file_id in file_ids:
                try:
                    file = ProjectFile.objects.get(id=file_id)
                    file_path = file.local_path
                    result = process_file(file_path)

                    # 存储处理结果到数据库
                    FileProcessingResult.objects.update_or_create(
                        project_file=file,
                        defaults={'result': result}
                    )

                    # 更新文件状态为已处理
                    file.status = '已处理'
                    file.save()

                    processed_files += 1
                    yield f"data: {json.dumps({'type': 'progress', 'processed': processed_files})}\n\n"
                    time.sleep(1)  # 模拟处理时间
                except ProjectFile.DoesNotExist:
                    print(f'文件 ID 为 {file_id} 的文件不存在')

            yield f"data: {json.dumps({'type': 'finished'})}\n\n"

        return StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    return JsonResponse({'message': '无效的请求方法'}, status=400)

@csrf_exempt
def get_file_processing_result(request, project_name, filename):
    try:
        project = Project.objects.get(name=project_name)
        project_file = ProjectFile.objects.get(project=project, file_name=filename)
        processing_result = FileProcessingResult.objects.get(project_file=project_file)
        result = processing_result.result
        return JsonResponse(result, safe=False)  # 修改这里，将 safe 参数设为 False
    except Project.DoesNotExist:
        return JsonResponse({'message': '项目不存在'}, status=404)
    except ProjectFile.DoesNotExist:
        return JsonResponse({'message': '文件不存在'}, status=404)
    except FileProcessingResult.DoesNotExist:
        return JsonResponse({'message': '文件处理结果不存在'}, status=404)