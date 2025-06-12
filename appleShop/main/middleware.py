


class AdminMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        admin_paths = ['/admin/', '/admin_dashboard/']  # Защищенные пути
        
        if any(request.path.startswith(path) for path in admin_paths):
            if not (request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
                from django.shortcuts import redirect
                return redirect('login')