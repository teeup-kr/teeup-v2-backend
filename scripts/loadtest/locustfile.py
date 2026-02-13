from __future__ import annotations

import os
import sys
from itertools import count

from locust import HttpUser, between, task

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from auth_provider import AuthProvider
from scenario_manager import ManagerScenario
from scenario_user import UserScenario
from state_store import StateStore


RUN_ID = os.getenv("LOADTEST_RUN_ID", "local")
WAIT_MIN = float(os.getenv("LOADTEST_USER_WAIT_MIN", "1"))
WAIT_MAX = float(os.getenv("LOADTEST_USER_WAIT_MAX", "3"))

VU_COUNTER = count(1)
STATE_STORE = StateStore()


class BaseLoadUser(HttpUser):
    abstract = True
    wait_time = between(WAIT_MIN, WAIT_MAX)

    def on_start(self):
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
        if not self.state.access_token:
            return
        self.user_scenario.browse_clubs(self.state)

    @task(2)
    def join_club(self):
        if not self.state.access_token:
            return
        self.user_scenario.join_shared_club(self.state)

    @task(3)
    def browse_meetings(self):
        if not self.state.access_token:
            return
        self.user_scenario.browse_meetings(self.state)

    @task(2)
    def apply_meeting(self):
        if not self.state.access_token:
            return
        self.user_scenario.apply_shared_meeting(self.state)

    @task(2)
    def sync_score_target(self):
        if not self.state.access_token:
            return
        self.user_scenario.sync_score_target(self.state)

    @task(1)
    def submit_simple_score(self):
        if not self.state.access_token:
            return
        self.user_scenario.submit_simple_score(self.state)


class ManagerUser(BaseLoadUser):
    weight = 2

    def on_start(self):
        super().on_start()
        if self.state.access_token:
            self.manager_scenario.ensure_managed_club(self.state)

    @task(1)
    def refresh_club_role(self):
        if not self.state.access_token:
            return
        self.manager_scenario.ensure_managed_club(self.state)

    @task(2)
    def approve_members(self):
        if not self.state.access_token:
            return
        self.manager_scenario.approve_pending_members(self.state)

    @task(1)
    def manage_workflow(self):
        if not self.state.access_token:
            return
        self.manager_scenario.progress_workflow(self.state)
