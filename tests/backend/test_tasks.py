"""
Tests for task API endpoints.
"""
import pytest

import main


@pytest.fixture(autouse=True)
def reset_tasks():
    """Tasks live in memory; isolate every test."""
    main.tasks.clear()
    main.task_sequence = 0
    yield
    main.tasks.clear()
    main.task_sequence = 0


@pytest.fixture
def task_payload():
    """Valid create request, in the shape TasksModal.vue sends."""
    return {"title": "Check Q4 stock levels", "priority": "high", "dueDate": "2025-11-20"}


class TestTaskEndpoints:
    """Test suite for task endpoints."""

    def test_get_tasks_initially_empty(self, client):
        """Test that there are no API tasks before any are created."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_task(self, client, task_payload):
        """Test creating a task returns the frontend's task shape."""
        response = client.post("/api/tasks", json=task_payload)
        assert response.status_code == 201
        assert response.json() == {
            "id": "TASK-0001",
            "title": "Check Q4 stock levels",
            "priority": "high",
            "dueDate": "2025-11-20",
            "status": "pending",
        }

    def test_task_ids_are_strings(self, client, task_payload):
        """Test IDs can't collide with the numeric IDs of the mock tasks in useAuth."""
        task = client.post("/api/tasks", json=task_payload).json()
        assert isinstance(task["id"], str)
        assert not task["id"].isdigit()

    def test_get_tasks_newest_first(self, client, task_payload):
        """Test that tasks are listed newest first."""
        client.post("/api/tasks", json=task_payload)
        client.post("/api/tasks", json={**task_payload, "title": "Second"})

        titles = [t["title"] for t in client.get("/api/tasks").json()]
        assert titles == ["Second", "Check Q4 stock levels"]

    def test_title_is_trimmed(self, client, task_payload):
        """Test that surrounding whitespace is removed from the title."""
        task_payload["title"] = "  Padded  "
        assert client.post("/api/tasks", json=task_payload).json()["title"] == "Padded"

    def test_priority_defaults_to_medium(self, client, task_payload):
        """Test that priority is optional and defaults to medium."""
        del task_payload["priority"]
        assert client.post("/api/tasks", json=task_payload).json()["priority"] == "medium"

    @pytest.mark.parametrize("field,value", [
        ("title", "   "),
        ("priority", "urgent"),
        ("dueDate", "20.11.2025"),
        ("dueDate", "2025-13-01"),
    ])
    def test_invalid_input_rejected(self, client, task_payload, field, value):
        """Test that invalid field values return 400 and create nothing."""
        task_payload[field] = value
        response = client.post("/api/tasks", json=task_payload)
        assert response.status_code == 400
        assert main.tasks == []

    def test_missing_title_returns_422(self, client, task_payload):
        """Test that a missing required field fails validation."""
        del task_payload["title"]
        assert client.post("/api/tasks", json=task_payload).status_code == 422

    def test_toggle_task(self, client, task_payload):
        """Test toggling a task to completed and back."""
        task_id = client.post("/api/tasks", json=task_payload).json()["id"]

        response = client.patch(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

        assert client.patch(f"/api/tasks/{task_id}").json()["status"] == "pending"
        assert client.get("/api/tasks").json()[0]["status"] == "pending"

    def test_delete_task(self, client, task_payload):
        """Test deleting a task removes it and returns it."""
        task = client.post("/api/tasks", json=task_payload).json()

        response = client.delete(f"/api/tasks/{task['id']}")
        assert response.status_code == 200
        assert response.json() == task
        assert client.get("/api/tasks").json() == []

    def test_ids_not_reused_after_delete(self, client, task_payload):
        """Test that a new task never reuses a deleted task's ID."""
        first = client.post("/api/tasks", json=task_payload).json()["id"]
        client.delete(f"/api/tasks/{first}")
        second = client.post("/api/tasks", json=task_payload).json()["id"]
        assert second != first

    @pytest.mark.parametrize("method", ["patch", "delete"])
    def test_nonexistent_task(self, client, method):
        """Test toggling or deleting a task that doesn't exist."""
        response = getattr(client, method)("/api/tasks/TASK-9999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
