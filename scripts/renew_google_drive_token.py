#!/usr/bin/env python3
"""
Google OAuth 토큰 발급/갱신 스크립트

사용법:
    python scripts/renew_google_token.py

스크립트 실행 후 브라우저에서 Google 로그인하고
리다이렉트된 URL을 복사해서 붙여넣으면 token.json이 생성됩니다.
"""
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
import requests
import urllib.parse

from urllib.parse import urlencode

# 필요한 Google API 스코프 (드라이브 업로드 전용)
SCOPES = ['https://www.googleapis.com/auth/drive.file']

TOKEN_FILE = settings.GOOGLE_TOKEN_FILE


def main():
    print("="*80)
    print("Google OAuth 토큰 발급/갱신")
    print("="*80)
    
    print("\n선택하세요:")
    print("1. 인증 URL 생성")
    print("2. 토큰 발급 (URL 받은 후)")
    print("3. 종료")
    
    choice = input("\n번호 입력: ").strip()
    
    if choice == "1":
        # 1단계: 인증 URL 생성
        params = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': settings.GOOGLE_DRIVE_REDIRECT_URI,
            'response_type': 'code',
            'scope': ' '.join(SCOPES),
            'access_type': 'offline',
            'prompt': 'consent'
        }
        auth_url = 'https://accounts.google.com/o/oauth2/auth?' + urlencode(params)
        
        print("\n" + "="*80)
        print("🔗 다음 URL을 브라우저에서 열어 Google 로그인하세요:")
        print("="*80)
        print(f"\n{auth_url}\n")
        print("="*80)
        print("📋 로그인 후 리다이렉트된 URL 전체를 복사하세요!")
        print("="*80)
        print("\n다음 단계: python scripts/renew_google_token.py 재실행 → 2번 선택\n")
        
    elif choice == "2":
        # 2단계: 토큰 발급
        print("\n리다이렉트된 URL 또는 code 값을 붙여넣으세요:")
        user_input = input().strip()
        
        # URL에서 code 추출 또는 직접 사용
        import re
        if user_input.startswith('http'):
            match = re.search(r'[?&]code=([^&\s]+)', user_input)
            if not match:
                print("❌ URL에서 code를 찾을 수 없습니다!")
                sys.exit(1)
            code = match.group(1)
            print(f"\n✅ Code 추출: {code[:30]}...")
        else:
            code = user_input
            print(f"\n✅ Code 입력: {code[:30]}...")
        
        print("⏳ 토큰 발급 중...")
        
        # HTTP POST로 토큰 요청
        data = {
            'code': code,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'redirect_uri': settings.GOOGLE_DRIVE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.post('https://oauth2.googleapis.com/token', data=data)
            
            if response.status_code == 200:
                result = response.json()
                
                # token.json 생성
                from google.oauth2.credentials import Credentials
                
                creds = Credentials(
                    token=result.get('access_token'),
                    refresh_token=result.get('refresh_token'),
                    token_uri='https://oauth2.googleapis.com/token',
                    client_id=settings.GOOGLE_CLIENT_ID,
                    client_secret=settings.GOOGLE_CLIENT_SECRET,
                    scopes=SCOPES
                )
                
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                
                print("\n✅ 토큰 발급 완료!")
                print(f"✅ Access Token: {result.get('access_token', '')[:50]}...")
                if result.get('refresh_token'):
                    print(f"✅ Refresh Token: {result.get('refresh_token', '')[:50]}...")
                print(f"\n🎉 성공! {TOKEN_FILE} 파일이 생성되었습니다!")
                print("\n서버를 재시작하세요: python main.py\n")
                
            else:
                print(f"\n❌ 실패!")
                print(f"응답 코드: {response.status_code}")
                print(f"응답 내용: {response.text}")
                print("\n💡 인증 코드가 만료되었을 수 있습니다. 1번부터 다시 시도하세요.\n")
                
        except Exception as e:
            print(f"\n❌ 에러: {e}")
            import traceback
            traceback.print_exc()
    
    elif choice == "3":
        print("종료합니다.")
        sys.exit(0)
    
    else:
        print("❌ 1, 2, 또는 3을 입력하세요.")


if __name__ == "__main__":
    main()

