#!/usr/bin/env python3
"""
테스트 모임 48개 생성 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database import get_db
from models import Meeting, Club
from schemas import MeetingType, MeetingSubtype, SettlementMethod, MeetingStatus, TeamFormationMode
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 48개 모임별 팀 편성 테스트 계획
MEETING_CONFIGS = [
    # Phase 1: 전체 테스트 계획 (모임 1~18, A~R)
    # 성별 분리 + 핸디캡 기준
    {"mode": TeamFormationMode.GENDER_SEPARATED_HANDICAP, "max_participants": 8, "label": "A"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_HANDICAP, "max_participants": 9, "label": "B"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_HANDICAP, "max_participants": 10, "label": "C"},
    # 성별 분리 + 직전대회 성적 기준
    {"mode": TeamFormationMode.GENDER_SEPARATED_PREVIOUS_RECORD, "max_participants": 8, "label": "D"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_PREVIOUS_RECORD, "max_participants": 9, "label": "E"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_PREVIOUS_RECORD, "max_participants": 10, "label": "F"},
    # 성별 분리 + 랜덤
    {"mode": TeamFormationMode.GENDER_SEPARATED_RANDOM, "max_participants": 8, "label": "G"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_RANDOM, "max_participants": 9, "label": "H"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_RANDOM, "max_participants": 10, "label": "I"},
    # 성별 혼합 + 핸디캡 기준
    {"mode": TeamFormationMode.GENDER_MIXED_HANDICAP, "max_participants": 8, "label": "J"},
    {"mode": TeamFormationMode.GENDER_MIXED_HANDICAP, "max_participants": 9, "label": "K"},
    {"mode": TeamFormationMode.GENDER_MIXED_HANDICAP, "max_participants": 10, "label": "L"},
    # 성별 혼합 + 직전대회 성적 기준
    {"mode": TeamFormationMode.GENDER_MIXED_PREVIOUS_RECORD, "max_participants": 8, "label": "M"},
    {"mode": TeamFormationMode.GENDER_MIXED_PREVIOUS_RECORD, "max_participants": 9, "label": "N"},
    {"mode": TeamFormationMode.GENDER_MIXED_PREVIOUS_RECORD, "max_participants": 10, "label": "O"},
    # 성별 혼합 + 랜덤
    {"mode": TeamFormationMode.GENDER_MIXED_RANDOM, "max_participants": 8, "label": "P"},
    {"mode": TeamFormationMode.GENDER_MIXED_RANDOM, "max_participants": 9, "label": "Q"},
    {"mode": TeamFormationMode.GENDER_MIXED_RANDOM, "max_participants": 10, "label": "R"},
    # Phase 2: 추가 인원수 테스트 (모임 19~30)
    # 성별 분리 모드
    {"mode": TeamFormationMode.GENDER_SEPARATED_HANDICAP, "max_participants": 12, "label": "19"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_HANDICAP, "max_participants": 15, "label": "20"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_PREVIOUS_RECORD, "max_participants": 12, "label": "21"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_PREVIOUS_RECORD, "max_participants": 16, "label": "22"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_RANDOM, "max_participants": 12, "label": "23"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_RANDOM, "max_participants": 15, "label": "24"},
    # 성별 혼합 모드
    {"mode": TeamFormationMode.GENDER_MIXED_HANDICAP, "max_participants": 12, "label": "25"},
    {"mode": TeamFormationMode.GENDER_MIXED_HANDICAP, "max_participants": 16, "label": "26"},
    {"mode": TeamFormationMode.GENDER_MIXED_PREVIOUS_RECORD, "max_participants": 12, "label": "27"},
    {"mode": TeamFormationMode.GENDER_MIXED_PREVIOUS_RECORD, "max_participants": 15, "label": "28"},
    {"mode": TeamFormationMode.GENDER_MIXED_RANDOM, "max_participants": 12, "label": "29"},
    {"mode": TeamFormationMode.GENDER_MIXED_RANDOM, "max_participants": 16, "label": "30"},
    # Phase 3: 각 모드별 반복 테스트 (모임 31~42)
    {"mode": TeamFormationMode.GENDER_SEPARATED_HANDICAP, "max_participants": 11, "label": "31"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_PREVIOUS_RECORD, "max_participants": 11, "label": "32"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_RANDOM, "max_participants": 11, "label": "33"},
    {"mode": TeamFormationMode.GENDER_MIXED_HANDICAP, "max_participants": 11, "label": "34"},
    {"mode": TeamFormationMode.GENDER_MIXED_PREVIOUS_RECORD, "max_participants": 11, "label": "35"},
    {"mode": TeamFormationMode.GENDER_MIXED_RANDOM, "max_participants": 11, "label": "36"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_HANDICAP, "max_participants": 13, "label": "37"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_PREVIOUS_RECORD, "max_participants": 13, "label": "38"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_RANDOM, "max_participants": 13, "label": "39"},
    {"mode": TeamFormationMode.GENDER_MIXED_HANDICAP, "max_participants": 13, "label": "40"},
    {"mode": TeamFormationMode.GENDER_MIXED_PREVIOUS_RECORD, "max_participants": 13, "label": "41"},
    {"mode": TeamFormationMode.GENDER_MIXED_RANDOM, "max_participants": 13, "label": "42"},
    # Phase 4: 엣지 케이스 테스트 (모임 43~48)
    {"mode": TeamFormationMode.GENDER_MIXED_HANDICAP, "max_participants": 4, "label": "43"},
    {"mode": TeamFormationMode.GENDER_MIXED_HANDICAP, "max_participants": 5, "label": "44"},
    {"mode": TeamFormationMode.GENDER_MIXED_HANDICAP, "max_participants": 17, "label": "45"},
    {"mode": TeamFormationMode.GENDER_MIXED_HANDICAP, "max_participants": 18, "label": "46"},
    {"mode": TeamFormationMode.GENDER_SEPARATED_HANDICAP, "max_participants": 20, "label": "47"},
    {"mode": TeamFormationMode.GENDER_MIXED_HANDICAP, "max_participants": 20, "label": "48"},
]

def create_test_meetings(): 
    """테스트 모임 48개 생성"""
    
    # 데이터베이스 세션 생성
    db = next(get_db())
    
    # 클럽 조회 - 먼저 지정된 display_id로 찾기
    club_display_id = "cmiy6k1oe0001ldau4p"
    club = db.query(Club).filter(
        Club.display_id == club_display_id,
        Club.deleted_at.is_(None)
    ).first()
    
    if not club:
        # display_id로 찾지 못했으면 숫자로 변환 가능한지 확인 후 id로 조회
        try:
            club_id_int = int(club_display_id)
            club = db.query(Club).filter(
                Club.id == club_id_int,
                Club.deleted_at.is_(None)
            ).first()
        except ValueError:
            club = None
    
    if not club:
        # 모든 클럽 목록 조회
        print(f"❌ 클럽을 찾을 수 없습니다: {club_display_id}")
        print("\n📋 사용 가능한 클럽 목록:")
        print("-" * 70)
        all_clubs = db.query(Club).filter(Club.deleted_at.is_(None)).all()
        if all_clubs:
            print(f"{'ID':<6} {'display_id':<25} {'이름':<30}")
            print("-" * 70)
            for c in all_clubs:
                display_id_str = c.display_id if c.display_id else "(없음)"
                print(f"{c.id:<6} {display_id_str:<25} {c.name:<30}")
            print("-" * 70)
            print(f"\n💡 첫 번째 클럽을 자동으로 사용합니다...")
            
            # 자동으로 첫 번째 클럽 사용
            if all_clubs:
                club = all_clubs[0]
                print(f"✅ 클럽 자동 선택: {club.name} (ID: {club.id}, display_id: {club.display_id})")
        else:
            print("  사용 가능한 클럽이 없습니다.")
            logger.error(f"클럽을 찾을 수 없습니다: {club_display_id}")
            db.close()
            return
    
    print(f"✅ 클럽 조회 성공: {club.name} (ID: {club.id})")
    logger.info(f"클럽 조회 성공: {club.name} (ID: {club.id})")
    
    created_meetings = []
    failed_meetings = []
    
    try:
        for i in range(1, 49):
            try:
                # 모임 설정 가져오기
                config = MEETING_CONFIGS[i - 1]
                formation_mode = config["mode"]
                max_participants = config["max_participants"]
                label = config["label"]
                
                # 모임 데이터 생성
                meeting_time = datetime(2025, 12, 14, 18, 0) + timedelta(days=i-1)
                deadline_time = datetime(2025, 12, 11, 15, 0) + timedelta(days=i-1)
                
                meeting_name = f"테스트모임{i:02d}번 ({label})"
                
                # 기존 모임 확인 및 삭제
                existing_meeting = db.query(Meeting).filter(
                    Meeting.name == meeting_name,
                    Meeting.club_id == club.id
                ).first()
                
                if existing_meeting:
                    logger.info(f"기존 모임 삭제: {meeting_name}")
                    db.delete(existing_meeting)
                    db.commit()
                
                # 편성 모드 라벨 생성
                mode_labels = {
                    TeamFormationMode.GENDER_SEPARATED_HANDICAP: "성별 분리 + 핸디캡 기준",
                    TeamFormationMode.GENDER_SEPARATED_PREVIOUS_RECORD: "성별 분리 + 직전대회 성적 기준",
                    TeamFormationMode.GENDER_SEPARATED_RANDOM: "성별 분리 + 랜덤",
                    TeamFormationMode.GENDER_MIXED_HANDICAP: "성별 혼합 + 핸디캡 기준",
                    TeamFormationMode.GENDER_MIXED_PREVIOUS_RECORD: "성별 혼합 + 직전대회 성적 기준",
                    TeamFormationMode.GENDER_MIXED_RANDOM: "성별 혼합 + 랜덤",
                }
                mode_label = mode_labels.get(formation_mode, str(formation_mode.value))
                
                # 모임 생성
                meeting = Meeting(
                    name=meeting_name,
                    description=f"테스트모임{i:02d}번 ({label}) - {mode_label}, 최대 {max_participants}명",
                    location=f"케이스{i:02d} CC",
                    meeting_time=meeting_time,
                    tee_times=["18:10"],
                    max_participants=max_participants,
                    meeting_type=MeetingType.ROUND,
                    meeting_subtype=MeetingSubtype.REGULAR,
                    settlement_method=SettlementMethod.EQUAL_SPLIT,
                    course_name=f"케이스{i:02d} CC",
                    hole_count=18,
                    reservation_name=f"트리플에스{i:02d}",
                    application_deadline=deadline_time,
                    team_formation_mode=formation_mode.value,  # Enum 값을 문자열로 변환
                    team_size=4,
                    club_id=club.id,
                    status=MeetingStatus.SCHEDULED
                )
                
                db.add(meeting)
                db.commit()
                db.refresh(meeting)
                
                created_meetings.append({
                    "number": i,
                    "name": meeting_name,
                    "label": label,
                    "mode": mode_label,
                    "max_participants": max_participants,
                    "meeting_time": meeting_time.strftime("%Y-%m-%d %H:%M"),
                    "location": f"케이스{i:02d} CC",
                    "id": meeting.id,
                    "uuid": meeting.uuid
                })
                
                logger.info(f"✅ 모임 생성 성공: {meeting_name} (ID: {meeting.id}, 모드: {mode_label}, 인원: {max_participants}명)")
                print(f"✅ 모임{i:02d} ({label}) 생성 완료: {meeting_name} - {mode_label}, {max_participants}명 ({meeting_time.strftime('%Y-%m-%d %H:%M')})")
                
            except Exception as e:
                logger.error(f"모임{i:02d} 생성 실패: {e}")
                print(f"❌ 모임{i:02d} 생성 실패: {e}")
                failed_meetings.append((i, str(e)))
                db.rollback()
                continue
        
        # 결과 요약 출력
        print("\n" + "="*100)
        print(f"✅ 총 {len(created_meetings)}개의 모임이 성공적으로 생성되었습니다!")
        print("="*100)
        print("\n생성된 모임 목록:")
        print("-"*100)
        print(f"{'번호':<6} {'라벨':<6} {'모임명':<25} {'편성 모드':<30} {'인원':<8} {'일시':<20} {'ID':<10}")
        print("-"*100)
        for meeting in created_meetings:
            print(f"{meeting['number']:<6} {meeting['label']:<6} {meeting['name']:<25} {meeting['mode']:<30} {meeting['max_participants']:<8} {meeting['meeting_time']:<20} {meeting['id']:<10}")
        print("-"*100)
        
        # 편성 모드별 통계 출력
        print("\n편성 모드별 통계:")
        print("-"*100)
        mode_stats = {}
        for meeting in created_meetings:
            mode = meeting['mode']
            if mode not in mode_stats:
                mode_stats[mode] = 0
            mode_stats[mode] += 1
        
        for mode, count in sorted(mode_stats.items()):
            print(f"  {mode}: {count}개")
        print("-"*100)
        
        if failed_meetings:
            print(f"\n⚠️  {len(failed_meetings)}개의 모임 생성 실패:")
            for meeting_num, error in failed_meetings:
                print(f"  - 모임{meeting_num:02d}: {error}")
        
        logger.info(f"테스트 모임 생성 완료: 성공 {len(created_meetings)}개, 실패 {len(failed_meetings)}개")
        
    except Exception as e:
        logger.error(f"테스트 모임 생성 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"❌ 테스트 모임 생성 중 오류 발생: {e}")
        print(traceback.format_exc())
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_meetings()

