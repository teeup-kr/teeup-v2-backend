#!/usr/bin/env python3
"""
모든 사용자(user1~user31)를 각 모임의 인원수 경우의 수에 맞게 참가신청하는 스크립트

48개 모임을 순서대로 나머지 0, 1, 2, 3 패턴으로 반복:
- 1-12번: 4,5,6,7,8,9,10,11,12,13,14,15명
- 13-24번: 16,17,18,19,20,21,22,23,24,25,26,27명
- 25-36번: 28,29,30,31,32,33,34,35,36,37,38,39명
- 37-48번: 40,41,42,43,44,45,46,47,48,49,50,51명

각 4개씩 나머지 0,1,2,3 패턴 반복 (예: 4명=나머지0, 5명=나머지1, 6명=나머지2, 7명=나머지3)

각 모임별로 필요한 인원수만큼만 참가신청합니다.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database import get_db
from models import Meeting, User, MeetingParticipant, ClubMembership, ParticipantType
from schemas import UserRole
from utils.permissions import MEMBERSHIP_ACTIVE_STATUSES
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_application_deadline_passed(application_deadline):
    """한국 시간 기준으로 신청 마감일이 지났는지 확인"""
    if not application_deadline:
        return False
    return datetime.now() > application_deadline

def get_required_participants(meeting_number):
    """
    모임 번호에 따라 필요한 참가자 수 계산
    48개 모임을 순서대로 나머지 0, 1, 2, 3 패턴으로 반복
    """
    # 1-12: 4,5,6,7,8,9,10,11,12,13,14,15
    # 13-24: 16,17,18,19,20,21,22,23,24,25,26,27
    # 25-36: 28,29,30,31,32,33,34,35,36,37,38,39
    # 37-48: 40,41,42,43,44,45,46,47,48,49,50,51
    
    # 12개씩 그룹으로 나누고, 각 그룹 내에서 1씩 증가
    group = (meeting_number - 1) // 12
    position_in_group = (meeting_number - 1) % 12
    
    # 각 그룹의 시작값: 4, 16, 28, 40
    base = 4 + (group * 12)
    
    # 그룹 내 위치에 따라 추가: 0,1,2,3,4,5,6,7,8,9,10,11
    # 결과: 나머지 0,1,2,3 패턴이 4개씩 반복
    return base + position_in_group

def apply_users_to_meetings():
    """user1~user31을 각 모임의 인원수 경우의 수에 맞게 참가신청"""
    
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
        
        # 모든 모임 조회 (테스트모임으로 시작하는 모임)
        meetings = db.query(Meeting).filter(
            Meeting.name.like("테스트모임%번")
        ).order_by(Meeting.id).all()
        
        # 모임이 없으면 모든 모임 조회 (디버깅용)
        if not meetings:
            print("⚠️  '테스트모임%번' 패턴으로 모임을 찾지 못했습니다.")
            print("   모든 모임을 조회합니다...")
            all_meetings = db.query(Meeting).order_by(Meeting.id).limit(10).all()
            if all_meetings:
                print("   최근 모임 목록:")
                for m in all_meetings:
                    print(f"     - {m.name} (ID: {m.id})")
        
        if not meetings:
            print("❌ 테스트 모임을 찾을 수 없습니다.")
            logger.error("테스트 모임을 찾을 수 없습니다.")
            db.close()
            return
        
        print(f"✅ 총 {len(meetings)}개의 모임을 찾았습니다.")
        logger.info(f"총 {len(meetings)}개의 모임을 찾았습니다.")
        
        total_success = 0
        total_failed = 0
        failed_details = []
        
        # 각 모임에 대해 필요한 인원수만큼만 참가신청
        for idx, meeting in enumerate(meetings, 1):
            meeting_success = 0
            meeting_failed = 0
            
            # 모임 번호 추출 (테스트모임01번 -> 1)
            try:
                meeting_number = int(meeting.name.replace("테스트모임", "").replace("번", ""))
            except:
                meeting_number = idx
            
            # 필요한 참가자 수 계산
            required_count = get_required_participants(meeting_number)
            
            # 사용자가 31명밖에 없으므로 최대 31명까지만
            required_count = min(required_count, len(users))
            
            print(f"\n📋 모임: {meeting.name} (ID: {meeting.id}) - 필요 인원: {required_count}명")
            logger.info(f"모임 처리 시작: {meeting.name} (ID: {meeting.id}) - 필요 인원: {required_count}명")
            
            # 모임 상태 확인
            if meeting.application_closed_early:
                print(f"  ⚠️  조기 마감된 모임입니다. 건너뜁니다.")
                logger.warning(f"조기 마감된 모임: {meeting.name}")
                continue
            
            if is_application_deadline_passed(meeting.application_deadline):
                print(f"  ⚠️  참가 신청 마감된 모임입니다. 건너뜁니다.")
                logger.warning(f"참가 신청 마감된 모임: {meeting.name}")
                continue
            
            # 현재 참가 신청된 인원 수 확인
            current_participants = db.query(MeetingParticipant).filter(
                MeetingParticipant.meeting_id == meeting.id
            ).count()
            
            # 이미 필요한 인원수만큼 참가신청이 되어 있으면 건너뜀
            if current_participants >= required_count:
                print(f"  ✅ 이미 {current_participants}명이 참가신청되어 있습니다. (필요: {required_count}명)")
                logger.info(f"이미 충분한 인원: {meeting.name} ({current_participants}/{required_count})")
                continue
            
            # 필요한 인원수만큼만 참가신청
            applied_count = 0
            needed_count = required_count - current_participants
            
            for user in users:
                if applied_count >= needed_count:
                    break
                
                try:
                    # 클럽 멤버십 확인
                    membership = db.query(ClubMembership).filter(
                        ClubMembership.club_id == meeting.club_id,
                        ClubMembership.user_id == user.id,
                        ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES)
                    ).first()
                    
                    if not membership:
                        logger.warning(f"클럽 멤버 아님: {user.email} -> {meeting.name}")
                        continue
                    
                    # 이미 참가 신청했는지 확인
                    existing_participant = db.query(MeetingParticipant).filter(
                        MeetingParticipant.meeting_id == meeting.id,
                        MeetingParticipant.user_id == user.id
                    ).first()
                    
                    if existing_participant:
                        logger.info(f"이미 참가 신청됨: {user.email} -> {meeting.name}")
                        continue
                    
                    # 참가자 수 확인 (max_participants 체크)
                    if meeting.max_participants is not None:
                        current_count = db.query(MeetingParticipant).filter(
                            MeetingParticipant.meeting_id == meeting.id
                        ).count()
                        
                        if current_count >= meeting.max_participants:
                            logger.warning(f"정원 마감: {meeting.name} ({current_count}/{meeting.max_participants})")
                            break  # 정원이 찼으므로 다음 모임으로
                    
                    # 참가자 생성
                    participant = MeetingParticipant(
                        meeting_id=meeting.id,
                        user_id=user.id,
                        participant_type=ParticipantType.USER
                    )
                    
                    db.add(participant)
                    db.commit()
                    db.refresh(participant)
                    
                    meeting_success += 1
                    total_success += 1
                    applied_count += 1
                    logger.info(f"✅ 참가 신청 성공: {user.email} -> {meeting.name} ({applied_count}/{needed_count})")
                    
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
                MeetingParticipant.meeting_id == meeting.id
            ).count()
            
            remainder = final_count % 4
            print(f"  ✅ 성공: {meeting_success}명 신청, 현재 총 {final_count}명 (나머지: {remainder})")
            
            if final_count < required_count:
                print(f"  ⚠️  부족: {final_count}명 / 필요: {required_count}명 (부족: {required_count - final_count}명)")
        
        # 결과 요약 출력
        print("\n" + "="*70)
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
    apply_users_to_meetings()
