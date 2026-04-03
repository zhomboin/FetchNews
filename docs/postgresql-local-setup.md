# 鏈湴 PostgreSQL 閰嶇疆璇存槑

鏈枃妗ｈ鏄庡綋鍓嶉」鐩浣曞湪鏈湴浣跨敤 PostgreSQL銆佸湪鍝噷閰嶇疆銆侀渶瑕佹墽琛屽摢浜涘垵濮嬪寲 SQL锛屼互鍙?Alembic 涓庡簲鐢ㄥ垵濮嬪寲鐨勮竟鐣屻€?
## 1. PostgreSQL 鍦ㄥ摢閲岄厤缃?
褰撳墠瀹為檯鐢熸晥鐨勬暟鎹簱閰嶇疆椤规槸锛?
- `APP_DATABASE_URL`

甯歌浣嶇疆锛?
- 椤圭洰鏍圭洰褰?`.env`
- `docker-compose.yml` 涓紶鍏ョ殑鐜鍙橀噺
- 鏈湴鎵嬪姩鍚姩鍛戒护涓殑鐜鍙橀噺瑕嗙洊

鎺ㄨ崘鐨勬湰鍦?`.env` 鍐欐硶锛?
```env
APP_DATABASE_URL=postgresql+psycopg://fetchnews:fetchnews@localhost:5432/fetchnews
APP_DATABASE_BOOTSTRAP_MODE=skip
```

鍚箟锛?
- 浣跨敤瀹夸富鏈烘湰鍦?PostgreSQL
- 搴旂敤涓嶅啀鑷繁鍒涘缓 schema锛岃€屾槸浜ょ粰 Alembic

## 2. Compose 閲屽浣曡繛鎺ュ涓绘満 PostgreSQL

褰撳墠 Compose 宸叉敼涓鸿繛鎺ュ涓绘満鏁版嵁搴擄紝涓嶅啀榛樿鍚姩 PostgreSQL 瀹瑰櫒銆?
搴旂敤瀹瑰櫒浣跨敤锛?
```env
APP_DATABASE_URL=postgresql+psycopg://fetchnews:fetchnews@host.docker.internal:5432/fetchnews
```

杩欐剰鍛崇潃锛?
- `api`銆乣worker`銆乣beat` 浼氳繛鎺ヤ綘鏈満 PostgreSQL
- `redis` 浠嶅彲鐢?Compose 鍚姩
- 鍚姩鍓嶉渶瑕佺‘淇濆涓绘満 PostgreSQL 宸茶繍琛?
## 3. 鏈疆蹇呴』鎵嬪姩鎵ц鐨勫垵濮嬪寲 SQL

### 3.1 鍏ㄦ柊鏈湴 PostgreSQL

濡傛灉鏈湴 PostgreSQL 杩樻病鏈夊噯澶囧ソ锛屽厛鍦?`psql` 涓墽琛岋細

```sql
CREATE USER fetchnews WITH PASSWORD 'fetchnews';
CREATE DATABASE fetchnews OWNER fetchnews;
GRANT ALL PRIVILEGES ON DATABASE fetchnews TO fetchnews;
\connect fetchnews
GRANT ALL ON SCHEMA public TO fetchnews;
ALTER SCHEMA public OWNER TO fetchnews;
```

杩欏嚑鏉?SQL 鐨勪綔鐢細

- 鍒涘缓鏁版嵁搴撶敤鎴?`fetchnews`
- 鍒涘缓鏁版嵁搴?`fetchnews`
- 灏嗘暟鎹簱鎵€鏈夋潈浜ょ粰璇ョ敤鎴?- 灏?`public` schema 鏉冮檺鍜屾墍鏈夋潈浜ょ粰璇ョ敤鎴?
### 3.2 瑙掕壊鍜屾暟鎹簱宸插瓨鍦ㄦ椂

濡傛灉瑙掕壊鍜屾暟鎹簱宸茬粡瀛樺湪锛屽彧闇€瑕佹洿鏂板畠浠細

```sql
ALTER USER fetchnews WITH PASSWORD 'fetchnews';
ALTER DATABASE fetchnews OWNER TO fetchnews;
\connect fetchnews
GRANT ALL ON SCHEMA public TO fetchnews;
ALTER SCHEMA public OWNER TO fetchnews;
```

## 4. 鍝簺鍐呭涓嶅簲璇ユ墜鍐?SQL

鏈疆涓嶉渶瑕佹墜鍔ㄦ墽琛屽缓琛?SQL銆?
鍘熷洜锛?
- 涓氬姟琛ㄧ粨鏋勭粺涓€鐢?Alembic 鍒涘缓
- 杩佺Щ鍛戒护鏄細

