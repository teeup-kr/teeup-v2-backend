"""
pytest fixtures for API testing
"""
import pytest
import requests

# API 기본 URL
BASE_URL = "http://localhost:8002/api/v1"

@pytest.fixture
def token():
    """로그인하여 토큰을 반환하는 fixture"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "leader@teeup.run",
        "password": "test123"
    })
    
    if response.status_code == 200:
        data = response.json()
        return data['access_token']
    else:
        pytest.skip("로그인 실패 - 테스트 데이터가 없습니다")

@pytest.fixture
def admin_token():
    """관리자 토큰을 반환하는 fixture"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@teeup.run",
        "password": "admin123"
    })
    
    if response.status_code == 200:
        data = response.json()
        return data['access_token']
    else:
        pytest.skip("관리자 로그인 실패 - 테스트 데이터가 없습니다")

@pytest.fixture
def club_id(token):
    """테스트용 클럽 ID를 반환하는 fixture"""
    # 기존 클럽이 있는지 확인
    response = requests.get(f"{BASE_URL}/clubs", headers={"Authorization": f"Bearer {token}"})
    
    if response.status_code == 200:
        clubs = response.json()
        if clubs and len(clubs) > 0:
            return clubs[0]['id']
    
    # 클럽이 없으면 생성
    club_data = {
        "name": "테스트 골프클럽",
        "type": "REGULAR",
        "description": "테스트용 골프클럽입니다",
        "member_count": 10,
        "location": "서울시 강남구",
        "contact_info": "010-1234-5678",
        "additional_info": "매주 토요일 정기 라운딩"
    }
    
    response = requests.post(f"{BASE_URL}/clubs", json=club_data, headers={"Authorization": f"Bearer {token}"})
    
    if response.status_code in [200, 201]:
        data = response.json()
        return data['id']
    else:
        pytest.skip("클럽 생성 실패")
