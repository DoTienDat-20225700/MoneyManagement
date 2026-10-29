from typing import Union
from django.http import JsonResponse


def custom_server_error_response(error_message: str = '', status_code=500):
    if 500 <= status_code < 600:
        return JsonResponse({'success': False, 'message': error_message}, status=status_code)
    raise ValueError("status_code for server error must be between 500 and 599.")


def custom_user_error_response(error_message: str = '', status_code=400):
    if 400 <= status_code < 500:
        return JsonResponse({'success': False, 'message': error_message}, status=status_code)
    raise ValueError("status_code for user error must be between 400 and 499.")


def custom_success_response(success_message: Union[str, dict] = '', status_code=200):
    if 200 <= status_code < 300:
        response = {'success': True, 'message': success_message}
        return JsonResponse(response, status=status_code)

    raise ValueError("status_code for success response must be between 200 and 299.")