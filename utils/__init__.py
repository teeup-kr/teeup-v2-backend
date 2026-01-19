# Utils package for backend utilities and scripts
import random
import string
import time
from datetime import datetime

def generate_id(prefix: str = "", length: int = 8) -> str:
    """고유 ID 생성"""
    if prefix:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        return f"{prefix}{timestamp}{random_str}"
    else:
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_cuid() -> str:
    """CUID(Collision-resistant Unique Identifier) 생성"""
    timestamp = str(int(time.time() * 1000))  # 밀리초 타임스탬프
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"c{timestamp}{random_part}"
