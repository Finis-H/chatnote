import json
import os
import re
import threading
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Column, Text, text as sa_text
from sqlmodel import Field, Session, SQLModel, create_engine, select

from main import VAULT_ROOT

# 获取当前时间的辅助函数
def _now():
    return datetime.now().isoformat(timespec="seconds")

# 简单封装一下 JSON 序列化，避免 None 导致的异常，并且保持兼容性
def _json_dump(value):
    return json.dumps(value if value is not None else {}, ensure_ascii=False)

# 简单封装一下 JSON 反序列化，避免空字符串或异常导致的崩溃，并且保持兼容性
def _json_load(value, fallback=None):
    if fallback is None:
        fallback = {}
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback

# 定义数据库模型
class Entity(SQLModel, table=True):
    __tablename__ = "entities"

    entity_id: str = Field(primary_key=True, max_length=50)
    type: str = Field(max_length=20)
    name: str = Field(index=True, max_length=100)
    aliases_json: str = Field(default="[]", sa_column=Column("aliases", Text))
    attributes_json: str = Field(default="{}", sa_column=Column("attributes", Text))
    archived_at: Optional[str] = Field(default=None)
    created_at: str = Field(default_factory=_now)


class Relationship(SQLModel, table=True):
    __tablename__ = "relationships"

    rel_id: Optional[int] = Field(default=None, primary_key=True)
    source_id: str = Field(index=True, max_length=50)
    target_id: str = Field(index=True, max_length=50)
    relation_type: str = Field(index=True, max_length=50)
    status: str = Field(default="ACTIVE", index=True, max_length=20)
    confidence: float = Field(default=1.0)
    source_event_id: Optional[str] = Field(default=None, max_length=50)
    properties_json: str = Field(default="{}", sa_column=Column("properties", Text))
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)
    archived_at: Optional[str] = Field(default=None)


class MemoryEvent(SQLModel, table=True):
    __tablename__ = "memory_events"

    event_id: str = Field(primary_key=True, max_length=50)
    timestamp: str = Field(default_factory=_now, index=True)
    actor_id: str = Field(index=True, max_length=50)
    target_id: Optional[str] = Field(default=None, index=True, max_length=50)
    action_category: str = Field(index=True, max_length=20)
    action_detail: str = Field(max_length=100)
    context: str = Field(default="", sa_column=Column(Text))
    raw_reference: Optional[str] = Field(default=None, max_length=160)
    payload_json: str = Field(default="{}", sa_column=Column("payload", Text))
    created_at: str = Field(default_factory=_now)


class EventReview(SQLModel, table=True):
    __tablename__ = "event_reviews"

    event_id: str = Field(primary_key=True, max_length=50)
    status: str = Field(default="MERGED", index=True, max_length=20)
    review_type: str = Field(default="NEW", max_length=30)
    category: str = Field(default="facts", max_length=50)
    old_trait: Optional[str] = Field(default=None, sa_column=Column(Text))
    new_trait: Optional[str] = Field(default=None, sa_column=Column(Text))
    reason: Optional[str] = Field(default=None, sa_column=Column(Text))
    expires_at: Optional[str] = Field(default=None)
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


class StagedEvent(SQLModel, table=True):
    __tablename__ = "staged_events"

    stage_id: str = Field(primary_key=True, max_length=50)
    status: str = Field(default="PENDING", index=True, max_length=20)
    review_type: str = Field(default="NEW", max_length=30)
    target_id: str = Field(index=True, max_length=50)
    action_category: str = Field(index=True, max_length=20)
    action_detail: str = Field(max_length=100)
    category: str = Field(default="facts", max_length=50)
    old_trait: Optional[str] = Field(default=None, sa_column=Column(Text))
    new_trait: Optional[str] = Field(default=None, sa_column=Column(Text))
    context: str = Field(default="", sa_column=Column(Text))
    raw_reference: Optional[str] = Field(default=None, max_length=160)
    payload_json: str = Field(default="{}", sa_column=Column("payload", Text))
    reason: Optional[str] = Field(default=None, sa_column=Column(Text))
    expires_at: str = Field(index=True)
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


class L2EntitySnapshot(SQLModel, table=True):
    __tablename__ = "l2_entity_snapshots"

    entity_id: str = Field(primary_key=True, max_length=50)
    core_profile_json: str = Field(default="{}", sa_column=Column("core_profile", Text))
    active_relations_json: str = Field(default="[]", sa_column=Column("active_relations", Text))
    is_archived: bool = Field(default=False)
    last_event_id: Optional[str] = Field(default=None, max_length=50)
    last_updated: str = Field(default_factory=_now)

# L2认知快照表，用于存储不同领域的宏观认知和当前关注点等信息，支持被事件更新和查询展示
class L2CognitiveSnapshot(SQLModel, table=True):
    __tablename__ = "l2_cognitive_snapshots"

    domain: str = Field(primary_key=True, max_length=50)
    macro_vision: str = Field(default="", sa_column=Column(Text))
    current_focus: str = Field(default="", sa_column=Column(Text))
    current_status: str = Field(default="ACTIVE", max_length=20)
    last_event_id: Optional[str] = Field(default=None, max_length=50)
    last_updated: str = Field(default_factory=_now)


class MemoryMeta(SQLModel, table=True):
    __tablename__ = "memory_meta"

    key: str = Field(primary_key=True, max_length=80)
    value: str = Field(default="", sa_column=Column(Text))
    updated_at: str = Field(default_factory=_now)


