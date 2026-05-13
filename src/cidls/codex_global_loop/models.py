import json
from datetime import datetime, timezone


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class HookExecutionResult:
    def __init__(
        self,
        ok,
        command,
        returncode,
        stdout="",
        stderr="",
        attempted_installer=False,
        installer_command="",
        installer_returncode=None,
    ):
        self.ok = bool(ok)
        self.command = str(command or "")
        self.returncode = int(returncode)
        self.stdout = str(stdout or "")
        self.stderr = str(stderr or "")
        self.attempted_installer = bool(attempted_installer)
        self.installer_command = str(installer_command or "")
        self.installer_returncode = installer_returncode
        self.generated_at_utc = utc_now_iso()

    def to_dict(self):
        return {
            "ok": self.ok,
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "attempted_installer": self.attempted_installer,
            "installer_command": self.installer_command,
            "installer_returncode": self.installer_returncode,
            "generated_at_utc": self.generated_at_utc,
        }


class GlobalWiringAuditResult:
    def __init__(self, payload):
        self.payload = dict(payload or {})

    def issues(self):
        return list(self.payload.get("issues", []))

    def ok(self):
        return not self.issues()

    def to_dict(self):
        return dict(self.payload)


class KanbanTicketUpdate:
    def __init__(
        self,
        ticket_id="",
        status="todo",
        priority="medium",
        title="",
        copy="",
        stage_id="fusion",
        asis="",
        tobe="",
        evidence="",
        trace=None,
        action="upsert",
    ):
        self.ticket_id = str(ticket_id or "")
        self.status = str(status or "todo")
        self.priority = str(priority or "medium")
        self.title = str(title or "")
        self.copy = str(copy or "")
        self.stage_id = str(stage_id or "fusion")
        self.asis = str(asis or "")
        self.tobe = str(tobe or "")
        self.evidence = str(evidence or "")
        self.trace = list(trace or [])
        self.action = str(action or "upsert")

    def to_ticket_dict(self):
        return {
            "id": self.ticket_id,
            "status": self.status,
            "priority": self.priority,
            "title": self.title,
            "copy": self.copy,
            "stageId": self.stage_id,
            "asis": self.asis,
            "tobe": self.tobe,
            "evidence": self.evidence,
            "trace": list(self.trace),
        }

    def to_dict(self):
        payload = self.to_ticket_dict()
        payload["action"] = self.action
        return payload


class DevragSearchResult:
    def __init__(self, query, command, returncode, results=None, stdout="", stderr=""):
        self.query = str(query or "")
        self.command = list(command or [])
        self.returncode = int(returncode)
        self.results = list(results or [])
        self.stdout = str(stdout or "")
        self.stderr = str(stderr or "")
        self.generated_at_utc = utc_now_iso()

    def ok(self):
        return self.returncode == 0

    def to_dict(self):
        return {
            "query": self.query,
            "command": list(self.command),
            "returncode": self.returncode,
            "results": list(self.results),
            "stdout": self.stdout,
            "stderr": self.stderr,
            "generated_at_utc": self.generated_at_utc,
        }

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
