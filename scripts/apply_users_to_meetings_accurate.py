#!/usr/bin/env python3
"""
48개 모임에 대해 정확한 참가자 신청 스크립트
- 각 모임의 max_participants와 team_formation_mode 확인
- 성별 분리 모드: 남녀 균등 배분
- 성별 혼합 모드: 자유롭게 배분
- 핸디캡 분포 고려 (다양한 핸디캡 사용자 선택)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database import get_db
from models import Meeting, User, MeetingParticipant, ClubMembership, Gender
from schemas import MeetingParticipantStatus, MeetingParticipantRole, UserRole, TeamFormationMode
from utils.permissions import MEMBERSHIP_ACTIVE_STATUSES
from datetime import datetime
import logging
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_application_deadline_passed(application_deadline):
    """한국 시간 기준으로 신청 마감일이 지났는지 확인"""
    if not application_deadline:
        return False
    return datetime.now() > application_deadline

def is_gender_separated_mode(team_formation_mode):
    """성별 분리 모드인지 확인"""
    if not team_formation_mode:
        return False
    return team_formation_mode.startswith("GENDER_SEPARATED_")

def select_users_by_gender_and_handicap(
    db: Session,
    users: list,
    club_id: int,
    meeting_id: int,
    required_count: int,
    is_gender_separated: bool,
    target_gender: Gender = None
):
    """
    성별과 핸디캡을 고려하여 사용자 선택
    
    Args:
        db: 데이터베이스 세션
        users: 전체 사용자 리스트
        club_id: 클럽 ID
        meeting_id: 모임 ID
        required_count: 필요한 인원수
        is_gender_separated: 성별 분리 모드 여부
        target_gender: 목표 성별 (성별 분리 모드인 경우)
    
    Returns:
        선택된 사용자 리스트
    """
    selected_users = []
    
    # 클럽 멤버십이 있는 사용자만 필터링
    club_members = []
    for user in users:
        membership = db.query(ClubMembership).filter(
            ClubMembership.club_id == club_id,
            ClubMembership.user_id == user.id,
            ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES)
        ).first()
        
        if membership:
            # 이미 참가 신청했는지 확인
            existing = db.query(MeetingParticipant).filter(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user.id
            ).first()
            
            if not existing:
                club_members.append(user)
    
    if not club_members:
        logger.warning(f"클럽 멤버를 찾을 수 없습니다. club_id: {club_id}")
        return selected_users
    
    # 성별 분리 모드인 경우
    if is_gender_separated and target_gender:
        # 목표 성별에 맞는 사용자만 필터링
        gender_users = [u for u in club_members if u.gender == target_gender]
        
        if len(gender_users) < required_count:
            logger.warning(f"목표 성별({target_gender.value}) 사용자가 부족합니다: {len(gender_users)}명 / 필요: {required_count}명")
            return gender_users[:required_count]
        
        # 핸디캡 분포를 고려하여 선택
        # 핸디캡이 있는 사용자와 없는 사용자를 섞어서 선택
        users_with_handicap = [u for u in gender_users if u.handicap is not None or u.initial_handicap is not None]
        users_without_handicap = [u for u in gender_users if u.handicap is None and u.initial_handicap is None]
        
        # 핸디캡이 있는 사용자 우선 선택 (다양한 핸디캡 분포)
        if users_with_handicap:
            # 핸디캡 순서로 정렬하여 다양한 핸디캡 선택
            users_with_handicap.sort(key=lambda u: (u.handicap or u.initial_handicap or 0))
            
            # 핸디캡 분포를 고려하여 선택 (고핸디, 중핸디, 저핸디 섞기)
            selected_count = min(required_count, len(users_with_handicap))
            if selected_count > 0:
                # 균등하게 분포시키기 위해 인덱스 간격 계산
                step = max(1, len(users_with_handicap) // selected_count)
                selected_users = [users_with_handicap[i] for i in range(0, len(users_with_handicap), step)][:selected_count]
        
        # 부족한 인원은 핸디캡 없는 사용자로 채우기
        if len(selected_users) < required_count:
            needed = required_count - len(selected_users)
            selected_users.extend(users_without_handicap[:needed])
        
        # 정확히 필요한 인원수만큼만 선택
        selected_users = selected_users[:required_count]
        
    else:
        # 성별 혼합 모드: 자유롭게 배분
        if len(club_members) < required_count:
            logger.warning(f"사용자가 부족합니다: {len(club_members)}명 / 필요: {required_count}명")
            return club_members[:required_count]
        
        # 핸디캡 분포를 고려하여 선택
        users_with_handicap = [u for u in club_members if u.handicap is not None or u.initial_handicap is not None]
        users_without_handicap = [u for u in club_members if u.handicap is None and u.initial_handicap is None]
        
        # 핸디캡이 있는 사용자 우선 선택
        if users_with_handicap:
            users_with_handicap.sort(key=lambda u: (u.handicap or u.initial_handicap or 0))
            selected_count = min(required_count, len(users_with_handicap))
            if selected_count > 0:
                step = max(1, len(users_with_handicap) // selected_count)
                selected_users = [users_with_handicap[i] for i in range(0, len(users_with_handicap), step)][:selected_count]
        
        # 부족한 인원은 핸디캡 없는 사용자로 채우기
        if len(selected_users) < required_count:
            needed = required_count - len(selected_users)
            selected_users.extend(users_without_handicap[:needed])
        
        # 정확히 필요한 인원수만큼만 선택
        selected_users = selected_users[:required_count]
    
    return selected_users

def apply_users_to_meetings_accurate():
    """48개 모임에 대해 정확한 참가자 신청"""
    
    # 데이터베이스 세션 생성
    db = next(get_db())
    
    try:
        # user1~user31 조회 (관리자 제외)
        users = db.query(User).filter(
            User.email.like("user%@teeup.run"),
            User.role != UserRole.ADMIN,
            User.deleted_at.is_(None)
        ).order_by(User.email).all()
        
        if not users:
            print("❌ user1~user31 사용자를 찾을 수 없습니다.")
            logger.error("user1~user31 사용자를 찾을 수 없습니다.")
            db.close()
            return
        
        print(f"✅ 총 {len(users)}명의 사용자를 찾았습니다.")
        logger.info(f"총 {len(users)}명의 사용자를 찾았습니다.")
        
        # 성별별 사용자 수 확인
        male_users = [u for u in users if u.gender == Gender.MALE]
        female_users = [u for u in users if u.gender == Gender.FEMALE]
        other_users = [u for u in users if u.gender == Gender.OTHER or u.gender is None]
        
        print(f"  - 남성: {len(male_users)}명")
        print(f"  - 여성: {len(female_users)}명")
        print(f"  - 기타/없음: {len(other_users)}명")
        
        # 모든 모임 조회 (테스트모임으로 시작하는 모임)
        # 모임 이름 형식: "테스트모임01번 (A)" 또는 "테스트 모임01번 (A)"
        meetings = db.query(Meeting).filter(
            (Meeting.name.like("테스트모임%번%")) | 
            (Meeting.name.like("테스트 모임%번%"))
        ).order_by(Meeting.id).all()
        
        if not meetings:
            print("❌ 테스트 모임을 찾을 수 없습니다.")
            logger.error("테스트 모임을 찾을 수 없습니다.")
            db.close()
            return
        
        print(f"✅ 총 {len(meetings)}개의 모임을 찾았습니다.\n")
        logger.info(f"총 {len(meetings)}개의 모임을 찾았습니다.")
        
        total_success = 0
        total_failed = 0
        failed_details = []
        
        # 각 모임에 대해 정확한 참가자 신청
        for idx, meeting in enumerate(meetings, 1):
            meeting_success = 0
            meeting_failed = 0
            
            # 모임 정보 확인
            max_participants = meeting.max_participants
            team_formation_mode = meeting.team_formation_mode
            is_gender_separated = is_gender_separated_mode(team_formation_mode)
            
            if not max_participants:
                print(f"⚠️  모임 {idx}: {meeting.name} - max_participants가 설정되지 않았습니다. 건너뜁니다.")
                continue
            
            print(f"📋 모임 {idx}: {meeting.name} (ID: {meeting.id})")
            print(f"   - 최대 인원: {max_participants}명")
            print(f"   - 편성 모드: {team_formation_mode}")
            print(f"   - 성별 분리 모드: {is_gender_separated}")
            
            # 모임 상태 확인
            if meeting.application_closed_early:
                print(f"   ⚠️  조기 마감된 모임입니다. 건너뜁니다.\n")
                continue
            
            if is_application_deadline_passed(meeting.application_deadline):
                print(f"   ⚠️  참가 신청 마감된 모임입니다. 건너뜁니다.\n")
                continue
            
            # 현재 참가 신청된 인원 수 확인
            current_participants = db.query(MeetingParticipant).filter(
                MeetingParticipant.meeting_id == meeting.id,
                MeetingParticipant.status.in_([MeetingParticipantStatus.CONFIRMED, MeetingParticipantStatus.PENDING])
            ).count()
            
            # 필요한 인원수 계산: max_participants만큼 정확히 신청 (현재 참가자 수와 무관하게)
            # 각 모임은 4명부터 다양하게 설정되어 있음
            needed_count = max_participants - current_participants
            
            if needed_count <= 0:
                print(f"   ✅ 이미 충분한 인원이 참가 신청되어 있습니다. ({current_participants}/{max_participants}명)\n")
                continue
            
            # 최대 인원수 제한 확인
            if needed_count > max_participants:
                needed_count = max_participants
            
            print(f"   - 현재 참가자: {current_participants}명")
            print(f"   - 추가 필요: {needed_count}명")
            
            # 성별 분리 모드인 경우
            if is_gender_separated:
                # 남녀 균등 배분
                male_count = needed_count // 2
                female_count = needed_count - male_count
                
                print(f"   - 남성 필요: {male_count}명")
                print(f"   - 여성 필요: {female_count}명")
                
                # 남성 사용자 선택
                selected_males = select_users_by_gender_and_handicap(
                    db=db,
                    users=users,
                    club_id=meeting.club_id,
                    meeting_id=meeting.id,
                    required_count=male_count,
                    is_gender_separated=True,
                    target_gender=Gender.MALE
                )
                
                # 여성 사용자 선택
                selected_females = select_users_by_gender_and_handicap(
                    db=db,
                    users=users,
                    club_id=meeting.club_id,
                    meeting_id=meeting.id,
                    required_count=female_count,
                    is_gender_separated=True,
                    target_gender=Gender.FEMALE
                )
                
                selected_users = selected_males + selected_females
                
            else:
                # 성별 혼합 모드: 자유롭게 배분
                selected_users = select_users_by_gender_and_handicap(
                    db=db,
                    users=users,
                    club_id=meeting.club_id,
                    meeting_id=meeting.id,
                    required_count=needed_count,
                    is_gender_separated=False
                )
            
            # 참가 신청 생성
            for user in selected_users:
                try:
                    # 참가자 생성 (바로 확정 상태로)
                    participant = MeetingParticipant(
                        meeting_id=meeting.id,
                        user_id=user.id,
                        status=MeetingParticipantStatus.CONFIRMED,
                        role=MeetingParticipantRole.PARTICIPANT
                    )
                    
                    db.add(participant)
                    db.commit()
                    db.refresh(participant)
                    
                    meeting_success += 1
                    total_success += 1
                    logger.info(f"✅ 참가 신청 성공: {user.email} ({user.gender.value if user.gender else 'None'}) -> {meeting.name}")
                    
                except Exception as e:
                    meeting_failed += 1
                    total_failed += 1
                    failed_details.append({
                        "meeting": meeting.name,
                        "user": user.email,
                        "reason": str(e)
                    })
                    logger.error(f"참가 신청 실패: {user.email} -> {meeting.name}: {e}")
                    db.rollback()
                    continue
            
            # 최종 참가자 수 확인
            final_count = db.query(MeetingParticipant).filter(
                MeetingParticipant.meeting_id == meeting.id,
                MeetingParticipant.status.in_([MeetingParticipantStatus.CONFIRMED, MeetingParticipantStatus.PENDING])
            ).count()
            
            # 성별별 참가자 수 확인
            final_participants = db.query(MeetingParticipant).filter(
                MeetingParticipant.meeting_id == meeting.id,
                MeetingParticipant.status.in_([MeetingParticipantStatus.CONFIRMED, MeetingParticipantStatus.PENDING]),
                MeetingParticipant.is_guest == False
            ).all()
            
            male_participants = 0
            female_participants = 0
            for p in final_participants:
                if p.user:
                    if p.user.gender == Gender.MALE:
                        male_participants += 1
                    elif p.user.gender == Gender.FEMALE:
                        female_participants += 1
            
            remainder = final_count % 4
            print(f"   ✅ 성공: {meeting_success}명 신청, 현재 총 {final_count}명 (나머지: {remainder})")
            if is_gender_separated:
                print(f"      - 남성: {male_participants}명, 여성: {female_participants}명")
            
            if final_count < max_participants:
                print(f"   ⚠️  부족: {final_count}명 / 필요: {max_participants}명 (부족: {max_participants - final_count}명)")
            
            print()
        
        # 결과 요약 출력
        print("="*70)
        print(f"✅ 총 {total_success}건의 참가 신청이 성공했습니다!")
        print(f"❌ 총 {total_failed}건의 참가 신청이 실패했습니다!")
        print("="*70)
        
        if failed_details:
            print(f"\n⚠️  실패 상세 내역 (최대 20개):")
            print("-"*70)
            for i, detail in enumerate(failed_details[:20], 1):
                print(f"  {i}. {detail['meeting']} - {detail['user']}: {detail['reason']}")
            if len(failed_details) > 20:
                print(f"  ... 외 {len(failed_details) - 20}건")
            print("-"*70)
        
        logger.info(f"참가 신청 완료: 성공 {total_success}건, 실패 {total_failed}건")
        
    except Exception as e:
        logger.error(f"참가 신청 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"❌ 참가 신청 중 오류 발생: {e}")
        print(traceback.format_exc())
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    apply_users_to_meetings_accurate()

