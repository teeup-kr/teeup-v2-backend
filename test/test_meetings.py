#!/usr/bin/env python3
"""
미팅 관리 테스트
- 미팅 생성/수정/삭제
- 미팅 참가/나가기
- 참가자 관리
- 미팅 통계
"""

import requests
import pytest
import time
from datetime import datetime, timedelta

# API 기본 URL
BASE_URL = "http://localhost:8002/api/v1"

class TestMeetings:
    """미팅 관리 테스트 클래스"""
    
    def get_auth_token(self, email="leader1@teeup.run", password="test1234"):
        """인증 토큰 획득"""
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "email": email,
            "password": password
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def create_test_club(self):
        """테스트용 클럽 생성 헬퍼 메서드"""
        token = self.get_auth_token()
        
        club_data = {
            "name": f"테스트 골프클럽 {int(time.time())}",
            "description": "테스트용 골프클럽입니다",
            "member_count": 10,
            "location": "서울시 강남구",
            "contact_info": "010-1234-5678",
            "representative_name": "김테스트",
            "additional_info": "매주 토요일 정기 라운딩"
        }
        
        response = requests.post(f"{BASE_URL}/clubs", json=club_data, headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        return data["id"]
    
    def create_test_meeting(self, club_id=None):
        """테스트용 미팅 생성 헬퍼 메서드"""
        if club_id is None:
            club_id = self.create_test_club()
        
        token = self.get_auth_token()
        
        # 미래 시간으로 설정 (1시간 후)
        meeting_time = datetime.now() + timedelta(hours=1)
        
        meeting_data = {
            "name": f"테스트 라운딩 {int(time.time())}",
            "description": "테스트용 라운딩입니다",
            "location": "서울 골프클럽",
            "meeting_time": meeting_time.isoformat(),
            "tee_times": ["08:00", "08:10", "08:20"],
            "max_participants": 4,
            "meeting_type": "ROUND",
            "meeting_subtype": "REGULAR",
            "total_cost": 100000,
            "green_fee": 80000,
            "caddy_fee": 20000,
            "cart_fee": 0,
            "settlement_method": "EQUAL_SPLIT",
            "reservation_name": "김테스트"
        }
        
        response = requests.post(f"{BASE_URL}/meetings/", json=meeting_data, headers={
            "Authorization": f"Bearer {token}"
        }, params={"club_id": club_id})
        
        assert response.status_code == 200
        data = response.json()
        return data["id"]
    
    def test_create_meeting_success(self):
        """미팅 생성 성공"""
        club_id = self.create_test_club()
        token = self.get_auth_token()
        
        # 미래 시간으로 설정 (1시간 후)
        meeting_time = datetime.now() + timedelta(hours=1)
        
        meeting_data = {
            "name": f"테스트 라운딩 {int(time.time())}",
            "description": "테스트용 라운딩입니다",
            "location": "서울 골프클럽",
            "meeting_time": meeting_time.isoformat(),
            "tee_times": ["08:00", "08:10", "08:20"],
            "max_participants": 4,
            "meeting_type": "ROUND",
            "meeting_subtype": "REGULAR",
            "total_cost": 100000,
            "green_fee": 80000,
            "caddy_fee": 20000,
            "cart_fee": 0,
            "settlement_method": "EQUAL_SPLIT",
            "reservation_name": "김테스트"
        }
        
        response = requests.post(f"{BASE_URL}/meetings/", json=meeting_data, headers={
            "Authorization": f"Bearer {token}"
        }, params={"club_id": club_id})
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == meeting_data["name"]
        assert data["description"] == meeting_data["description"]
        assert "id" in data
    
    def test_create_meeting_without_authentication(self):
        """인증 없이 미팅 생성 실패"""
        meeting_data = {
            "name": "무인증 미팅",
            "meeting_time": (datetime.now() + timedelta(hours=1)).isoformat(),
            "tee_times": ["08:00"],
            "max_participants": 4,
            "meeting_subtype": "REGULAR",
            "settlement_method": "EQUAL_SPLIT"
        }
        
        response = requests.post(f"{BASE_URL}/meetings", json=meeting_data, params={"club_id": "test_club"})
        
        assert response.status_code == 403
    
    def test_create_meeting_with_invalid_data(self):
        """잘못된 데이터로 미팅 생성 실패"""
        club_id = self.create_test_club()
        token = self.get_auth_token()
        
        # 필수 필드 누락
        meeting_data = {
            "name": "",  # 빈 이름
            "max_participants": -1  # 음수 참가자 수
        }
        
        response = requests.post(f"{BASE_URL}/meetings/", json=meeting_data, headers={
            "Authorization": f"Bearer {token}"
        }, params={"club_id": club_id})
        
        assert response.status_code == 422  # Validation Error
    
    def test_get_meetings_list(self):
        """미팅 목록 조회"""
        token = self.get_auth_token()
        
        response = requests.get(f"{BASE_URL}/meetings", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_get_my_meetings(self):
        """내 미팅 목록 조회"""
        token = self.get_auth_token()
        
        response = requests.get(f"{BASE_URL}/meetings/my", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_get_meeting_detail(self):
        """미팅 상세 정보 조회"""
        # 먼저 미팅 생성
        meeting_id = self.create_test_meeting()
        
        token = self.get_auth_token()
        
        response = requests.get(f"{BASE_URL}/meetings/{meeting_id}", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == meeting_id
        assert "name" in data
        assert "description" in data
    
    def test_update_meeting(self):
        """미팅 정보 수정"""
        # 먼저 미팅 생성
        meeting_id = self.create_test_meeting()
        
        token = self.get_auth_token()
        
        update_data = {
            "name": "수정된 미팅 이름",
            "description": "수정된 미팅 설명"
        }
        
        response = requests.put(f"{BASE_URL}/meetings/{meeting_id}", json=update_data, headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    def test_delete_meeting(self):
        """미팅 삭제"""
        # 먼저 미팅 생성
        meeting_id = self.create_test_meeting()
        
        token = self.get_auth_token()
        
        # 미팅 삭제
        response = requests.delete(f"{BASE_URL}/meetings/{meeting_id}", headers={
            "Authorization": f"Bearer {token}"
        })
        
        # 삭제 성공 확인
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["success"] == True
        
        # 삭제된 미팅 조회 시 404 확인
        get_response = requests.get(f"{BASE_URL}/meetings/{meeting_id}", headers={
            "Authorization": f"Bearer {token}"
        })
        assert get_response.status_code == 404
    
    def test_get_club_meetings(self):
        """클럽별 미팅 목록 조회"""
        # 먼저 클럽과 미팅 생성
        club_id = self.create_test_club()
        self.create_test_meeting(club_id)

        token = self.get_auth_token()

        response = requests.get(f"{BASE_URL}/meetings/clubs/{club_id}", headers={
            "Authorization": f"Bearer {token}"
        })

        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_join_meeting(self):
        """미팅 참가"""
        # 먼저 미팅 생성
        meeting_id = self.create_test_meeting()
        
        token = self.get_auth_token()
        
        response = requests.post(f"{BASE_URL}/meetings/{meeting_id}/join", headers={
            "Authorization": f"Bearer {token}"
        })
        
        # 이미 참가한 경우(400) 또는 성공한 경우(200) 모두 허용
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
    
    def test_leave_meeting(self):
        """미팅 나가기"""
        # 먼저 미팅 생성 (생성자는 자동 참가됨)
        meeting_id = self.create_test_meeting()

        token = self.get_auth_token()

        # 생성자는 탈퇴할 수 없으므로 400 에러가 정상
        response = requests.delete(f"{BASE_URL}/meetings/{meeting_id}/leave", headers={
            "Authorization": f"Bearer {token}"
        })

        # 생성자는 탈퇴할 수 없으므로 400 에러가 예상됨
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "생성자" in data["detail"]
    
    def test_get_meeting_participants(self):
        """미팅 참가자 목록 조회"""
        # 먼저 미팅 생성
        meeting_id = self.create_test_meeting()
        
        token = self.get_auth_token()
        
        response = requests.get(f"{BASE_URL}/meetings/{meeting_id}/participants", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_remove_participant(self):
        """참가자 제거"""
        # 먼저 미팅 생성 (생성자는 자동 참가됨)
        meeting_id = self.create_test_meeting()

        token = self.get_auth_token()

        # 이미 참가되어 있으므로 바로 제거 테스트
        
        # 참가자 목록 조회하여 participant_id 획득
        participants_response = requests.get(f"{BASE_URL}/meetings/{meeting_id}/participants", headers={
            "Authorization": f"Bearer {token}"
        })
        assert participants_response.status_code == 200
        participants = participants_response.json()
        
        if participants:
            participant_id = participants[0]["id"]
            
            # 참가자 제거
            response = requests.delete(f"{BASE_URL}/meetings/{meeting_id}/participants/{participant_id}", headers={
                "Authorization": f"Bearer {token}"
            })
            
            # 성공 또는 권한 없음 모두 허용
            assert response.status_code in [200, 204, 403, 400]
    
    def test_meeting_workflow_complete(self):
        """전체 미팅 워크플로우 테스트"""
        # 1. 클럽 생성
        club_id = self.create_test_club()
        
        # 2. 미팅 생성
        meeting_id = self.create_test_meeting(club_id)
        
        # 3. 미팅 정보 조회
        token = self.get_auth_token()
        response = requests.get(f"{BASE_URL}/meetings/{meeting_id}", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        
        # 4. 미팅 참가 (생성자는 이미 참가되어 있음)
        response = requests.post(f"{BASE_URL}/meetings/{meeting_id}/join", headers={
            "Authorization": f"Bearer {token}"
        })
        # 이미 참가한 경우(400) 또는 성공한 경우(200) 모두 허용
        assert response.status_code in [200, 400]
        
        # 5. 참가자 목록 조회
        response = requests.get(f"{BASE_URL}/meetings/{meeting_id}/participants", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        
        # 6. 클럽별 미팅 목록 조회
        response = requests.get(f"{BASE_URL}/meetings/clubs/{club_id}", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        
        # 7. 내 미팅 목록 조회
        response = requests.get(f"{BASE_URL}/meetings/my", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