class MemoryRepository:
    PROFILE_KEYS = ("coding_style", "communication", "interests", "facts")
    SINGLE_VALUE_PREFERENCE_DETAILS = {"favorite_food"}
    NEGATIVE_PREFERENCE_DETAILS = {"disliked_food"}
    PREFERENCE_DETAILS = SINGLE_VALUE_PREFERENCE_DETAILS | NEGATIVE_PREFERENCE_DETAILS | {"food_preference"}
    PENDING_TTL_DAYS = 3
    BUFFER_BATCH_SIZE = 5
    BUFFER_IDLE_SECONDS = 10 * 60

    def __init__(self, vault_root=VAULT_ROOT):
        self.vault_root = vault_root
        self.buffer_path = os.path.join(vault_root, "event_buffer.jsonl")
        sqlite_url = f"sqlite:///{os.path.join(vault_root, 'vault_core.db')}"
        self.engine = create_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(self.engine)
        self._migrate_schema()
        self.ensure_seed_entities()

    def _migrate_schema(self):
        with self.engine.begin() as conn:
            rel_columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(relationships)").fetchall()}
            migrations = {
                "status": "ALTER TABLE relationships ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE'",
                "confidence": "ALTER TABLE relationships ADD COLUMN confidence FLOAT DEFAULT 1.0",
                "source_event_id": "ALTER TABLE relationships ADD COLUMN source_event_id VARCHAR(50)",
                "properties": "ALTER TABLE relationships ADD COLUMN properties TEXT DEFAULT '{}'",
                "updated_at": "ALTER TABLE relationships ADD COLUMN updated_at VARCHAR",
                "archived_at": "ALTER TABLE relationships ADD COLUMN archived_at VARCHAR",
            }
            for column_name, sql in migrations.items():
                if column_name not in rel_columns:
                    conn.execute(sa_text(sql))
            conn.execute(sa_text("UPDATE relationships SET status = 'ACTIVE' WHERE status IS NULL OR status = ''"))
            conn.execute(sa_text("UPDATE relationships SET confidence = 1.0 WHERE confidence IS NULL"))
            conn.execute(sa_text("UPDATE relationships SET properties = '{}' WHERE properties IS NULL OR properties = ''"))
            conn.execute(sa_text("UPDATE relationships SET updated_at = created_at WHERE updated_at IS NULL OR updated_at = ''"))

    def ensure_seed_entities(self):
        with Session(self.engine) as session:
            if not session.get(Entity, "e_boss"):
                session.add(Entity(
                    entity_id="e_boss",
                    type="self",
                    name="Boss",
                    aliases_json=_json_dump(["我", "用户", "Boss", "BOSS", "boss", "Master", "主人", "本尊", "自己", "本人"]),
                ))
            if not session.get(L2EntitySnapshot, "e_boss"):
                session.add(L2EntitySnapshot(entity_id="e_boss", core_profile_json=_json_dump(self.empty_profile())))
            meta = session.get(MemoryMeta, "schema_version")
            if not meta:
                session.add(MemoryMeta(key="schema_version", value="2"))
            session.commit()
        self.settle_expired_pending()

    def _get_meta(self, session, key, default=""):
        meta = session.get(MemoryMeta, key)
        return meta.value if meta else default

    def empty_profile(self):
        return {key: [] for key in self.PROFILE_KEYS}

    def make_entity_id(self, name):
        if self.normalize_entity_name(name) == "Boss":
            return "e_boss"
        return "e_" + uuid.uuid5(uuid.NAMESPACE_URL, f"vaultos:{name}").hex[:12]

    def get_entity_by_name(self, session, name):
        normalized = self.normalize_entity_name(name)
        entity_id = self.make_entity_id(normalized)
        entity = session.get(Entity, entity_id)
        if entity:
            return entity
        entity_type = "self" if normalized == "Boss" else "person"
        entity = Entity(
            entity_id=entity_id,
            type=entity_type,
            name=normalized,
            aliases_json=_json_dump(MemoryRouter.aliases_for(normalized)),
        )
        session.add(entity)
        session.flush()
        if not session.get(L2EntitySnapshot, entity_id):
            session.add(L2EntitySnapshot(entity_id=entity_id, core_profile_json=_json_dump(self.empty_profile())))
        return entity

    def normalize_entity_name(self, entity):
        return MemoryRouter.normalize_entity(entity)

    def get_profile(self, entity_name="Boss"):
        with Session(self.engine) as session:
            entity = self.get_entity_by_name(session, entity_name)
            snapshot = session.get(L2EntitySnapshot, entity.entity_id)
            if not snapshot:
                return self.empty_profile()
            profile = _json_load(snapshot.core_profile_json, self.empty_profile())
            for key in self.PROFILE_KEYS:
                if not isinstance(profile.get(key), list):
                    profile[key] = []
            return profile

    def get_entity_snapshot_text(self, entity_name):
        with Session(self.engine) as session:
            entity = self.get_entity_by_name(session, entity_name)
            profile = self._profile_for_update(session, entity.entity_id)
            relations = self._relations_for_entity(session, entity.entity_id)
        lines = []
        for key, traits in profile.items():
            if traits:
                lines.append(f"[{key}]")
                lines.extend(f"- {trait}" for trait in traits)
        if relations:
            lines.append("[relations]")
            lines.extend(f"- {item}" for item in relations)
        return "\n".join(lines)

    def get_l2_context_text(self, user_input):
        with Session(self.engine) as session:
            entities = session.exec(select(Entity)).all()
            known = {row.name: _json_load(row.aliases_json, []) for row in entities}
            known_set = set(known)
            matched = set(entity for entity in MemoryRouter().resolve_entities(user_input, known) if entity in known_set)
            for relation_type in MemoryRouter.resolve_relation_types(user_input):
                rows = session.exec(
                    select(Relationship).where(
                        Relationship.source_id == "e_boss",
                        Relationship.relation_type == relation_type,
                        Relationship.status == "ACTIVE",
                        Relationship.archived_at == None,  # noqa: E711
                    )
                ).all()
                for row in rows:
                    target = session.get(Entity, row.target_id)
                    if target:
                        matched.add(target.name)

            context_parts = []
            boss = session.get(Entity, "e_boss")
            boss_content = self._entity_snapshot_text_from_session(session, boss) if boss else ""
            if boss_content:
                context_parts.append(f"【Boss 当前 L2 画像摘要】\n{boss_content}")
            for entity_name in sorted(entity for entity in matched if entity != "Boss"):
                entity = self.get_entity_by_name(session, entity_name)
                content = self._entity_snapshot_text_from_session(session, entity)
                if content:
                    context_parts.append(
                        f"【实体专属事实源 - {entity.name}】\n"
                        f"以下内容是回答“{entity.name}”相关问题的最高优先级事实源。\n"
                        f"{content}"
                    )
                else:
                    context_parts.append(
                        f"【实体专属事实源 - {entity.name}】\n"
                        "本地实体档案暂无记录。回答该实体问题时，禁止套用 Boss 自己的画像或模型常识。"
                    )
            cognitive_rows = session.exec(select(L2CognitiveSnapshot)).all()
            cognitive_lines = []
            text = str(user_input or "")
            for row in cognitive_rows:
                if row.domain and row.domain in text:
                    if row.macro_vision:
                        cognitive_lines.append(f"[{row.domain}] 宏观规划: {row.macro_vision}")
                    if row.current_focus:
                        cognitive_lines.append(f"[{row.domain}] 当前焦点: {row.current_focus}")
            if cognitive_lines:
                context_parts.append("【命中认知快照】\n" + "\n".join(cognitive_lines))
            return "\n\n".join(context_parts)

    def _entity_snapshot_text_from_session(self, session, entity):
        snapshot = session.get(L2EntitySnapshot, entity.entity_id)
        profile = _json_load(snapshot.core_profile_json, self.empty_profile()) if snapshot else self.empty_profile()
        lines = []
        for key, traits in profile.items():
            if traits:
                lines.append(f"[{key}]")
                lines.extend(f"- {trait}" for trait in traits)
        relations = self._relations_for_entity(session, entity.entity_id)
        if relations:
            lines.append("[relations]")
            lines.extend(f"- {item}" for item in relations)
        return "\n".join(lines)

    def _relations_for_entity(self, session, entity_id):
        rows = session.exec(
            select(Relationship).where(
                Relationship.status == "ACTIVE",
                Relationship.archived_at == None,  # noqa: E711
            )
        ).all()
        lines = []
        for row in rows:
            if row.source_id != entity_id and row.target_id != entity_id:
                continue
            source = session.get(Entity, row.source_id)
            target = session.get(Entity, row.target_id)
            if not source or not target:
                continue
            lines.append(f"{source.name} --{row.relation_type}--> {target.name}")
        return lines

    def get_all_cognitive_snapshots(self):
        with Session(self.engine) as session:
            rows = session.exec(select(L2CognitiveSnapshot)).all()
            return [
                {
                    "domain": row.domain,
                    "macro_vision": row.macro_vision,
                    "current_focus": row.current_focus,
                    "current_status": row.current_status,
                }
                for row in rows
            ]

    def fetch_memory_items(self, limit=80):
        self.settle_expired_pending()
        with Session(self.engine) as session:
            staged_rows = session.exec(
                select(StagedEvent)
                .order_by(StagedEvent.created_at.desc())
                .limit(limit)
            ).all()
            result = []
            for stage in staged_rows:
                payload = _json_load(stage.payload_json, {})
                result.append({
                    "id": stage.stage_id,
                    "type": stage.review_type,
                    "status": stage.status,
                    "category": stage.category or stage.action_detail or stage.action_category,
                    "old_trait": stage.old_trait,
                    "new_trait": stage.new_trait or stage.context,
                    "expires_at": stage.expires_at,
                    "created_at": stage.created_at,
                    "target_entity": payload.get("target_entity"),
                    "action_category": stage.action_category,
                    "context": stage.context,
                })

            rows = session.exec(
                select(EventReview, MemoryEvent)
                .join(MemoryEvent, MemoryEvent.event_id == EventReview.event_id)
                .order_by(MemoryEvent.timestamp.desc())
                .limit(limit)
            ).all()
            for review, event in rows:
                payload = _json_load(event.payload_json, {})
                if payload.get("stage_id"):
                    continue
                if review.status == "PENDING":
                    continue
                result.append({
                    "id": event.event_id,
                    "type": review.review_type,
                    "status": review.status,
                    "category": review.category or event.action_detail or event.action_category,
                    "old_trait": review.old_trait,
                    "new_trait": review.new_trait or event.context,
                    "expires_at": review.expires_at,
                    "created_at": review.created_at or event.created_at,
                    "target_entity": payload.get("target_entity"),
                    "action_category": event.action_category,
                    "context": event.context,
                })
            return sorted(result, key=lambda item: item.get("created_at") or "", reverse=True)[:limit]

    def append_buffer_item(self, text, thread_id="global"):
        os.makedirs(self.vault_root, exist_ok=True)
        record = {
            "buffer_id": f"buf_{uuid.uuid4().hex[:12]}",
            "thread_id": thread_id or "global",
            "text": str(text or "").strip(),
            "created_at": _now(),
        }
        if not record["text"]:
            return {"queued": False, "reason": "empty"}
        with open(self.buffer_path, "a", encoding="utf-8") as f:
            f.write(_json_dump(record) + "\n")
        return {"queued": True, "buffer_id": record["buffer_id"]}

    def _read_buffer_records(self):
        if not os.path.exists(self.buffer_path):
            return []
        records = []
        with open(self.buffer_path, "r", encoding="utf-8") as f:
            for index, line in enumerate(f, start=1):
                data = _json_load(line.strip(), None)
                if isinstance(data, dict):
                    data["_cursor"] = index
                    records.append(data)
        return records

    def get_unprocessed_buffer_records(self, session):
        cursor = int(self._get_meta(session, "last_buffer_cursor", "0") or 0)
        return [item for item in self._read_buffer_records() if int(item.get("_cursor", 0)) > cursor]

    def _buffer_should_flush(self, records, force=False):
        if force:
            return bool(records)
        if len(records) >= self.BUFFER_BATCH_SIZE:
            return True
        if not records:
            return False
        try:
            oldest = datetime.fromisoformat(records[0].get("created_at"))
        except Exception:
            return False
        return (datetime.now() - oldest).total_seconds() >= self.BUFFER_IDLE_SECONDS

    def flush_event_buffer(self, extractor, force=False):
        self.settle_expired_pending()
        with Session(self.engine) as session:
            records = self.get_unprocessed_buffer_records(session)
            if not self._buffer_should_flush(records, force=force):
                return {
                    "ok": True,
                    "processed": 0,
                    "queued": len(records),
                    "pending": len(session.exec(select(StagedEvent).where(StagedEvent.status == "PENDING")).all()),
                    "message": f"缓冲池尚未达到批处理阈值：当前 {len(records)} 条，已处理 0 条。",
                }
            try:
                buffer_count = len(records)
                routed_events = extractor(records) if extractor else []
                if isinstance(routed_events, dict):
                    routed_events = [routed_events]
                routed_events = [item for item in (routed_events or []) if isinstance(item, dict)]
                processed = self._submit_events_grouped_in_session(session, routed_events)
                self._set_meta(session, "last_buffer_cursor", str(records[-1]["_cursor"]))
                self._set_meta(session, "last_settlement_time", _now())
                session.commit()
                pending = len(session.exec(select(StagedEvent).where(StagedEvent.status == "PENDING")).all())
                return {
                    "ok": True,
                    "processed": processed,
                    "queued": 0,
                    "pending": pending,
                    "message": f"缓冲池 {buffer_count} 条，已提取并处理 {processed} 条标准记忆事件，当前待审 {pending} 条。",
                }
            except Exception as e:
                session.rollback()
                return {
                    "ok": False,
                    "processed": 0,
                    "queued": len(records),
                    "pending": len(session.exec(select(StagedEvent).where(StagedEvent.status == "PENDING")).all()),
                    "message": f"记忆缓冲池处理失败：{e}",
                }

    def submit_events_grouped(self, routed_events):
        self.settle_expired_pending()
        with Session(self.engine) as session:
            try:
                processed = self._submit_events_grouped_in_session(session, routed_events)
                self._set_meta(session, "last_settlement_time", _now())
                session.commit()
                return processed
            except Exception:
                session.rollback()
                raise

    def _submit_events_grouped_in_session(self, session, routed_events):
        grouped = sorted(
            routed_events or [],
            key=lambda item: (
                str(item.get("target_entity") or "Boss"),
                str(item.get("action_category") or "PROFILE"),
            ),
        )
        processed = 0
        for routed in grouped:
            routed = MemoryRouter().route(routed)
            if not routed:
                continue
            target = self.get_entity_by_name(session, routed.get("target_entity") or "Boss")
            stage = self._build_stage(session, target, routed)
            if stage:
                session.add(stage)
                processed += 1
                continue
            if routed.pop("_drop_event", False):
                continue
            event, review = self._build_merged_event(session, target, routed, status="MERGED")
            session.add(event)
            session.add(review)
            self._apply_event_to_snapshots(session, event, review)
            processed += 1
        event_count = len(session.exec(select(MemoryEvent)).all())
        self._set_meta(session, "last_analyzed_cursor", str(event_count))
        return processed

    def submit_event(self, routed):
        self.settle_expired_pending()
        with Session(self.engine) as session:
            target = self.get_entity_by_name(session, routed.get("target_entity") or "Boss")
            stage = self._build_stage(session, target, routed)
            if stage:
                session.add(stage)
                self._set_meta(session, "last_settlement_time", _now())
                session.commit()
                return stage.stage_id, stage.status
            if routed.pop("_drop_event", False):
                return f"drop_{uuid.uuid4().hex[:12]}", "REJECTED"

            event, review = self._build_merged_event(session, target, routed, status="MERGED")
            if review.status == "MERGED":
                session.add(event)
                session.add(review)
                self._apply_event_to_snapshots(session, event, review)
            self._set_meta(session, "last_settlement_time", _now())
            session.commit()
            return event.event_id, review.status

    def _build_stage(self, session, target, routed):
        category = self._category_for_routed(routed)
        new_trait = routed.get("new_trait") or routed.get("context") or ""
        confidence = float(routed.get("confidence", 1.0) or 0)
        requires_review = bool(routed.get("requires_review")) or confidence < 0.7
        review_type = routed.get("review_type") or "NEW"
        old_trait = None
        action_detail = str(routed.get("action_detail") or "").lower()

        if routed.get("action_category") in {"RELATION", "ENTITY"} and routed.get("relation_type"):
            relation_type = routed.get("relation_type")
            if relation_type in MemoryRouter.SINGLE_VALUE_RELATIONS:
                existing = self._active_relationship(session, "e_boss", relation_type)
                if existing and existing.target_id != target.entity_id:
                    existing_target = session.get(Entity, existing.target_id)
                    old_name = existing_target.name if existing_target else existing.target_id
                    old_trait = f"{relation_type}: {old_name}"
                    review_type = "CONFLICT"
                    requires_review = True
                elif existing and existing.target_id == target.entity_id and self._is_duplicate(
                    self._profile_for_update(session, target.entity_id), category, new_trait
                ):
                    routed["_drop_event"] = True
                    return None

        if routed.get("action_category") in {"PROFILE", "ENTITY"}:
            profile = self._profile_for_update(session, target.entity_id)
            if target.entity_id == "e_boss" and action_detail in {"name", "identity"}:
                old_trait = self._latest_single_value_trait(session, target.entity_id, {"name", "identity"})
                if old_trait and old_trait != new_trait:
                    review_type = "CONFLICT"
                    requires_review = True
                elif old_trait and old_trait == new_trait:
                    routed["_drop_event"] = True
                    return None
            if target.entity_id == "e_boss" and action_detail in self.SINGLE_VALUE_PREFERENCE_DETAILS:
                old_trait = self._latest_single_value_trait(session, target.entity_id, {action_detail})
                if old_trait and old_trait != new_trait:
                    review_type = "CONFLICT"
                    requires_review = True
                elif old_trait and old_trait == new_trait:
                    routed["_drop_event"] = True
                    return None
            if target.entity_id == "e_boss" and action_detail in self.NEGATIVE_PREFERENCE_DETAILS:
                conflict_trait = self._conflicting_preference_trait(session, target.entity_id, action_detail, new_trait)
                if conflict_trait:
                    old_trait = conflict_trait
                    review_type = "CONFLICT"
                    requires_review = True
            if not requires_review and self._is_duplicate(profile, category, new_trait):
                routed["_drop_event"] = True
                return None

        if not requires_review:
            return None

        expires_at = (datetime.now() + timedelta(days=self.PENDING_TTL_DAYS)).isoformat(timespec="seconds")
        return StagedEvent(
            stage_id=f"stage_{uuid.uuid4().hex[:12]}",
            status="PENDING",
            review_type=review_type,
            target_id=target.entity_id,
            action_category=routed.get("action_category", "PROFILE"),
            action_detail=routed.get("action_detail", "facts"),
            category=category,
            old_trait=old_trait,
            new_trait=new_trait,
            reason=routed.get("reason"),
            context=routed.get("context", ""),
            raw_reference=routed.get("raw_reference"),
            payload_json=_json_dump(routed),
            expires_at=expires_at,
        )

    def _build_merged_event(self, session, target, routed, status="MERGED", review_type=None, old_trait=None, action_detail=None):
        detail = action_detail or routed.get("action_detail", "facts")
        event = MemoryEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            actor_id="e_boss",
            target_id=target.entity_id,
            action_category=routed.get("action_category", "PROFILE"),
            action_detail=detail,
            context=routed.get("context", ""),
            raw_reference=routed.get("raw_reference"),
            payload_json=_json_dump(routed),
        )
        review = EventReview(
            event_id=event.event_id,
            status=status,
            review_type=review_type or routed.get("review_type") or "NEW",
            category=self._category_for_routed(routed),
            old_trait=old_trait,
            new_trait=routed.get("new_trait") or event.context,
            reason=routed.get("reason"),
        )
        return event, review

    def _build_event_from_stage(self, stage, status):
        payload = _json_load(stage.payload_json, {})
        payload["stage_id"] = stage.stage_id
        action_detail = "corrected_fact" if stage.review_type == "CONFLICT" else stage.action_detail
        event = MemoryEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            actor_id="e_boss",
            target_id=stage.target_id,
            action_category=stage.action_category,
            action_detail=action_detail,
            context=stage.context,
            raw_reference=stage.raw_reference,
            payload_json=_json_dump(payload),
        )
        review = EventReview(
            event_id=event.event_id,
            status=status,
            review_type=stage.review_type,
            category=stage.category,
            old_trait=stage.old_trait,
            new_trait=stage.new_trait,
            reason=stage.reason,
        )
        return event, review

    def resolve_review(self, event_id, decision):
        self.settle_expired_pending()
        if decision not in {"accept", "reject"}:
            return {"ok": False, "message": " 冲突处理失败：未知裁决动作。"}
        with Session(self.engine) as session:
            stage = session.get(StagedEvent, event_id)
            if stage:
                if stage.status != "PENDING":
                    return {"ok": False, "message": " 冲突处理失败：该记忆不是待决状态。"}
                if decision == "accept":
                    event, review = self._build_event_from_stage(stage, "MERGED")
                    stage.status = "MERGED"
                    stage.updated_at = _now()
                    session.add(event)
                    session.add(review)
                    session.add(stage)
                    self._apply_event_to_snapshots(session, event, review)
                    message = " 已同意修改：新记忆已写入。"
                else:
                    stage.status = "REJECTED"
                    stage.updated_at = _now()
                    session.add(stage)
                    message = " 已拒绝修改：旧记忆已保留。"
                self._set_meta(session, "last_settlement_time", _now())
                session.commit()
                return {"ok": True, "message": message, "queue": self.fetch_memory_items()}

            return {"ok": False, "message": " 冲突处理失败：找不到新版待审事件。"}

    def settle_expired_pending(self):
        now = datetime.now()
        with Session(self.engine) as session:
            expired = session.exec(
                select(StagedEvent).where(StagedEvent.status == "PENDING")
            ).all()
            changed = False
            for stage in expired:
                try:
                    expires_at = datetime.fromisoformat(stage.expires_at)
                except Exception:
                    continue
                if expires_at > now:
                    continue
                event, review = self._build_event_from_stage(stage, "AUTO_OVERWRITTEN")
                stage.status = "AUTO_OVERWRITTEN"
                stage.updated_at = _now()
                session.add(event)
                session.add(review)
                session.add(stage)
                self._apply_event_to_snapshots(session, event, review)
                changed = True
            if changed:
                self._set_meta(session, "last_settlement_time", _now())
                session.commit()

    def _profile_for_update(self, session, entity_id):
        snapshot = session.get(L2EntitySnapshot, entity_id)
        if not snapshot:
            snapshot = L2EntitySnapshot(entity_id=entity_id, core_profile_json=_json_dump(self.empty_profile()))
            session.add(snapshot)
            session.flush()
        profile = _json_load(snapshot.core_profile_json, self.empty_profile())
        for key in self.PROFILE_KEYS:
            if not isinstance(profile.get(key), list):
                profile[key] = []
        return profile

    def _apply_event_to_snapshots(self, session, event, review):
        payload = _json_load(event.payload_json, {})
        if event.action_category == "ARCHIVE":
            snapshot = session.get(L2EntitySnapshot, event.target_id)
            if snapshot:
                snapshot.is_archived = True
                snapshot.last_event_id = event.event_id
                snapshot.last_updated = _now()
                session.add(snapshot)
            relation_id = payload.get("relationship_id")
            if relation_id:
                rel = session.get(Relationship, relation_id)
                if rel:
                    rel.status = "ARCHIVED"
                    rel.archived_at = _now()
                    rel.updated_at = _now()
                    session.add(rel)
            return

        if event.action_category == "COGNITIVE":
            domain = payload.get("domain") or review.category or "General"
            snapshot = session.get(L2CognitiveSnapshot, domain)
            if not snapshot:
                snapshot = L2CognitiveSnapshot(domain=domain)
            text = self._cognition_text(payload.get("new_cognition") or event.context)
            route_category = (payload.get("route_category") or "LEARN").upper()
            if route_category in {"PLAN", "LEARN"}:
                snapshot.macro_vision = text
            elif route_category in {"BUILD", "DEBUG"}:
                snapshot.current_focus = text
            snapshot.current_status = payload.get("current_status") or "ACTIVE"
            snapshot.last_event_id = event.event_id
            snapshot.last_updated = _now()
            session.add(snapshot)
            self._rebuild_cognitive_snapshot(session, domain, event.event_id)
            return

        if event.action_category in {"RELATION", "ENTITY"} and payload.get("relation_type"):
            self._apply_relationship_edge(session, event, payload)

        if event.action_category not in {"PROFILE", "ENTITY", "RELATION"}:
            return

        snapshot = session.get(L2EntitySnapshot, event.target_id)
        if not snapshot:
            snapshot = L2EntitySnapshot(entity_id=event.target_id, core_profile_json=_json_dump(self.empty_profile()))
        profile = _json_load(snapshot.core_profile_json, self.empty_profile())
        category = review.category if review.category in self.PROFILE_KEYS else "facts"
        for key in self.PROFILE_KEYS:
            if not isinstance(profile.get(key), list):
                profile[key] = []
        if review.old_trait and review.old_trait in profile[category]:
            profile[category].remove(review.old_trait)
        if review.new_trait and review.new_trait not in profile[category]:
            profile[category].append(review.new_trait)
        snapshot.core_profile_json = _json_dump(profile)
        snapshot.last_event_id = event.event_id
        snapshot.last_updated = _now()
        session.add(snapshot)
        self._rebuild_entity_profile_snapshot(session, event.target_id, event.event_id)

    def _rebuild_entity_profile_snapshot(self, session, entity_id, event_id=None):
        snapshot = session.get(L2EntitySnapshot, entity_id)
        if not snapshot:
            snapshot = L2EntitySnapshot(entity_id=entity_id, core_profile_json=_json_dump(self.empty_profile()))
        profile = self.empty_profile()
        single_value_traits = {}
        rows = session.exec(
            select(MemoryEvent, EventReview)
            .join(EventReview, EventReview.event_id == MemoryEvent.event_id)
            .where(
                MemoryEvent.target_id == entity_id,
                MemoryEvent.action_category.in_(["PROFILE", "ENTITY", "RELATION"]),
                EventReview.status.in_(["MERGED", "AUTO_OVERWRITTEN"]),
            )
            .order_by(MemoryEvent.timestamp.asc())
        ).all()
        for memory_event, review in rows:
            value = review.new_trait or memory_event.context
            if not value:
                continue
            category = review.category if review.category in self.PROFILE_KEYS else "facts"
            payload = _json_load(memory_event.payload_json, {})
            detail = (payload.get("action_detail") or memory_event.action_detail or "").lower()
            if detail in {"name", "identity"}:
                previous = single_value_traits.get(detail)
                if previous and previous in profile[category]:
                    profile[category].remove(previous)
                single_value_traits[detail] = value
            if value not in profile[category]:
                profile[category].append(value)
        snapshot.core_profile_json = _json_dump(profile)
        if event_id:
            snapshot.last_event_id = event_id
        snapshot.last_updated = _now()
        session.add(snapshot)

    def _apply_relationship_edge(self, session, event, payload):
        relation_type = payload.get("relation_type")
        source_entity = payload.get("source_entity") or "Boss"
        source = self.get_entity_by_name(session, source_entity)
        if relation_type in MemoryRouter.SINGLE_VALUE_RELATIONS:
            rows = session.exec(
                select(Relationship).where(
                    Relationship.source_id == source.entity_id,
                    Relationship.relation_type == relation_type,
                    Relationship.status == "ACTIVE",
                    Relationship.archived_at == None,  # noqa: E711
                )
            ).all()
            for row in rows:
                if row.target_id != event.target_id:
                    row.status = "ARCHIVED"
                    row.archived_at = _now()
                    row.updated_at = _now()
                    session.add(row)

        current = session.exec(
            select(Relationship).where(
                Relationship.source_id == source.entity_id,
                Relationship.target_id == event.target_id,
                Relationship.relation_type == relation_type,
                Relationship.status == "ACTIVE",
                Relationship.archived_at == None,  # noqa: E711
            )
        ).first()
        if not current:
            current = Relationship(
                source_id=source.entity_id,
                target_id=event.target_id,
                relation_type=relation_type,
            )
        current.status = "ACTIVE"
        current.confidence = float(payload.get("confidence", 1.0) or 0)
        current.source_event_id = event.event_id
        current.properties_json = _json_dump({
            "context": event.context,
            "target_entity": payload.get("target_entity"),
            "role_name": payload.get("role_name"),
        })
        current.updated_at = _now()
        session.add(current)
        session.flush()
        self._refresh_active_relations(session, source.entity_id, event.event_id)

    def _latest_single_value_trait(self, session, target_id, action_details):
        rows = session.exec(
            select(MemoryEvent, EventReview)
            .join(EventReview, EventReview.event_id == MemoryEvent.event_id)
            .where(
                MemoryEvent.target_id == target_id,
                EventReview.status.in_(["MERGED", "AUTO_OVERWRITTEN"]),
            )
            .order_by(MemoryEvent.timestamp.desc())
        ).all()
        for event, review in rows:
            payload = _json_load(event.payload_json, {})
            detail = (payload.get("action_detail") or event.action_detail or "").lower()
            if detail not in action_details:
                continue
            value = review.new_trait or event.context
            if value:
                return value
        return None

    def _category_for_routed(self, routed):
        category = routed.get("category")
        detail = str(routed.get("action_detail") or "").lower()
        if category in self.PROFILE_KEYS:
            return category
        if detail in self.PREFERENCE_DETAILS or detail == "interests":
            return "interests"
        if detail in {"communication", "coding_style"}:
            return detail
        return "facts"

    def _conflicting_preference_trait(self, session, target_id, action_detail, new_trait):
        new_object = MemoryRouter.preference_object(action_detail, new_trait)
        if not new_object:
            return None
        rows = session.exec(
            select(MemoryEvent, EventReview)
            .join(EventReview, EventReview.event_id == MemoryEvent.event_id)
            .where(
                MemoryEvent.target_id == target_id,
                MemoryEvent.action_category == "PROFILE",
                EventReview.status.in_(["MERGED", "AUTO_OVERWRITTEN"]),
            )
            .order_by(MemoryEvent.timestamp.desc())
        ).all()
        positive_details = self.SINGLE_VALUE_PREFERENCE_DETAILS | {"interests", "food_preference"}
        for event, review in rows:
            payload = _json_load(event.payload_json, {})
            detail = (payload.get("action_detail") or event.action_detail or "").lower()
            if detail not in positive_details:
                continue
            old_trait = review.new_trait or event.context
            if MemoryRouter.preference_object(detail, old_trait) == new_object:
                return old_trait
        return None

    def _refresh_active_relations(self, session, source_id, event_id=None):
        snapshot = session.get(L2EntitySnapshot, source_id)
        if not snapshot:
            snapshot = L2EntitySnapshot(entity_id=source_id, core_profile_json=_json_dump(self.empty_profile()))
        rows = session.exec(
            select(Relationship).where(
                Relationship.source_id == source_id,
                Relationship.status == "ACTIVE",
                Relationship.archived_at == None,  # noqa: E711
            )
        ).all()
        active = []
        for row in rows:
            target = session.get(Entity, row.target_id)
            active.append({
                "relationship_id": row.rel_id,
                "relation_type": row.relation_type,
                "target_id": row.target_id,
                "target_name": target.name if target else row.target_id,
                "confidence": row.confidence,
            })
        snapshot.active_relations_json = _json_dump(active)
        if event_id:
            snapshot.last_event_id = event_id
        snapshot.last_updated = _now()
        session.add(snapshot)

    def _cognition_text(self, value):
        if isinstance(value, dict):
            parts = []
            if value.get("current_bottlenecks"):
                parts.append("当前卡点: " + ", ".join(map(str, value["current_bottlenecks"])))
            if value.get("mental_model"):
                parts.append("心智模型: " + str(value["mental_model"]))
            if value.get("actionable_insight"):
                parts.append("对接策略: " + str(value["actionable_insight"]))
            return "\n".join(parts) or json.dumps(value, ensure_ascii=False)
        return str(value or "")

    def _rebuild_cognitive_snapshot(self, session, domain, event_id=None):
        rows = session.exec(
            select(MemoryEvent, EventReview)
            .join(EventReview, EventReview.event_id == MemoryEvent.event_id)
            .where(
                MemoryEvent.action_category == "COGNITIVE",
                EventReview.status.in_(["MERGED", "AUTO_OVERWRITTEN"]),
            )
            .order_by(MemoryEvent.timestamp.asc())
        ).all()
        macro_parts = []
        focus_parts = []
        for memory_event, review in rows:
            payload = _json_load(memory_event.payload_json, {})
            if (payload.get("domain") or review.category or "General") != domain:
                continue
            text = self._cognition_text(payload.get("new_cognition") or memory_event.context)
            if not text:
                continue
            route_category = (payload.get("route_category") or "LEARN").upper()
            if route_category in {"PLAN", "LEARN"}:
                macro_parts.append(text)
            elif route_category in {"BUILD", "DEBUG"}:
                focus_parts.append(text)
        snapshot = session.get(L2CognitiveSnapshot, domain) or L2CognitiveSnapshot(domain=domain)
        snapshot.macro_vision = "\n".join(dict.fromkeys(macro_parts[-5:]))
        snapshot.current_focus = "\n".join(dict.fromkeys(focus_parts[-5:]))
        snapshot.current_status = "ACTIVE"
        if event_id:
            snapshot.last_event_id = event_id
        snapshot.last_updated = _now()
        session.add(snapshot)

    def _is_duplicate(self, profile, category, new_trait):
        if category not in profile or not new_trait:
            return False
        new_key = MemoryRouter.normalize_trait(new_trait)
        return any(MemoryRouter.normalize_trait(item) == new_key for item in profile.get(category, []))

    def _active_relationship(self, session, source_id, relation_type):
        return session.exec(
            select(Relationship).where(
                Relationship.source_id == source_id,
                Relationship.relation_type == relation_type,
                Relationship.status == "ACTIVE",
                Relationship.archived_at == None,  # noqa: E711
            )
        ).first()

    def _set_meta(self, session, key, value):
        meta = session.get(MemoryMeta, key) or MemoryMeta(key=key)
        meta.value = value
        meta.updated_at = _now()
        session.add(meta)


