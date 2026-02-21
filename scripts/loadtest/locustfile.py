from __future__ import annotations

# 실행:
#   locust -f scripts/loadtest/locustfile.py --host http://127.0.0.1:8200
# 테스트 요약:
#   - 일반 사용자/매니저 사용자 시나리오를 가중치 기반으로 반복 실행
#   - 온보딩(OAuth mock, 약관 동의, 프로필 완료) 후 클럽/모임/승인/점수 흐름 검증
#   - Locust UI/Headless 모두 동일 task 세트를 사용

import os
import sys
from itertools import count

from locust import HttpUser, between, task

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from lib.auth_provider import AuthProvider
from lib.scenario_manager import ManagerScenario
from lib.scenario_user import UserScenario
from lib.state_store import StateStore


RUN_ID = os.getenv("LOADTEST_RUN_ID", "local")
WAIT_MIN = float(os.getenv("LOADTEST_USER_WAIT_MIN", "1"))
WAIT_MAX = float(os.getenv("LOADTEST_USER_WAIT_MAX", "3"))

VU_COUNTER = count(1)
STATE_STORE = StateStore()


class BaseLoadUser(HttpUser):
    abstract = True
    wait_time = between(WAIT_MIN, WAIT_MAX)

    def on_start(self):
        """가상 사용자 시작 시 인증/약관/프로필 온보딩을 준비한다."""
        self.vu_id = next(VU_COUNTER)
        self.state = STATE_STORE.get_or_create(self.vu_id, RUN_ID)

        self.auth_provider = AuthProvider(self.client, RUN_ID)
        self.user_scenario = UserScenario(self.client, STATE_STORE)
        self.manager_scenario = ManagerScenario(self.client, STATE_STORE)

        if not self.auth_provider.ensure_bootstrap():
            return
        if not self.auth_provider.oauth_mock_login(self.state):
            return
        if not self.auth_provider.agree_required_terms(self.state):
            return
        self.auth_provider.complete_profile(self.state)


class RegularUser(BaseLoadUser):
    weight = 8

    @task(2)
    def browse_clubs(self):
        """클럽 목록 조회 트래픽을 생성한다."""
        if not self.state.access_token:
            return
        self.user_scenario.browse_clubs(self.state)

    @task(2)
    def join_club(self):
        """공유 클럽 가입 신청 트래픽을 생성한다."""
        if not self.state.access_token:
            return
        self.user_scenario.join_shared_club(self.state)

    @task(3)
    def browse_meetings(self):
        """모임 목록 조회 트래픽을 생성한다."""
        if not self.state.access_token:
            return
        self.user_scenario.browse_meetings(self.state)

    @task(2)
    def apply_meeting(self):
        """공유 모임 참가 신청 트래픽을 생성한다."""
        if not self.state.access_token:
            return
        self.user_scenario.apply_shared_meeting(self.state)

    @task(2)
    def sync_score_target(self):
        """점수 입력 대상 모임/참가자를 동기화한다."""
        if not self.state.access_token:
            return
        self.user_scenario.sync_score_target(self.state)

    @task(1)
    def submit_simple_score(self):
        """간단 점수 입력 트래픽을 생성한다."""
        if not self.state.access_token:
            return
        self.user_scenario.submit_simple_score(self.state)


class ManagerUser(BaseLoadUser):
    weight = 2

    def on_start(self):
        """매니저 사용자의 관리 클럽 상태를 초기화한다."""
        super().on_start()
        if self.state.access_token:
            self.manager_scenario.ensure_managed_club(self.state)

    @task(1)
    def refresh_club_role(self):
        """관리 클럽 권한/식별자 상태를 갱신한다."""
        if not self.state.access_token:
            return
        self.manager_scenario.ensure_managed_club(self.state)

    @task(2)
    def approve_members(self):
        """대기 멤버 승인 트래픽을 생성한다."""
        if not self.state.access_token:
            return
        self.manager_scenario.approve_pending_members(self.state)

    @task(1)
    def manage_workflow(self):
        """라운딩 워크플로우(생성~완료) 트래픽을 생성한다."""
        if not self.state.access_token:
            return
        self.manager_scenario.progress_workflow(self.state)
