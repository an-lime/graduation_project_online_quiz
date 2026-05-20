import uuid


def generate_event_random_id():
    return int(uuid.uuid4().hex[:12], 16)
