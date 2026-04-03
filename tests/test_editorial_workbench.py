from datetime import UTC, datetime

from fastapi.testclient import TestClient

from fetchnews.db.session import session_scope
from fetchnews.main import create_app
from fetchnews.models import DigestTemplate
from fetchnews.schemas import StoryCreatePayload
from fetchnews.settings import Settings


def _story_payload() -> dict:
    return StoryCreatePayload(
        story_key='editorial-workbench-weekly-1',
        cluster_title='Weekly digest should create an editable revision',
        summary='The weekly digest response should expose revision and block metadata.',
        highlights=['Covers revision bootstrap', 'Prepares block editor migration'],
        source_links=['https://example.com/editorial-workbench-weekly-1'],
        tags=['weekly', 'editorial'],
        risk_flags=[],
        score=9.1,
        item_count=1,
        first_seen_at=datetime(2026, 4, 3, 9, 0, tzinfo=UTC),
        last_seen_at=datetime(2026, 4, 3, 9, 0, tzinfo=UTC),
    ).model_dump(mode='json')


def test_generate_weekly_digest_creates_initial_revision_with_blocks() -> None:
    app = create_app(
        Settings(
            database_url='sqlite:///./test_editorial_workbench.db',
            redis_url='redis://localhost:6379/0',
            environment='test',
        )
    )

    with TestClient(app) as client:
        create_response = client.post('/stories', json=_story_payload())
        assert create_response.status_code == 201
        story_id = create_response.json()['id']
        assert client.post(f'/stories/{story_id}/approve').status_code == 200

        generate_response = client.post(
            '/articles/generate/weekly',
            json={'target_date': '2026-04-03'},
        )
        assert generate_response.status_code == 200

        payload = generate_response.json()
        assert payload['active_revision_id'] is not None
        assert payload['block_count'] > 0


def test_article_blocks_and_revisions_can_be_fetched() -> None:
    app = create_app(
        Settings(
            database_url='sqlite:///./test_editorial_workbench_read_models.db',
            redis_url='redis://localhost:6379/0',
            environment='test',
        )
    )

    with TestClient(app) as client:
        create_response = client.post('/stories', json=_story_payload())
        assert create_response.status_code == 201
        story_id = create_response.json()['id']
        assert client.post(f'/stories/{story_id}/approve').status_code == 200

        generate_response = client.post(
            '/articles/generate/weekly',
            json={'target_date': '2026-04-03'},
        )
        assert generate_response.status_code == 200
        article_payload = generate_response.json()
        article_id = article_payload['id']
        active_revision_id = article_payload['active_revision_id']

        blocks_response = client.get(f'/articles/{article_id}/blocks')
        assert blocks_response.status_code == 200
        blocks_payload = blocks_response.json()
        assert len(blocks_payload) == article_payload['block_count']
        assert any(block['block_type'] == 'title' for block in blocks_payload)
        assert any(block['block_type'] == 'story_paragraph' for block in blocks_payload)

        revisions_response = client.get(f'/articles/{article_id}/revisions')
        assert revisions_response.status_code == 200
        revisions_payload = revisions_response.json()
        assert len(revisions_payload) == 1
        assert revisions_payload[0]['id'] == active_revision_id
        assert revisions_payload[0]['version_number'] == 1
        assert revisions_payload[0]['change_type'] == 'generate'


def test_default_digest_templates_are_exposed() -> None:
    app = create_app(
        Settings(
            database_url='sqlite:///./test_editorial_templates.db',
            redis_url='redis://localhost:6379/0',
            environment='test',
        )
    )

    with TestClient(app) as client:
        response = client.get('/templates/digests')
        assert response.status_code == 200
        payload = response.json()
        period_types = {template['period_type'] for template in payload}
        assert {'weekly', 'monthly'}.issubset(period_types)
        assert any(template['is_default'] for template in payload if template['period_type'] == 'weekly')
        assert any(template['is_default'] for template in payload if template['period_type'] == 'monthly')