```bash
alembic upgrade head
```

鍥犳锛屾墜鍔?SQL 浠呴檺锛?
- 瑙掕壊鍒涘缓
- 鏁版嵁搴撳垱寤?- schema 鏉冮檺涓庢墍鏈夋潈閰嶇疆

涓氬姟琛ㄣ€佺储寮曚笌鍚庣画 schema 鍙樻洿閮藉簲杩涘叆 Alembic migration銆?
## 5. Bootstrap Admin 鏄惁闇€瑕佹墜鍐?SQL

涓嶉渶瑕併€?
褰撳墠绠＄悊鍛樿处鍙风敱搴旂敤鍚姩闃舵鏍规嵁鐜鍙橀噺鑷姩琛ラ綈锛岀浉鍏冲彉閲忓寘鎷細

- `APP_BOOTSTRAP_ADMIN_USERNAME`
- `APP_BOOTSTRAP_ADMIN_PASSWORD`
- `APP_BOOTSTRAP_ADMIN_DISPLAY_NAME`

涔熷氨鏄锛?
- 鏁版嵁搴撹鑹插拰搴撻渶瑕佷綘鎵嬪姩鍑嗗
- 搴旂敤琛ㄧ粨鏋勭敱 Alembic 鍒涘缓
- 绠＄悊鍛樿处鍙风敱搴旂敤鍒濆鍖栭€昏緫鑷姩鍒涘缓鎴栨洿鏂?
## 6. 鎺ㄨ崘鍚姩椤哄簭

### 浣跨敤 Compose

```bash
docker compose run --rm migrate
docker compose up api worker beat web redis
```

### 鎵嬪姩鍚姩

```bash
alembic upgrade head
uvicorn fetchnews.main:app --host 0.0.0.0 --port 8000 --reload
celery -A fetchnews.tasks.worker.celery_app worker --loglevel=info
celery -A fetchnews.tasks.worker.celery_app beat --loglevel=info
cd web
npm run dev -- --host 0.0.0.0
```

## 7. 濡備綍楠岃瘉 PostgreSQL 宸叉纭帴鍏?
鎵ц杩佺Щ鍚庯紝鍙互鍦?`psql` 涓鏌ワ細

```sql
\dt
SELECT version_num FROM alembic_version;
SELECT username, role, is_active FROM users ORDER BY id;
```

棰勬湡缁撴灉锛?
- 鑳界湅鍒颁笟鍔¤〃
- `alembic_version` 鏈夊綋鍓嶇増鏈彿
- `users` 琛ㄤ腑鏈?bootstrap 绠＄悊鍛樿处鍙?
## 8. 褰撳墠涓轰綍涓嶄娇鐢?SQLite

褰撳墠椤圭洰渚濈劧鏀寔 `SQLite` 浣滀负娴嬭瘯鎴栦复鏃惰矾寰勶紝浣嗘湰鍦板紑鍙戞寮忔帹鑽?PostgreSQL锛屽師鍥犳槸锛?
- 褰撳墠宸ヤ綔娴佸凡缁忔秹鍙?Alembic銆侀壌鏉冦€佸璁′笌鏇存帴杩戠敓浜х殑 schema 婕旇繘
- 鍚庣画杩樹細寮曞叆鏇村鏉傜殑缂栬緫鍘嗗彶銆佹ā鏉垮拰鍙戝竷璁板綍
- PostgreSQL 鎵嶆槸褰撳墠浠撳簱鐨勪富璺緞

## 9. 鏂囨。绾︽潫

- PostgreSQL 閰嶇疆鏂囨。缁熶竴浣跨敤涓枃
- 淇濈暀 SQL銆佺幆澧冨彉閲忓拰宸ュ叿鍛戒护鍘熸枃锛屼絾璇存槑蹇呴』浣跨敤涓枃
## 10. 2026-04-03 编辑工作台迁移说明

本轮新增了两条 Alembic migration：

- `20260403_0002_editorial_workbench.py`
- `20260403_0003_article_draft_templates.py`

它们负责创建和扩展以下结构：

- `digest_templates`
- `article_revisions`
- `article_blocks`
- `editorial_actions`
- `article_drafts.template_id`
- `article_drafts.active_revision_id`

这轮**不需要新增手工 SQL**。仍然只需要完成：

1. PostgreSQL 角色、数据库、schema 权限初始化
2. 执行 `alembic upgrade head`

也就是说，编辑工作台相关表和字段全部由 Alembic 创建，不要手工在 `psql` 里补 DDL。