class MemoryRouter:
    SELF_ENTITIES = {"我", "用户", "Boss", "BOSS", "boss", "Master", "主人", "本尊", "自己", "本人", "创造者"}
    RELATION_ALIASES = {
        "father": ("父亲", "爸爸", "爸", "爹", "老爸", "father"),
        "mother": ("母亲", "妈妈", "妈", "娘", "老妈", "mother"),
        "partner": ("妻子", "老婆", "丈夫", "老公", "女朋友", "男朋友", "伴侣"),
        "child": ("儿子", "女儿", "孩子", "小孩"),
        "friend": ("朋友", "好友", "同学", "同事"),
        "boss": ("老板", "上司", "领导"),
        "project": ("项目", "工程", "产品"),
        "uses_tech": ("技术栈", "框架", "语言", "工具"),
    }
    SINGLE_VALUE_RELATIONS = {"father", "mother", "partner", "boss"}
    ROLE_ENTITY_BY_RELATION = {
        "father": "父亲",
        "mother": "母亲",
        "partner": "伴侣",
        "child": "孩子",
        "friend": "朋友",
        "boss": "老板",
        "project": "项目",
        "uses_tech": "技术栈",
    }
    ENTITY_ALIASES = {
        "父亲": ("父亲", "爸爸", "爸", "爹", "老爸", "father"),
        "母亲": ("母亲", "妈妈", "妈", "娘", "老妈", "mother"),
        "朋友": ("朋友", "好友", "同学", "同事"),
        "老板": ("老板", "上司", "领导"),
        "伴侣": ("妻子", "老婆", "丈夫", "老公", "女朋友", "男朋友", "伴侣"),
        "孩子": ("儿子", "女儿", "孩子", "小孩"),
    }
    ENTITY_GROUPS = {
        "父母": ("父亲", "母亲"),
        "双亲": ("父亲", "母亲"),
        "爸妈": ("父亲", "母亲"),
        "家人": ("父亲", "母亲", "伴侣", "孩子"),
        "亲人": ("父亲", "母亲", "伴侣", "孩子"),
    }
    NAME_STOP_WORDS = {"用户", "名字", "姓名", "真实姓名", "父亲", "母亲", "爸爸", "妈妈", "朋友", "老板", "喜欢", "讨厌", "不是", "不知道", "什么", "多少", "谁", "吗", "呢"}

    @classmethod
    def resolve_relation_types(cls, text):
        text = str(text or "")
        matched = set()
        for relation_type, aliases in cls.RELATION_ALIASES.items():
            if any(alias in text for alias in aliases):
                matched.add(relation_type)
        return sorted(matched)

    @classmethod
    def aliases_for(cls, entity_name):
        if entity_name == "Boss":
            return list(cls.SELF_ENTITIES)
        return list(cls.ENTITY_ALIASES.get(entity_name, (entity_name,)))

    @classmethod
    def normalize_entity(cls, entity):
        if not entity:
            return "Boss"
        text = str(entity).strip()
        if text in cls.SELF_ENTITIES:
            return "Boss"
        for canonical, aliases in cls.ENTITY_ALIASES.items():
            if text == canonical or text in aliases:
                return canonical
        return text

    @classmethod
    def sanitize_entity_name(cls, entity):
        name = cls.normalize_entity(entity)
        if name == "Boss":
            return "Boss"
        if not name or len(name) > 40:
            return None
        if name in {".", ".."} or ".." in name:
            return None
        if any(ch in name for ch in ('/', '\\', ':', '*', '?', '"', '<', '>', '|')):
            return None
        return name

    @classmethod
    def normalize_trait(cls, trait):
        text = str(trait or "").strip()
        text = re.sub(r"^(用户|Boss|我|本人|自己)的?", "", text)
        text = text.replace("最爱吃的水果是", "喜欢吃")
        text = text.replace("最喜欢吃的水果是", "喜欢吃")
        text = text.replace("最喜欢的水果是", "喜欢吃")
        text = text.replace("爱吃", "喜欢吃")
        return re.sub(r"[，,。.!！?？\s]", "", text)

    @classmethod
    def preference_object(cls, action_detail, trait):
        text = cls.normalize_trait(trait)
        for token in (
            "最不喜欢吃", "不喜欢吃", "讨厌吃",
            "最喜欢吃", "最爱吃", "喜欢吃", "爱吃",
            "最不喜欢", "不喜欢", "讨厌",
            "最喜欢", "最爱", "喜欢", "爱",
            "水果是",
        ):
            text = text.replace(token, "")
        text = re.sub(r"^(用户|Boss|我|本人|自己)", "", text)
        return text.strip()

    def route(self, candidate, llm_router=None):
        if not isinstance(candidate, dict):
            return None
        if "target_entity" in candidate and "action_category" in candidate:
            return self._normalize_routed(candidate)

        if llm_router:
            routed = llm_router(candidate)
            if isinstance(routed, list):
                routed = routed[0] if routed else None
            if isinstance(routed, dict):
                return self._normalize_routed(routed)
        return None

    def _normalize_routed(self, routed):
        target = self.sanitize_entity_name(routed.get("target_entity")) or "Boss"
        action_category = str(routed.get("action_category") or "PROFILE").upper()
        if action_category in {"PLAN", "LEARN", "BUILD", "DEBUG"}:
            routed["route_category"] = action_category
            action_category = "COGNITIVE"
        routed["target_entity"] = target
        routed["action_category"] = action_category
        routed["action_detail"] = str(routed.get("action_detail") or routed.get("category") or "facts")[:100]
        routed["context"] = str(routed.get("context") or routed.get("new_trait") or "")[:2000]
        routed["new_trait"] = str(routed.get("new_trait") or routed.get("context") or "")[:2000]
        try:
            routed["confidence"] = float(routed.get("confidence", 1.0))
        except Exception:
            routed["confidence"] = 0.0
        routed["requires_review"] = bool(routed.get("requires_review"))
        return routed

    def resolve_entities(self, text, known_entities):
        text = str(text or "")
        if isinstance(known_entities, dict):
            known_aliases = known_entities
            known_names = set(known_entities)
        else:
            known_names = set(known_entities or [])
            known_aliases = {name: self.ENTITY_ALIASES.get(name, (name,)) for name in known_names}
        matched = set()
        for group_word, group_entities in self.ENTITY_GROUPS.items():
            if group_word in text:
                if group_word in {"家人", "亲人"}:
                    matched.update(entity for entity in group_entities if entity in known_names)
                else:
                    matched.update(group_entities)
        for entity_name, aliases in known_aliases.items():
            if entity_name in text or any(alias in text for alias in aliases):
                matched.add(entity_name)
        return sorted(entity for entity in matched if self.sanitize_entity_name(entity) and entity != "Boss")


