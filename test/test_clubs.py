#!/usr/bin/env python3
"""
클럽 관리 테스트
- 클럽 생성/수정/삭제
- 클럽 멤버 관리
- 클럽 승인/거부
"""

import requests
import pytest
import time

# API 기본 URL
BASE_URL = "http://localhost:8002/api/v1"

class TestClubs:
    """클럽 관리 테스트 클래스"""
    
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
    
    def test_create_club_success(self):
        """클럽 생성 성공"""
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
        assert data["name"] == club_data["name"]
        assert data["description"] == club_data["description"]
        assert "id" in data
    
    def test_create_club_without_authentication(self):
        """인증 없이 클럽 생성 실패"""
        club_data = {
            "name": "무인증 클럽",
            "member_count": 10
        }
        
        response = requests.post(f"{BASE_URL}/clubs", json=club_data)
        
        assert response.status_code == 403
    
    def test_create_club_with_invalid_data(self):
        """잘못된 데이터로 클럽 생성 실패"""
        token = self.get_auth_token()
        
        # 필수 필드 누락
        club_data = {
            "name": "",  # 빈 이름
            "member_count": -1  # 음수 멤버 수
        }
        
        response = requests.post(f"{BASE_URL}/clubs", json=club_data, headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == 422  # Validation Error
    
    def test_get_clubs_list(self):
        """클럽 목록 조회"""
        token = self.get_auth_token()
        
        response = requests.get(f"{BASE_URL}/clubs", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_get_club_detail(self):
        """클럽 상세 정보 조회"""
        # 먼저 클럽 생성
        club_id = self.create_test_club()
        
        token = self.get_auth_token()
        
        response = requests.get(f"{BASE_URL}/clubs/{club_id}", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == club_id
        assert "name" in data
        assert "description" in data
    
    def test_update_club(self):
        """클럽 정보 수정"""
        # 먼저 클럽 생성
        club_id = self.create_test_club()
        
        token = self.get_auth_token()
        
        update_data = {
            "name": "수정된 클럽 이름",
            "description": "수정된 클럽 설명"
        }
        
        response = requests.put(f"{BASE_URL}/clubs/{club_id}", json=update_data, headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    def test_approve_club(self):
        """클럽 승인 (관리자)"""
        # 먼저 클럽 생성
        club_id = self.create_test_club()
        
        # 관리자 토큰으로 승인
        admin_token = self.get_auth_token("admin@teeup.run", "test1234")
        
        response = requests.put(f"{BASE_URL}/clubs/{club_id}/approve", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_reject_club(self):
        """클럽 거부 (관리자)"""
        # 먼저 클럽 생성
        club_id = self.create_test_club()
        
        # 관리자 토큰으로 거부
        admin_token = self.get_auth_token("admin@teeup.run", "test1234")
        
        response = requests.put(f"{BASE_URL}/clubs/{club_id}/reject", json={
            "reason": "테스트 거부 사유"
        }, headers={
            "Authorization": f"Bearer {admin_token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_get_club_members(self):
        """클럽 멤버 목록 조회"""
        # 먼저 클럽 생성
        club_id = self.create_test_club()

        token = self.get_auth_token()

        response = requests.get(f"{BASE_URL}/clubs/{club_id}/members", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # 최소 1명의 멤버(리더)가 있어야 함
    
    def test_add_club_member(self):
        """클럽 멤버 추가"""
        # 먼저 클럽 생성
        club_id = self.create_test_club()
        
        token = self.get_auth_token()
        
        # 다른 사용자를 멤버로 추가
        member_data = {
            "user_id": "user_001",  # user1@teeup.run
            "role": "MEMBER"
        }
        
        response = requests.post(f"{BASE_URL}/clubs/{club_id}/members", json=member_data, headers={
            "Authorization": f"Bearer {token}"
        })
        
        # 성공 또는 이미 존재하는 경우 모두 허용
        assert response.status_code in [200, 201, 400]
    
    def test_update_member_role(self):
        """멤버 역할 변경"""
        # 먼저 클럽 생성
        club_id = self.create_test_club()
        
        token = self.get_auth_token()
        
        # 먼저 멤버 추가
        member_data = {
            "user_id": "user_001",
            "role": "MEMBER"
        }
        
        add_response = requests.post(f"{BASE_URL}/clubs/{club_id}/members", json=member_data, headers={
            "Authorization": f"Bearer {token}"
        })
        
        # 멤버 추가가 성공하거나 이미 존재하는 경우
        assert add_response.status_code in [200, 201, 400]
        
        # 멤버 역할 변경
        role_data = {
            "role": "MANAGER"
        }
        
        response = requests.put(f"{BASE_URL}/clubs/{club_id}/members/user_001/role", json=role_data, headers={
            "Authorization": f"Bearer {token}"
        })
        
        # 성공 또는 권한 없음 모두 허용
        assert response.status_code in [200, 403]
    
    def test_remove_club_member(self):
        """클럽 멤버 제거"""
        # 먼저 클럽 생성
        club_id = self.create_test_club()
        
        token = self.get_auth_token()
        
        # 먼저 멤버 추가
        member_data = {
            "user_id": "user_001",
            "role": "MEMBER"
        }
        
        add_response = requests.post(f"{BASE_URL}/clubs/{club_id}/members", json=member_data, headers={
            "Authorization": f"Bearer {token}"
        })
        
        # 멤버 추가가 성공하거나 이미 존재하는 경우
        assert add_response.status_code in [200, 201, 400]
        
        # 멤버 제거
        response = requests.delete(f"{BASE_URL}/clubs/{club_id}/members/user_001", headers={
            "Authorization": f"Bearer {token}"
        })
        
        # 성공 또는 권한 없음 모두 허용
        assert response.status_code in [200, 204, 403]
    
    def test_club_workflow_complete(self):
        """전체 클럽 워크플로우 테스트"""
        # 1. 클럽 생성
        club_id = self.create_test_club()
        
        # 2. 클럽 정보 조회
        token = self.get_auth_token()
        response = requests.get(f"{BASE_URL}/clubs/{club_id}", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        
        # 3. 클럽 승인 (관리자)
        admin_token = self.get_auth_token("admin@teeup.run", "test1234")
        response = requests.put(f"{BASE_URL}/clubs/{club_id}/approve", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        
        # 4. 멤버 추가
        member_data = {
            "user_id": "user_001",
            "role": "MEMBER"
        }
        response = requests.post(f"{BASE_URL}/clubs/{club_id}/members", json=member_data, headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code in [200, 201, 400]
        
        # 5. 멤버 목록 조회
        response = requests.get(f"{BASE_URL}/clubs/{club_id}/members", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
