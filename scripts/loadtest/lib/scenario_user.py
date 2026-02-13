from __future__ import annotations

# 실행: 직접 실행하지 않음.
# 사용: scripts/loadtest/locustfile.py, scripts/loadtest/run_single_test_profile.py

from .state_store import StateStore, UserRuntimeState


class UserScenario:
    def __init__(self, client, state_store: StateStore):
        self.client = client
        self.state_store = state_store

    @staticmethod
    def _headers(token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def browse_clubs(self, state: UserRuntimeState) -> None:
        self.client.get(
            "/api/v1/clubs?page=1&limit=20",
            headers=self._headers(state.access_token),
            name="clubs.list",
        )

    def join_shared_club(self, state: UserRuntimeState) -> None:
        shared_club = self.state_store.get_random_club()
        if shared_club is not None:
            club_id = shared_club.display_id
        else:
            response = self.client.get(
                "/api/v1/clubs?page=1&limit=20",
                headers=self._headers(state.access_token),
                name="clubs.list_for_join",
            )
            if response.status_code != 200:
                return
            data = response.json()
            clubs = data["data"]
            if not clubs:
                return
            club = clubs[0]
            club_id = club["display_id"] if club["display_id"] else str(club["id"])

        with self.client.post(
            f"/api/v1/clubs/{club_id}/join",
            headers=self._headers(state.access_token),
            name="clubs.join",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                state.joined_club_id = str(club_id)
                response.success()
                return
            if response.status_code == 400:
                # 이미 가입/신청 상태는 반복 시나리오에서 정상 케이스
                response.success()
                return
            response.failure(f"join failed: {response.status_code} {response.text}")

    def browse_meetings(self, state: UserRuntimeState) -> None:
        self.client.get(
            "/api/v1/meetings?page=1&limit=20",
            headers=self._headers(state.access_token),
            name="meetings.list",
        )

    def apply_shared_meeting(self, state: UserRuntimeState) -> None:
        shared_meeting = self.state_store.get_random_meeting(include_completed=False)
        if shared_meeting is None:
            return

        meeting_id = shared_meeting.id
        with self.client.post(
            f"/api/v1/meetings/{meeting_id}/apply",
            headers=self._headers(state.access_token),
            name="meetings.apply",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                state.target_meeting_id = meeting_id
                response.success()
                return
            if response.status_code == 400:
                # 이미 신청됨/모집 마감/정원 초과는 반복 시나리오에서 정상
                response.success()
                return
            if response.status_code == 403:
                # 클럽 미승인 상태일 수 있음
                response.success()
                return
            response.failure(f"apply failed: {response.status_code} {response.text}")

    def sync_score_target(self, state: UserRuntimeState) -> None:
        response = self.client.get(
            "/api/v1/meetings/my/participating?page=1&limit=20",
            headers=self._headers(state.access_token),
            name="meetings.my_participating",
        )
        if response.status_code != 200:
            return

        data = response.json()
        meetings = data["data"]
        for meeting in meetings:
            if not meeting["rounding_completed_at"]:
                continue
            my_participation = meeting["my_participation"]
            if not my_participation:
                continue
            state.target_meeting_id = meeting["id"]
            state.target_participant_id = my_participation["id"]
            return

    def submit_simple_score(self, state: UserRuntimeState) -> None:
        if state.target_meeting_id is None or state.target_participant_id is None:
            return

        with self.client.post(
            f"/api/v1/meetings/{state.target_meeting_id}/participants/{state.target_participant_id}/simple-score",
            json={"gross_score": 95},
            headers=self._headers(state.access_token),
            name="scores.simple",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                response.success()
                return
            if response.status_code in (400, 409):
                # 라운딩 미종료/이미 입력은 반복 시나리오에서 정상
                response.success()
                return
            response.failure(f"simple score failed: {response.status_code} {response.text}")
