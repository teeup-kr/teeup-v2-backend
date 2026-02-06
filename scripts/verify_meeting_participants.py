#!/usr/bin/env python3
"""
48개 모임의 참가자 수와 성별 배분을 가이드에 맞게 검증하는 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database import get_db
from models import Meeting, MeetingParticipant, User, Gender
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 가이드에 명시된 48개 모임 설정
GUIDE_CONFIG = [
    # Phase 1: 모임 1~18 (A~R)
    {"label": "A", "mode": "GENDER_SEPARATED_HANDICAP", "max_participants": 8},
    {"label": "B", "mode": "GENDER_SEPARATED_HANDICAP", "max_participants": 9},
    {"label": "C", "mode": "GENDER_SEPARATED_HANDICAP", "max_participants": 10},
    {"label": "D", "mode": "GENDER_SEPARATED_PREVIOUS_RECORD", "max_participants": 8},
    {"label": "E", "mode": "GENDER_SEPARATED_PREVIOUS_RECORD", "max_participants": 9},
    {"label": "F", "mode": "GENDER_SEPARATED_PREVIOUS_RECORD", "max_participants": 10},
    {"label": "G", "mode": "GENDER_SEPARATED_RANDOM", "max_participants": 8},
    {"label": "H", "mode": "GENDER_SEPARATED_RANDOM", "max_participants": 9},
    {"label": "I", "mode": "GENDER_SEPARATED_RANDOM", "max_participants": 10},
    {"label": "J", "mode": "GENDER_MIXED_HANDICAP", "max_participants": 8},
    {"label": "K", "mode": "GENDER_MIXED_HANDICAP", "max_participants": 9},
    {"label": "L", "mode": "GENDER_MIXED_HANDICAP", "max_participants": 10},
    {"label": "M", "mode": "GENDER_MIXED_PREVIOUS_RECORD", "max_participants": 8},
    {"label": "N", "mode": "GENDER_MIXED_PREVIOUS_RECORD", "max_participants": 9},
    {"label": "O", "mode": "GENDER_MIXED_PREVIOUS_RECORD", "max_participants": 10},
    {"label": "P", "mode": "GENDER_MIXED_RANDOM", "max_participants": 8},
    {"label": "Q", "mode": "GENDER_MIXED_RANDOM", "max_participants": 9},
    {"label": "R", "mode": "GENDER_MIXED_RANDOM", "max_participants": 10},
    # Phase 2: 모임 19~30
    {"label": "19", "mode": "GENDER_SEPARATED_HANDICAP", "max_participants": 12},
    {"label": "20", "mode": "GENDER_SEPARATED_HANDICAP", "max_participants": 15},
    {"label": "21", "mode": "GENDER_SEPARATED_PREVIOUS_RECORD", "max_participants": 12},
    {"label": "22", "mode": "GENDER_SEPARATED_PREVIOUS_RECORD", "max_participants": 16},
    {"label": "23", "mode": "GENDER_SEPARATED_RANDOM", "max_participants": 12},
    {"label": "24", "mode": "GENDER_SEPARATED_RANDOM", "max_participants": 15},
    {"label": "25", "mode": "GENDER_MIXED_HANDICAP", "max_participants": 12},
    {"label": "26", "mode": "GENDER_MIXED_HANDICAP", "max_participants": 16},
    {"label": "27", "mode": "GENDER_MIXED_PREVIOUS_RECORD", "max_participants": 12},
    {"label": "28", "mode": "GENDER_MIXED_PREVIOUS_RECORD", "max_participants": 15},
    {"label": "29", "mode": "GENDER_MIXED_RANDOM", "max_participants": 12},
    {"label": "30", "mode": "GENDER_MIXED_RANDOM", "max_participants": 16},
    # Phase 3: 모임 31~42
    {"label": "31", "mode": "GENDER_SEPARATED_HANDICAP", "max_participants": 11},
    {"label": "32", "mode": "GENDER_SEPARATED_PREVIOUS_RECORD", "max_participants": 11},
    {"label": "33", "mode": "GENDER_SEPARATED_RANDOM", "max_participants": 11},
    {"label": "34", "mode": "GENDER_MIXED_HANDICAP", "max_participants": 11},
    {"label": "35", "mode": "GENDER_MIXED_PREVIOUS_RECORD", "max_participants": 11},
    {"label": "36", "mode": "GENDER_MIXED_RANDOM", "max_participants": 11},
    {"label": "37", "mode": "GENDER_SEPARATED_HANDICAP", "max_participants": 13},
    {"label": "38", "mode": "GENDER_SEPARATED_PREVIOUS_RECORD", "max_participants": 13},
    {"label": "39", "mode": "GENDER_SEPARATED_RANDOM", "max_participants": 13},
    {"label": "40", "mode": "GENDER_MIXED_HANDICAP", "max_participants": 13},
    {"label": "41", "mode": "GENDER_MIXED_PREVIOUS_RECORD", "max_participants": 13},
    {"label": "42", "mode": "GENDER_MIXED_RANDOM", "max_participants": 13},
    # Phase 4: 모임 43~48
    {"label": "43", "mode": "GENDER_MIXED_HANDICAP", "max_participants": 4},
    {"label": "44", "mode": "GENDER_MIXED_HANDICAP", "max_participants": 5},
    {"label": "45", "mode": "GENDER_MIXED_HANDICAP", "max_participants": 17},
    {"label": "46", "mode": "GENDER_MIXED_HANDICAP", "max_participants": 18},
    {"label": "47", "mode": "GENDER_SEPARATED_HANDICAP", "max_participants": 20},
    {"label": "48", "mode": "GENDER_MIXED_HANDICAP", "max_participants": 20},
]

def is_gender_separated_mode(mode):
    """성별 분리 모드인지 확인"""
    return mode and mode.startswith("GENDER_SEPARATED_")

def verify_meetings():
    """모든 모임의 참가자 수와 성별 배분 검증"""
    db = next(get_db())
    
    try:
        # 모든 테스트 모임 조회
        meetings = db.query(Meeting).filter(
            (Meeting.name.like("테스트모임%번%")) | 
            (Meeting.name.like("테스트 모임%번%"))
        ).order_by(Meeting.id).all()
        
        if not meetings:
            print("❌ 테스트 모임을 찾을 수 없습니다.")
            return
        
        print(f"✅ 총 {len(meetings)}개의 모임을 찾았습니다.\n")
        print("="*80)
        print("모임별 참가자 수 및 성별 배분 검증 결과")
        print("="*80)
        
        issues = []
        correct_count = 0
        
        for idx, meeting in enumerate(meetings, 1):
            # 가이드 설정 찾기
            guide_config = None
            for config in GUIDE_CONFIG:
                if config["label"] in meeting.name:
                    guide_config = config
                    break
            
            if not guide_config:
                print(f"⚠️  모임 {idx}: {meeting.name} - 가이드 설정을 찾을 수 없습니다.")
                continue
            
            # 참가자 조회
            participants = db.query(MeetingParticipant).filter(
                MeetingParticipant.meeting_id == meeting.id,
                MeetingParticipant.user_id.isnot(None)
            ).all()
            
            # 성별별 집계
            male_count = 0
            female_count = 0
            for p in participants:
                if p.user and p.user.gender:
                    if p.user.gender == Gender.MALE:
                        male_count += 1
                    elif p.user.gender == Gender.FEMALE:
                        female_count += 1
            
            total_count = len(participants)
            expected_count = guide_config["max_participants"]
            is_separated = is_gender_separated_mode(meeting.team_formation_mode)
            
            # 검증
            status_icon = "✅"
            issues_found = []
            
            # 1. 인원수 검증
            if total_count != expected_count:
                status_icon = "❌"
                issues_found.append(f"인원수 불일치: {total_count}명 / 예상: {expected_count}명")
            
            # 2. 성별 분리 모드인 경우 남녀 균등 배분 검증
            if is_separated:
                # 남녀 차이가 1명 이내여야 함
                gender_diff = abs(male_count - female_count)
                if gender_diff > 1:
                    status_icon = "⚠️"
                    issues_found.append(f"성별 불균형: 남{male_count}명 / 여{female_count}명 (차이: {gender_diff}명)")
                
                # 최소 인원 확인
                if male_count < 2 or female_count < 2:
                    status_icon = "❌"
                    issues_found.append(f"성별 최소 인원 부족: 남{male_count}명 / 여{female_count}명 (최소 2명 필요)")
            
            # 출력
            mode_short = meeting.team_formation_mode.replace("GENDER_", "").replace("_", " ")[:20] if meeting.team_formation_mode else "N/A"
            print(f"\n{status_icon} 모임 {idx}: {meeting.name} ({guide_config['label']})")
            print(f"   모드: {mode_short}")
            print(f"   인원: {total_count}명 / 예상: {expected_count}명")
            if is_separated:
                print(f"   성별: 남{male_count}명 / 여{female_count}명")
            else:
                print(f"   성별: 남{male_count}명 / 여{female_count}명 (혼합 모드)")
            
            if issues_found:
                for issue in issues_found:
                    print(f"   ⚠️  {issue}")
                issues.append({
                    "meeting": meeting.name,
                    "label": guide_config["label"],
                    "issues": issues_found
                })
            else:
                correct_count += 1
        
        # 요약
        print("\n" + "="*80)
        print("검증 요약")
        print("="*80)
        print(f"✅ 정상: {correct_count}개 모임")
        print(f"⚠️  문제: {len(issues)}개 모임")
        
        if issues:
            print("\n문제가 있는 모임:")
            for issue in issues:
                print(f"  - {issue['meeting']} ({issue['label']}): {', '.join(issue['issues'])}")
        
    except Exception as e:
        logger.error(f"검증 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"❌ 검증 중 오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_meetings()