class MemorySettlementService:
    def __init__(self, repo):
        self.repo = repo

    def submit_routed_event(self, routed):
        return self.repo.submit_event(routed)

    def resolve_review(self, memory_id, decision):
        return self.repo.resolve_review(memory_id, decision)


class MemoryGatekeeper:
    def __init__(self, repo=None):
        self.repo = repo or MemoryRepository()
        self.router = MemoryRouter()
        self.settlement = MemorySettlementService(self.repo)
        self.memory_lock = threading.RLock()

    def check_and_promote(self, candidates=None, llm_caller=None, entity_callback=None, llm_router=None, raw_reference=None):
        from trace_system import trace_emitter

        results = []
        with self.memory_lock:
            self.repo.settle_expired_pending()
            if not candidates:
                return []
            if isinstance(candidates, dict):
                candidates = [candidates]
            for candidate in candidates:
                route_span = trace_emitter.start_span(
                    "MEMORY_ROUTE",
                    "判断记忆类别与目标实体",
                    {"action": candidate.get("action")}
                )
                routed = self.router.route(candidate, llm_router=llm_router)
                if not routed:
                    route_span.finish("SUCCESS", "记忆候选已忽略", {"status": "ignored"})
                    continue
                route_span.finish(
                    "SUCCESS",
                    f"归类为 {routed.get('target_entity') or 'Boss'} {routed.get('category') or routed.get('action_detail') or 'facts'}",
                    {
                        "entity": routed.get("target_entity") or "Boss",
                        "category": routed.get("category") or routed.get("action_detail") or "facts",
                        "action": routed.get("action_category") or "PROFILE",
                    }
                )
                routed["raw_reference"] = raw_reference
                review_span = trace_emitter.start_span(
                    "MEMORY_REVIEW",
                    "判断记忆审核状态",
                    {
                        "entity": routed.get("target_entity") or "Boss",
                        "category": routed.get("category") or routed.get("action_detail") or "facts",
                    }
                )
                write_span = trace_emitter.start_span(
                    "MEMORY_WRITE",
                    "写入记忆事件",
                    {
                        "entity": routed.get("target_entity") or "Boss",
                        "category": routed.get("category") or routed.get("action_detail") or "facts",
                    }
                )
                try:
                    event_id, status = self.settlement.submit_routed_event(routed)
                except Exception as e:
                    review_span.finish("FAILED", "记忆审核失败", {"error": str(e)[:120]})
                    write_span.finish("FAILED", "记忆写入失败", {"error": str(e)[:120]})
                    raise
                status_text = {
                    "MERGED": "已写入画像事件源",
                    "PENDING": "已进入待审队列",
                    "REJECTED": "未写入重复信息",
                }.get(status, f"写入状态 {status}")
                review_span.finish("SUCCESS", status_text, {"status": status})
                write_span.finish("SUCCESS", status_text, {"status": status})
                settle_span = trace_emitter.start_span("MEMORY_SETTLE", "更新画像快照", {"status": status})
                settle_message = "画像快照已更新" if status == "MERGED" else "等待后续结算"
                if status == "REJECTED":
                    settle_message = "无需更新画像快照"
                settle_span.finish("SUCCESS", settle_message, {"status": status})
                results.append({"id": event_id, "status": status})
        return results

    def enqueue_memory_observation(self, text, thread_id="global"):
        return self.repo.append_buffer_item(text, thread_id=thread_id)

    def flush_event_buffer(self, extractor, force=False):
        with self.memory_lock:
            return self.repo.flush_event_buffer(extractor, force=force)

    def submit_standard_events(self, events, raw_reference=None):
        normalized = []
        for event in events or []:
            if not isinstance(event, dict):
                continue
            item = dict(event)
            if raw_reference and not item.get("raw_reference"):
                item["raw_reference"] = raw_reference
            normalized.append(item)
        with self.memory_lock:
            return self.repo.submit_events_grouped(normalized)

    def resolve_memory_conflict(self, memory_id, decision):
        with self.memory_lock:
            return self.settlement.resolve_review(memory_id, decision)

    def fetch_memory(self):
        return self.repo.fetch_memory_items()

    def get_boss_profile(self):
        return self.repo.get_profile("Boss")

    def get_entity_profile(self, entity_name):
        return self.repo.get_profile(entity_name)

    def get_entity_snapshot_text(self, entity_name):
        return self.repo.get_entity_snapshot_text(entity_name)

    def get_l2_context_text(self, user_input):
        return self.repo.get_l2_context_text(user_input)

    def get_cognitive_snapshots(self):
        return self.repo.get_all_cognitive_snapshots()

    def resolve_entities(self, text):
        with Session(self.repo.engine) as session:
            known = {row.name: _json_load(row.aliases_json, []) for row in session.exec(select(Entity)).all()}
        return self.router.resolve_entities(text, known)

    def sanitize_entity_name(self, entity):
        return self.router.sanitize_entity_name(entity)

    def create_manual_event(self, user_command):
        routed = {
            "target_entity": "Boss",
            "action_category": "PROFILE",
            "action_detail": "facts",
            "category": "facts",
            "context": user_command,
            "new_trait": user_command,
            "confidence": 0.5,
            "requires_review": True,
            "review_type": "MANUAL",
            "reason": "memory_surgery",
        }
        event_id, _ = self.settlement.submit_routed_event(routed)
        return event_id

    def process_import_traits(self, traits):
        if isinstance(traits, dict):
            traits = [traits]
        return self.check_and_promote(traits or [], raw_reference="profile_import")
