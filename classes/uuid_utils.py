


try:
    from uuid import uuid7  # Python 3.12+ / 3.13
    new_id = uuid7
except ImportError:
    from uuid import uuid4
    new_id = uuid4