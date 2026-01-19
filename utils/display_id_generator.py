import random
from sqlalchemy.orm import Session
from models import Club

def generate_club_display_id(db: Session) -> str:
    """
    club-XXXXX 형태의 고유한 display_id 생성
    """
    while True:
        # 5자리 랜덤 숫자 생성
        random_number = random.randint(10000, 99999)
        display_id = f"club-{random_number}"
        
        # 중복 확인
        existing_club = db.query(Club).filter(Club.display_id == display_id).first()
        if not existing_club:
            return display_id