def test_unified_generate_endpoint_uses_digest_template_for_weekly_digest() -> None:
    app = create_app(
        Settings(
            database_url='sqlite:///./test_editorial_template_generate.db',
            redis_url='redis://localhost:6379/0',
            environment='test',
        )
    )

    with TestClient(app) as client:
        research_story_response = client.post(
            '/stories',
            json=StoryCreatePayload(
                story_key='editorial-template-research',
                cluster_title='Research benchmark drives the weekly recap',
                summary='A research benchmark should lead the weekly section plan.',
                highlights=['Research signal is dominant'],
                source_links=['https://arxiv.org/abs/1234.5678'],
                tags=['paper', 'benchmark', 'reasoning'],
                risk_flags=[],
                score=9.4,
                item_count=1,
                first_seen_at=datetime(2026, 4, 3, 9, 30, tzinfo=UTC),
                last_seen_at=datetime(2026, 4, 3, 9, 30, tzinfo=UTC),
            ).model_dump(mode='json'),
        )
        open_source_story_response = client.post(
            '/stories',
            json=StoryCreatePayload(
                story_key='editorial-template-open-source',
                cluster_title='Open-source runtime belongs in the same digest',
                summary='An open-source runtime should appear in the weekly mix.',
                highlights=['Open-source signal remains important'],
                source_links=['https://github.com/example/runtime'],
                tags=['github', 'runtime', 'open-source'],
                risk_flags=[],
                score=8.8,
                item_count=1,
                first_seen_at=datetime(2026, 4, 3, 10, 0, tzinfo=UTC),
                last_seen_at=datetime(2026, 4, 3, 10, 0, tzinfo=UTC),
            ).model_dump(mode='json'),
        )
        assert research_story_response.status_code == 201
        assert open_source_story_response.status_code == 201

        research_story_id = research_story_response.json()['id']
        open_source_story_id = open_source_story_response.json()['id']
        assert client.post(f'/stories/{research_story_id}/approve').status_code == 200
        assert client.post(f'/stories/{open_source_story_id}/approve').status_code == 200

        templates_response = client.get('/templates/digests')
        assert templates_response.status_code == 200
        weekly_template_id = next(
            template['id']
            for template in templates_response.json()
            if template['period_type'] == 'weekly' and template['is_default']
        )

        generate_response = client.post(
            '/articles/generate',
            json={
                'period_type': 'weekly',
                'target_date': '2026-04-03',
                'template_id': weekly_template_id,
                'story_ids': [research_story_id, open_source_story_id],
                'generation_note': 'Use the weekly template to shape the section plan.',
            },
        )
        assert generate_response.status_code == 200
        payload = generate_response.json()
        assert payload['template_id'] == weekly_template_id
        assert payload['template_name'] == '默认周报模板'
        assert payload['section_plan'][0]['section_key'] == 'research'
        assert payload['section_plan'][0]['story_count'] >= 1
        assert payload['blocks'][0]['block_type'] == 'title'
        assert any(block['block_type'] == 'story_paragraph' for block in payload['blocks'])


def test_block_edit_and_mixed_rebuild_preserve_locked_content() -> None:
    app = create_app(
        Settings(
            database_url='sqlite:///./test_editorial_rebuild.db',
            redis_url='redis://localhost:6379/0',
            environment='test',
        )
    )

    with TestClient(app) as client:
        create_response = client.post('/stories', json=_story_payload())
        assert create_response.status_code == 201
        story_id = create_response.json()['id']
        assert client.post(f'/stories/{story_id}/approve').status_code == 200

        article_response = client.post('/articles/generate/weekly', json={'target_date': '2026-04-03'})
        assert article_response.status_code == 200
        article_payload = article_response.json()
        article_id = article_payload['id']
        original_revision_id = article_payload['active_revision_id']

        blocks_response = client.get(f'/articles/{article_id}/blocks')
        assert blocks_response.status_code == 200
        blocks = blocks_response.json()
        title_block = next(block for block in blocks if block['block_type'] == 'title')
        story_block = next(block for block in blocks if block['block_type'] == 'story_paragraph')

        title_update_response = client.patch(
            f"/articles/{article_id}/blocks/{title_block['id']}",
            json={'content': 'LOCKED TITLE', 'is_locked': True},
        )
        assert title_update_response.status_code == 200
        assert title_update_response.json()['content'] == 'LOCKED TITLE'
        assert title_update_response.json()['is_locked'] is True

        story_update_response = client.patch(
            f"/articles/{article_id}/blocks/{story_block['id']}",
            json={'content': 'temporary manual rewrite'},
        )
        assert story_update_response.status_code == 200
        assert story_update_response.json()['content'] == 'temporary manual rewrite'
        assert story_update_response.json()['is_locked'] is False

        rebuild_response = client.post(
            f'/articles/{article_id}/rebuild',
            json={'mode': 'mixed'},
        )
        assert rebuild_response.status_code == 200
        rebuilt_payload = rebuild_response.json()
        assert rebuilt_payload['active_revision_id'] != original_revision_id

        rebuilt_blocks_response = client.get(f'/articles/{article_id}/blocks')
        assert rebuilt_blocks_response.status_code == 200
        rebuilt_blocks = rebuilt_blocks_response.json()
        rebuilt_title_block = next(block for block in rebuilt_blocks if block['block_key'] == title_block['block_key'])
        rebuilt_story_block = next(block for block in rebuilt_blocks if block['block_key'] == story_block['block_key'])
        assert rebuilt_title_block['content'] == 'LOCKED TITLE'
        assert rebuilt_title_block['is_locked'] is True
        assert rebuilt_story_block['content'] != 'temporary manual rewrite'

        revisions_response = client.get(f'/articles/{article_id}/revisions')
        assert revisions_response.status_code == 200
        assert len(revisions_response.json()) == 2
        assert revisions_response.json()[-1]['change_type'] == 'rebuild'

        actions_response = client.get(f'/articles/{article_id}/editorial-actions')
        assert actions_response.status_code == 200
        action_types = [action['action_type'] for action in actions_response.json()]
        assert 'edit_block' in action_types
        assert 'rebuild_article' in action_types


