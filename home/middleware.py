from urllib.parse import parse_qs, urlparse
from PIL import Image
import io
import os
from django.http import HttpResponse
from django.conf import settings

class ImageOptimizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if it's a media request with size parameter
        path = request.path_info
        if path.startswith('/media/hasil_deteksi/') and 'size' in request.GET:
            size_param = request.GET.get('size')
            
            # Get the file path on disk
            media_root = settings.MEDIA_ROOT
            rel_path = path.replace('/media/', '', 1)
            file_path = os.path.join(media_root, rel_path)
            
            # Check if file exists
            if os.path.exists(file_path):
                try:
                    # Resize the image
                    img = Image.open(file_path)
                    
                    if size_param == 'thumbnail':
                        # Thumbnail size (preserve aspect ratio)
                        img.thumbnail((300, 300), Image.LANCZOS)
                    elif 'x' in size_param:
                        # Custom size like 400x300
                        width, height = map(int, size_param.split('x'))
                        img = img.resize((width, height), Image.LANCZOS)
                    
                    # Convert to optimized JPEG format
                    output = io.BytesIO()
                    img.convert('RGB').save(output, format='JPEG', quality=85, optimize=True)
                    output.seek(0)
                    
                    # Return the optimized image
                    return HttpResponse(output.read(), content_type='image/jpeg')
                except Exception as e:
                    print(f"Image optimization error: {e}")
        
        return response 