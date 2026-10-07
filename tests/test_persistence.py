"""Testes de persistência (snapshot/reload) e limpeza por TTL."""
from __future__ import annotations

from datetime import timedelta

from app.config import Settings
from app.domain.models import now_utc
from app.realtime.hub import Hub
from app.services.room_manager import RoomManager


def _mgr(tmp_path) -> RoomManager:
    settings = Settings(data_dir=str(tmp_path), image_provider="fake", cors_origins="")
    return RoomManager(settings=settings, hub=Hub())


def test_snapshot_and_reload(tmp_path):
    mgr = _mgr(tmp_path)
    from app.domain.models import RoomConfig
    room = mgr.create_room("Host", RoomConfig(), "idhost")
    mgr.join_room(room.code, "Ana", "idana")
    code = room.code

    # novo manager (simula reinício do processo)
    mgr2 = _mgr(tmp_path)
    mgr2.load_from_disk()
    loaded = mgr2.get(code)
    assert loaded is not None
    assert set(loaded.players.keys()) == {"idhost", "idana"}
    assert loaded.host_id == "idhost"


def test_expired_room_not_reloaded(tmp_path):
    mgr = _mgr(tmp_path)
    from app.domain.models import RoomConfig
    room = mgr.create_room("Host", RoomConfig(), "idhost")
    code = room.code
    # envelhece o snapshot além do TTL
    room.updated_at = now_utc() - timedelta(hours=mgr.settings.room_ttl_hours + 1)
    mgr.persist(room)

    mgr2 = _mgr(tmp_path)
    mgr2.load_from_disk()
    assert mgr2.get(code) is None


def test_destroy_removes_files(tmp_path):
    mgr = _mgr(tmp_path)
    from app.domain.models import RoomConfig
    room = mgr.create_room("Host", RoomConfig(), "idhost")
    code = room.code
    assert (mgr.settings.rooms_path / f"{code}.json").exists()
    mgr._destroy(room)
    assert not (mgr.settings.rooms_path / f"{code}.json").exists()
    assert mgr.get(code) is None