def test_restore_revision_creates_new_active_revision() -> None:
    app = create_app(
        Settings(
            database_url='sqlite:///./test_editorial_restore.db',
            redis_url='redis://localhost:6379/0',
            environment='test',
        )
    )

    with TestClient(app) as client:
        create_response = client.post('/stories', json=_story_payload())
        assert create_response.status_code == 201
        story_id = create_response.json()['id']
        assert client.post(f'/stories/{story_id}/approve').status_code == 200

        article_response = client.post('/articles/generate/weekly', json={'target_date': '2026-04-03'})
        assert article_response.status_code == 200
        article_payload = article_response.json()
        article_id = article_payload['id']
        first_revision_id = article_payload['active_revision_id']
        original_title = article_payload['title']

        blocks_response = client.get(f'/articles/{article_id}/blocks')
        title_block = next(block for block in blocks_response.json() if block['block_type'] == 'title')
        update_response = client.patch(
            f"/articles/{article_id}/blocks/{title_block['id']}",
            json={'content': 'LOCKED TITLE', 'is_locked': True},
        )
        assert update_response.status_code == 200

        rebuild_response = client.post(f'/articles/{article_id}/rebuild', json={'mode': 'mixed'})
        assert rebuild_response.status_code == 200
        second_revision_id = rebuild_response.json()['active_revision_id']
        assert second_revision_id != first_revision_id

        restore_response = client.post(f'/articles/{article_id}/revisions/{first_revision_id}/restore')
        assert restore_response.status_code == 200
        restored_payload = restore_response.json()
        assert restored_payload['active_revision_id'] not in {first_revision_id, second_revision_id}
        assert restored_payload['title'] == original_title

        revisions_response = client.get(f'/articles/{article_id}/revisions')
        assert revisions_response.status_code == 200
        revisions_payload = revisions_response.json()
        assert len(revisions_payload) == 3
        assert revisions_payload[-1]['change_type'] == 'restore'


