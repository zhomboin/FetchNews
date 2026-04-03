# 宸ョ▼涓庤繍缁村熀绾?
鏈枃妗ｆ€荤粨褰撳墠浠撳簱宸茬粡鍏峰鐨勫伐绋嬩笌杩愮淮琛ラ綈鑳藉姏銆?
## 鏈疆鍩虹嚎鍖呭惈鐨勫唴瀹?
### Alembic 杩佺Щ

宸插疄鐜帮細

- Alembic 閰嶇疆涓庣幆澧冩枃浠?- 瀵瑰簲褰撳墠 SQLAlchemy 妯″瀷闆嗙殑棣栦釜 schema migration
- 鏄惧紡鍖哄垎 `SQLite` 娴嬭瘯寮曞涓?PostgreSQL 杩佺Щ娴佺▼

鍏抽敭鏂囦欢锛?
- [alembic.ini](/D:/Code/Project/FetchNews/alembic.ini)
- [alembic/env.py](/D:/Code/Project/FetchNews/alembic/env.py)
- [alembic/versions/20260401_0001_initial_schema.py](/D:/Code/Project/FetchNews/alembic/versions/20260401_0001_initial_schema.py)
- [fetchnews/db/session.py](/D:/Code/Project/FetchNews/fetchnews/db/session.py)

鏈疆 SQL 杈圭晫锛?
- 鎵嬪姩 SQL 浠呴檺 PostgreSQL 瑙掕壊銆佹暟鎹簱涓?schema 鏉冮檺鍒濆鍖?- 涓氬姟琛ㄧ粨鏋勭粺涓€閫氳繃 Alembic 鍒涘缓锛屼笉鎵嬪伐绮樿创 DDL 鍒?`psql`
- 鍏蜂綋 SQL 瑙?[docs/postgresql-local-setup.md](/D:/Code/Project/FetchNews/docs/postgresql-local-setup.md)

### PostgreSQL 姝ｅ紡鍖?
宸插疄鐜帮細

- 瀹夸富鏈?PostgreSQL 浣滀负鎺ㄨ崘鏈湴鏁版嵁搴撹矾寰?- Compose 涓嶅啀榛樿鎷夎捣 PostgreSQL 瀹瑰櫒
- 鏄惧紡鏀寔 `APP_DATABASE_BOOTSTRAP_MODE`
- 涓?Compose 娴佺▼鎻愪緵 `migrate` 鏈嶅姟

鍏抽敭鏂囦欢锛?
- [docker-compose.yml](/D:/Code/Project/FetchNews/docker-compose.yml)
- [.env.example](/D:/Code/Project/FetchNews/.env.example)
- [docs/postgresql-local-setup.md](/D:/Code/Project/FetchNews/docs/postgresql-local-setup.md)

### 鐧诲綍銆佹潈闄愪笌瀹¤

宸插疄鐜帮細

- 閴存潈寮€鍏虫帴鍙ｏ細`GET /auth/config`
- 鐧诲綍鎺ュ彛锛歚POST /auth/login`
- 褰撳墠鐢ㄦ埛鎺ュ彛锛歚GET /auth/me`
- 鍙椾繚鎶?API 鐨勮鑹叉潈闄愭帶鍒?- 閫氳繃鐜鍙橀噺寮曞鍒涘缓绠＄悊鍛樿处鍙?- 瀵瑰叧閿啓鎿嶄綔鎸佷箙鍖栧璁℃棩蹇?
褰撳墠瑙掕壊锛?
- `viewer`锛氬彧璇?API 璁块棶
- `editor`锛氬鏍搞€佺敓鎴愩€佸彂甯冨拰鎵嬪姩杩愮淮鎿嶄綔
- `admin`锛氬畬鏁存潈闄愶紝褰撳墠鐢ㄤ簬 bootstrap 鐧诲綍

鍏抽敭鏂囦欢锛?
- [fetchnews/core/security.py](/D:/Code/Project/FetchNews/fetchnews/core/security.py)
- [fetchnews/core/audit.py](/D:/Code/Project/FetchNews/fetchnews/core/audit.py)
- [fetchnews/main.py](/D:/Code/Project/FetchNews/fetchnews/main.py)
- [fetchnews/models.py](/D:/Code/Project/FetchNews/fetchnews/models.py)

### 鍛婅涓庣洃鎺?
宸插疄鐜帮細

- ops summary 涓殑鍛婅
- 鏈€杩戝け璐ュ垎缁?- 骞冲彴鎸囨爣
- 鏍忕洰瀹℃牳鎸囨爣
- 寤鸿鍒楄〃
- 鍓嶇 ops 鍛婅鍗＄墖涓?drill-down 鏀寔

鍏抽敭鏂囦欢锛?
- [fetchnews/ops/service.py](/D:/Code/Project/FetchNews/fetchnews/ops/service.py)
- [web/src/features/ops/ops-dashboard-page.tsx](/D:/Code/Project/FetchNews/web/src/features/ops/ops-dashboard-page.tsx)

### 鍓嶇娴嬭瘯鍩虹嚎

宸插疄鐜帮細

- `Vitest` 娴嬭瘯杩愯鍣?- `Testing Library` 娴嬭瘯鐜
- API 閴存潈澶存祴璇?- 鐧诲綍琛ㄥ崟鎻愪氦娴佺▼娴嬭瘯

鍛戒护锛?
```bash
cd web
npm run test:run
```

鍏抽敭鏂囦欢锛?
- [web/package.json](/D:/Code/Project/FetchNews/web/package.json)
- [web/vite.config.ts](/D:/Code/Project/FetchNews/web/vite.config.ts)
- [web/src/lib/api.test.ts](/D:/Code/Project/FetchNews/web/src/lib/api.test.ts)
- [web/src/features/auth/login-page.test.tsx](/D:/Code/Project/FetchNews/web/src/features/auth/login-page.test.tsx)

## 浠嶅緟琛ラ綈鐨勮兘鍔?
灏氭湭瀹屽叏瀹屾垚锛?
- 鐢ㄦ埛绠＄悊 UI 涓庡瘑鐮侀噸缃祦绋?- 瀹¤鏃ュ織鏌ョ湅 UI 涓庡鍑烘帴鍙?- 閭欢銆乄ebhook銆丼lack 绛夊閮ㄥ憡璀﹂€氶亾
- `Prometheus / Grafana` 鎴?`Sentry` 绛夌敓浜х洃鎺ф爤
- 闀跨敓鍛藉懆鏈?PostgreSQL 鐜鐨勫垎闃舵杩佺Щ绛栫暐

## 鏂囨。璇█绾︽潫

- 宸ョ▼涓庤繍缁磋鏄庣粺涓€浣跨敤涓枃鎾板啓
- 淇濈暀鑻辨枃宸ュ叿鍚嶆椂闇€閰嶅悎涓枃璇箟璇存槑
## 2026-04-03 迁移增量

工程基线已增加编辑工作台的数据库演进能力，当前 migration 集包括：

- `20260401_0001_initial_schema.py`
- `20260403_0002_editorial_workbench.py`
- `20260403_0003_article_draft_templates.py`

新增覆盖的结构：

- digest 模板表
- 稿件 revision 表
- 稿件 block 表
- 人工干预动作表
- 稿件模板关联字段

本轮没有新增需要人工执行的业务 SQL，数据库层面的新增动作继续统一走 Alembic。