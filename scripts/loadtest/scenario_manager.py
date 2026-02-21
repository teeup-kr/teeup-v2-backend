from __future__ import annotations

from datetime import datetime, timedelta

from state_store import StateStore, UserRuntimeState


class ManagerScenario:
    def __init__(self, client, state_store: StateStore):
        self.client = client
        self.state_store = state_store

    @staticmethod
    def _headers(token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def refresh_managed_club(self, state: UserRuntimeState) -> None:
        response = self.client.get(
            "/api/v1/clubs/my?page=1&limit=50",
            headers=self._headers(state.access_token),
            name="clubs.my",
        )
        if response.status_code != 200:
            return

        data = response.json()
        clubs = data["data"]
        for club in clubs:
            role = club["membership_role"]
            if role not in ("LEADER", "MANAGER"):
                continue
            display_id = club["display_id"] if club["display_id"] else str(club["id"])
            state.managed_club_id = display_id
            state.managed_club_numeric_id = club["id"]
            self.state_store.upsert_club(club_id=club["id"], display_id=display_id, owner_vu_id=state.vu_id)
            return

    def _create_managed_club(self, state: UserRuntimeState) -> None:
        sido_response = self.client.get(
            "/api/v1/sido-list",
            headers=self._headers(state.access_token),
            name="region.sido_list",
        )
        if sido_response.status_code != 200:
            return
        sidos = sido_response.json()
        if not sidos:
            return
        sido_code = sidos[0]["code"]

        gungu_response = self.client.get(
            f"/api/v1/gungu-list?sido_code={sido_code}",
            headers=self._headers(state.access_token),
            name="region.gungu_list",
        )
        if gungu_response.status_code != 200:
            return
        gungus = gungu_response.json()
        if not gungus:
            return
        gungu_code = gungus[0]["code"]

        payload = {
            "name": f"load-club-{state.run_id}-{state.vu_id}",
            "sido_code": sido_code,
            "gungu_codes": [gungu_code],
            "type": "REGULAR",
            "description": "loadtest club",
            "member_count": 16,
            "contact_info": "010-0000-0000",
            "representative_name": f"load_manager_{state.vu_id}",
            "additional_info": "loadtest",
        }

        with self.client.post(
            "/api/v1/clubs",
            json=payload,
            headers=self._headers(state.access_token),
            name="clubs.create",
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 201):
                response.failure(f"club create failed: {response.status_code} {response.text}")
                return
            club = response.json()
            display_id = club["display_id"] if club["display_id"] else str(club["id"])
            state.managed_club_id = display_id
            state.managed_club_numeric_id = club["id"]
            self.state_store.upsert_club(club_id=club["id"], display_id=display_id, owner_vu_id=state.vu_id)
            response.success()

    def ensure_managed_club(self, state: UserRuntimeState) -> None:
        self.refresh_managed_club(state)
        if state.managed_club_id and state.managed_club_numeric_id:
            return
        self._create_managed_club(state)

    def approve_pending_members(self, state: UserRuntimeState) -> None:
        if not state.managed_club_id:
            return

        response = self.client.get(
            f"/api/v1/clubs/{state.managed_club_id}/members?all_members=true&page=1&limit=500",
            headers=self._headers(state.access_token),
            name="clubs.members_all",
        )
        if response.status_code != 200:
            return

        data = response.json()
        members = data["data"]
        for member in members:
            if member["status"] != "PENDING":
                continue
            user_id = member["user_id"]
            with self.client.post(
                f"/api/v1/clubs/{state.managed_club_id}/members/{user_id}/approve",
                headers=self._headers(state.access_token),
                name="clubs.approve",
                catch_response=True,
            ) as approve_response:
                if approve_response.status_code in (200, 201, 404):
                    approve_response.success()
                else:
                    approve_response.failure(
                        f"approve failed: {approve_response.status_code} {approve_response.text}"
                    )

    def create_round_meeting(self, state: UserRuntimeState) -> None:
        if not state.managed_club_id or state.managed_club_numeric_id is None:
            return

        meeting_time = datetime.utcnow() + timedelta(days=3)
        deadline = datetime.utcnow() + timedelta(days=2)
        payload = {
            "name": f"load-round-{state.run_id}-{state.vu_id}-{int(datetime.utcnow().timestamp())}",
            "description": "loadtest meeting",
            "location": "Load Test CC",
            "meeting_time": meeting_time.isoformat(),
            "application_deadline": deadline.isoformat(),
            "tee_times": ["07:30"],
            "max_participants": 16,
            "meeting_type": "ROUND",
            "meeting_subtype": "REGULAR",
            "settlement_method": "EQUAL_SPLIT",
            "club_id": state.managed_club_numeric_id,
            "course_name": "Load Course",
            "hole_count": 18,
            "reservation_name": "loadtest",
            "team_formation_mode": "GENDER_MIXED_RANDOM",
            "team_size": 4,
        }

        with self.client.post(
            f"/api/v1/meetings?club_id={state.managed_club_id}",
            json=payload,
            headers=self._headers(state.access_token),
            name="meetings.create",
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 201):
                response.failure(f"meeting create failed: {response.status_code} {response.text}")
                return

            meeting = response.json()
            meeting_id = meeting["id"]
            state.target_meeting_id = meeting_id
            self.state_store.upsert_meeting(
                meeting_id=meeting_id,
                club_id=state.managed_club_numeric_id,
                club_display_id=state.managed_club_id,
                owner_vu_id=state.vu_id,
            )
            response.success()

    def _get_meeting_detail(self, state: UserRuntimeState, meeting_id: int) -> dict | None:
        response = self.client.get(
            f"/api/v1/meetings/{meeting_id}",
            headers=self._headers(state.access_token),
            name="meetings.detail",
        )
        if response.status_code != 200:
            return None
        return response.json()

    def _get_round_participants(self, state: UserRuntimeState, meeting_id: int) -> list[dict]:
        response = self.client.get(
            f"/api/v1/rounds/{meeting_id}/participants",
            headers=self._headers(state.access_token),
            name="rounds.participants",
        )
        if response.status_code != 200:
            return []
        return response.json()

    def _add_guest(self, state: UserRuntimeState, meeting_id: int, guest_index: int) -> None:
        payload = {
            "name": f"load_guest_{state.vu_id}_{guest_index}",
            "gender": "MALE" if guest_index % 2 == 0 else "FEMALE",
            "average_score": 95,
        }
        with self.client.post(
            f"/api/v1/meetings/{meeting_id}/guests",
            json=payload,
            headers=self._headers(state.access_token),
            name="meetings.add_guest",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                response.success()
                return
            if response.status_code == 400:
                response.success()
                return
            response.failure(f"add guest failed: {response.status_code} {response.text}")

    def _ensure_min_participants(self, state: UserRuntimeState, meeting_id: int, minimum: int = 4) -> None:
        participants = self._get_round_participants(state, meeting_id)
        current_count = len(participants)
        if current_count >= minimum:
            return

        needed = minimum - current_count
        for guest_index in range(needed):
            self._add_guest(state, meeting_id, guest_index)

    def _create_rounding_settlement(self, state: UserRuntimeState, meeting_id: int) -> None:
        participants = self._get_round_participants(state, meeting_id)
        if not participants:
            return

        payer_ids = [participant["user_id"] for participant in participants if participant["user_id"]]
        if not payer_ids:
            payer_ids = [participants[0]["id"]]

        payload = {
            "total_cost": 30000,
            "green_fee": 10000,
            "caddy_fee": 10000,
            "cart_fee": 10000,
            "other_fee": 0,
            "green_fee_participants": payer_ids,
            "caddy_fee_participants": payer_ids,
            "cart_fee_participants": payer_ids,
            "other_expense_items": [],
            "settlement_method": "EQUAL_SPLIT",
        }

        with self.client.post(
            f"/api/v1/meetings/{meeting_id}/settlement/rounding",
            json=payload,
            headers=self._headers(state.access_token),
            name="meetings.settlement_rounding",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                response.success()
                return
            if response.status_code == 400:
                # 이미 생성됨/상태 불일치 등 반복 시나리오에서 허용
                response.success()
                return
            response.failure(f"settlement create failed: {response.status_code} {response.text}")

    def progress_workflow(self, state: UserRuntimeState) -> None:
        if state.target_meeting_id is None:
            self.create_round_meeting(state)
            return

        meeting_id = state.target_meeting_id
        detail = self._get_meeting_detail(state, meeting_id)
        if detail is None:
            state.target_meeting_id = None
            return

        if detail["is_completed"]:
            self.state_store.update_meeting_flags(meeting_id=meeting_id, completed=True)
            state.target_meeting_id = None
            return

        self._ensure_min_participants(state, meeting_id)

        if not detail["application_closed_early"]:
            with self.client.post(
                f"/api/v1/meetings/{meeting_id}/close-application",
                headers=self._headers(state.access_token),
                name="meetings.close_application",
                catch_response=True,
            ) as response:
                if response.status_code in (200, 201, 400):
                    response.success()
                else:
                    response.failure(f"close application failed: {response.status_code} {response.text}")
            detail = self._get_meeting_detail(state, meeting_id)
            if detail is None:
                return

        if not detail["team_formation_confirmed_at"]:
            with self.client.post(
                f"/api/v1/meetings/{meeting_id}/start-team-formation",
                headers=self._headers(state.access_token),
                name="meetings.start_team_formation",
                catch_response=True,
            ) as response:
                if response.status_code in (200, 201, 400):
                    response.success()
                else:
                    response.failure(f"start team formation failed: {response.status_code} {response.text}")

            with self.client.post(
                f"/api/v1/meetings/{meeting_id}/teams/auto-formation",
                json={"formation_mode": "GENDER_MIXED_RANDOM", "team_size": 4},
                headers=self._headers(state.access_token),
                name="meetings.auto_formation",
                catch_response=True,
            ) as response:
                if response.status_code in (200, 201, 400):
                    response.success()
                else:
                    response.failure(f"auto formation failed: {response.status_code} {response.text}")

            with self.client.post(
                f"/api/v1/meetings/{meeting_id}/teams/confirm",
                headers=self._headers(state.access_token),
                name="meetings.confirm_teams",
                catch_response=True,
            ) as response:
                if response.status_code in (200, 201, 400):
                    response.success()
                else:
                    response.failure(f"confirm teams failed: {response.status_code} {response.text}")

            detail = self._get_meeting_detail(state, meeting_id)
            if detail is None:
                return

        if not detail["rounding_started_at"]:
            with self.client.post(
                f"/api/v1/meetings/{meeting_id}/start-rounding",
                headers=self._headers(state.access_token),
                name="meetings.start_rounding",
                catch_response=True,
            ) as response:
                if response.status_code in (200, 201, 400):
                    response.success()
                else:
                    response.failure(f"start rounding failed: {response.status_code} {response.text}")
            detail = self._get_meeting_detail(state, meeting_id)
            if detail is None:
                return

        if not detail["rounding_completed_at"]:
            with self.client.post(
                f"/api/v1/meetings/{meeting_id}/complete-rounding",
                headers=self._headers(state.access_token),
                name="meetings.complete_rounding",
                catch_response=True,
            ) as response:
                if response.status_code in (200, 201, 400):
                    response.success()
                else:
                    response.failure(f"complete rounding failed: {response.status_code} {response.text}")
            self.state_store.update_meeting_flags(meeting_id=meeting_id, rounding_completed=True)
            detail = self._get_meeting_detail(state, meeting_id)
            if detail is None:
                return

        if not detail["settlement_confirmed"]:
            settlement_response = self.client.get(
                f"/api/v1/meetings/{meeting_id}/settlement",
                headers=self._headers(state.access_token),
                name="meetings.get_settlement",
            )
            if settlement_response.status_code == 200:
                settlement_payload = settlement_response.json()
                if settlement_payload["settlement"] is None:
                    self._create_rounding_settlement(state, meeting_id)
            else:
                self._create_rounding_settlement(state, meeting_id)

            with self.client.post(
                f"/api/v1/meetings/{meeting_id}/settlement/confirm",
                headers=self._headers(state.access_token),
                name="meetings.confirm_settlement",
                catch_response=True,
            ) as response:
                if response.status_code in (200, 201, 400):
                    response.success()
                else:
                    response.failure(f"confirm settlement failed: {response.status_code} {response.text}")
            self.state_store.update_meeting_flags(meeting_id=meeting_id, settlement_confirmed=True)
            detail = self._get_meeting_detail(state, meeting_id)
            if detail is None:
                return

        if not detail["is_completed"]:
            with self.client.post(
                f"/api/v1/meetings/{meeting_id}/complete",
                headers=self._headers(state.access_token),
                name="meetings.complete",
                catch_response=True,
            ) as response:
                if response.status_code in (200, 201, 400):
                    response.success()
                else:
                    response.failure(f"complete meeting failed: {response.status_code} {response.text}")
            self.state_store.update_meeting_flags(meeting_id=meeting_id, completed=True)
