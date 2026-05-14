import random
import string

from django.contrib.sessions.models import Session
from django.utils import timezone


def terminate_all_user_sessions(user):
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        data = session.get_decoded()
        if str(data.get('_auth_user_id')) == str(user.id):
            session.delete()


def generate_verification_code(length=6):
    return ''.join(random.choices(string.digits, k=length))