def test_partial_rebuild_can_switch_template_and_only_refresh_selected_sections() -> None:
    app = create_app(
        Settings(
            database_url='sqlite:///./test_editorial_partial_rebuild.db',
            redis_url='redis://localhost:6379/0',
            environment='test',
        )
    )

    with TestClient(app) as client:
        research_story_response = client.post(
            '/stories',
            json=StoryCreatePayload(
                story_key='partial-rebuild-research',
                cluster_title='Research remains the lead section',
                summary='Research summary should be regenerated when the section is targeted.',
                highlights=['Research highlight'],
                source_links=['https://arxiv.org/abs/4321.1111'],
                tags=['paper', 'reasoning'],
                risk_flags=[],
                score=9.5,
                item_count=1,
                first_seen_at=datetime(2026, 4, 3, 9, 30, tzinfo=UTC),
                last_seen_at=datetime(2026, 4, 3, 9, 30, tzinfo=UTC),
            ).model_dump(mode='json'),
        )
        open_source_story_response = client.post(
            '/stories',
            json=StoryCreatePayload(
                story_key='partial-rebuild-open-source',
                cluster_title='Open-source runtime still needs coverage',
                summary='Open-source summary should be preserved when another section is rebuilt.',
                highlights=['Open-source highlight'],
                source_links=['https://github.com/example/runtime'],
                tags=['github', 'open-source', 'runtime'],
                risk_flags=[],
                score=8.9,
                item_count=1,
                first_seen_at=datetime(2026, 4, 3, 10, 0, tzinfo=UTC),
                last_seen_at=datetime(2026, 4, 3, 10, 0, tzinfo=UTC),
            ).model_dump(mode='json'),
        )
        assert research_story_response.status_code == 201
        assert open_source_story_response.status_code == 201

        research_story_id = research_story_response.json()['id']
        open_source_story_id = open_source_story_response.json()['id']
        assert client.post(f'/stories/{research_story_id}/approve').status_code == 200
        assert client.post(f'/stories/{open_source_story_id}/approve').status_code == 200

        with session_scope(app.state.container.session_factory) as session:
            alternate_template = DigestTemplate(
                name='编排型周报模板',
                period_type='weekly',
                description='强调开源优先和行动导向的平台模板。',
                section_quotas={'open_source': 0.45, 'research': 0.35, 'product_updates': 0.2},
                section_order=['open_source', 'research', 'product_updates', 'community'],
                default_platform_templates={'wechat': 'actionable_roundup', 'x': 'tracking_hook', 'telegram': 'discussion_brief'},
                is_default=False,
            )
            session.add(alternate_template)
            session.flush()
            alternate_template_id = alternate_template.id
            session.commit()

        templates_response = client.get('/templates/digests')
        assert templates_response.status_code == 200
        templates = templates_response.json()
        weekly_template_id = next(template['id'] for template in templates if template['period_type'] == 'weekly' and template['is_default'])

        article_response = client.post(
            '/articles/generate',
            json={
                'period_type': 'weekly',
                'target_date': '2026-04-03',
                'template_id': weekly_template_id,
                'story_ids': [research_story_id, open_source_story_id],
            },
        )
        assert article_response.status_code == 200
        article_id = article_response.json()['id']

        blocks_response = client.get(f'/articles/{article_id}/blocks')
        assert blocks_response.status_code == 200
        blocks = blocks_response.json()
        research_block = next(block for block in blocks if block['section_key'] == 'research' and block['block_type'] == 'story_paragraph')
        open_source_block = next(block for block in blocks if block['section_key'] == 'open_source' and block['block_type'] == 'story_paragraph')

        manual_research = client.patch(
            f"/articles/{article_id}/blocks/{research_block['id']}",
            json={'content': 'manual research rewrite'},
        )
        assert manual_research.status_code == 200

        manual_open_source = client.patch(
            f"/articles/{article_id}/blocks/{open_source_block['id']}",
            json={'content': 'manual open-source rewrite'},
        )
        assert manual_open_source.status_code == 200

        rebuild_response = client.post(
            f'/articles/{article_id}/rebuild',
            json={
                'mode': 'mixed',
                'template_id': alternate_template_id,
                'section_keys': ['research'],
            },
        )
        assert rebuild_response.status_code == 200
        rebuilt_payload = rebuild_response.json()
        assert rebuilt_payload['template_id'] == alternate_template_id
        assert rebuilt_payload['template_name'] == '编排型周报模板'

        rebuilt_blocks_response = client.get(f'/articles/{article_id}/blocks')
        assert rebuilt_blocks_response.status_code == 200
        rebuilt_blocks = rebuilt_blocks_response.json()
        rebuilt_research = next(block for block in rebuilt_blocks if block['block_key'] == research_block['block_key'])
        rebuilt_open_source = next(block for block in rebuilt_blocks if block['block_key'] == open_source_block['block_key'])
        assert rebuilt_research['content'] != 'manual research rewrite'
        assert rebuilt_open_source['content'] == 'manual open-source rewrite'

        actions_response = client.get(f'/articles/{article_id}/editorial-actions')
        assert actions_response.status_code == 200
        assert actions_response.json()[-1]['detail']['section_keys'] == ['research']
        assert actions_response.json()[-1]['detail']['template_id'] == alternate_template_id
