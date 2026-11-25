"""Authorized, bounded ZSXQ topic-feed import; no account discovery or model calls.

Only the returned post sections are archived. Attachments and embedded article
bodies are not fetched. Coverage dates describe observed posts, not a promise
that every post between those dates has been captured.
"""
import json
import re
from datetime import datetime, timezone, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


class _Stop(Exception):
    pass


def _page(group, token, cursor):
    query = {'scope': 'all', 'count': 20}
    if cursor:
        query['end_time'] = cursor
    req = Request('https://api.zsxq.com/v2/groups/%s/topics?%s' % (group, urlencode(query)),
                  headers={'Accept': 'application/json', 'Origin': 'https://wx.zsxq.com',
                           'Referer': 'https://wx.zsxq.com/', 'X-Version': '2.37.0',
                           'X-Timestamp': str(int(datetime.now(timezone.utc).timestamp()))})
    req.add_unredirected_header('Cookie', 'zsxq_access_token=' + token)
    try:
        with build_opener(_NoRedirect()).open(req, timeout=25) as resp:
            raw = resp.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise _Stop('invalid_response')
        data = json.loads(raw)
    except HTTPError as exc:
        code = exc.code
        exc.close()
        raise _Stop('rate_limited' if code == 429 else 'unauthorized' if code in (401, 403)
                    else 'redirect_refused' if 300 <= code < 400 else 'request_failed') from None
    except (OSError, URLError):
        raise _Stop('request_failed') from None
    except (ValueError, RecursionError):
        raise _Stop('invalid_response') from None
    if not isinstance(data, dict):
        raise _Stop('invalid_response')
    if data.get('succeeded') is not True:
        code = str(data.get('code'))
        raise _Stop('rate_limited' if code in ('1059', '429') else 'unauthorized' if code in ('401', '403') else 'request_failed')
    payload = data.get('resp_data')
    topics = payload.get('topics') if isinstance(payload, dict) else None
    if not isinstance(topics, list):
        raise _Stop('invalid_response')
    return topics


def _stamp(value):
    if not isinstance(value, str):
        raise ValueError('invalid timestamp')
    normalized = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', value.replace('Z', '+00:00'))
    dt = datetime.fromisoformat(normalized)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone(timedelta(hours=8)))


def _topic(group, topic):
    key = str(topic['topic_id'])
    if not re.fullmatch('[0-9]+', key):
        raise ValueError('invalid topic id')
    published = topic['create_time']
    dt = _stamp(published)
    kind = topic.get('type', 'talk')
    names = ('question', 'answer') if kind == 'q&a' else (kind,)
    parts, authors = [], []
    for name in names:
        section = topic.get(name) or {}
        author = (section.get('owner') or {}).get('name', '')
        if author and isinstance(author, str):
            authors.append(author)
        text = section.get('text')
        if isinstance(text, str) and text:
            parts.append((name, text))
        article = section.get('article') or {}
        title = article.get('title')
        if isinstance(title, str) and title:
            parts.append(('article:title', title))
    metadata = {'source_type': 'zsxq', 'group_id': group, 'topic_id': key, 'published': published,
                'author': ' / '.join(dict.fromkeys(authors)), 'url': 'https://wx.zsxq.com/topic_detail/' + key}
    raw = json.dumps({'metadata': metadata, 'sections': parts}, ensure_ascii=False,
                     sort_keys=True, separators=(',', ':')).encode('utf-8')
    metadata['collected_at'] = datetime.now(timezone.utc).isoformat()
    return key, published, dt, raw, parts, metadata


def planet_status(store, group_id):
    group = str(group_id)
    if not re.fullmatch('[0-9]{1,32}', group):
        raise ValueError('无效星球 ID')
    source = 'zsxq:' + group
    saved = store.get_cursor(source)
    state = json.loads(saved) if saved else {}
    return {'source': source, 'status': 'checkpointed' if saved else 'not_synced',
            'coverage': {'start': state.get('start'), 'end': state.get('end'),
                         'history_complete': bool(state.get('done')), 'incremental_pending': bool(state.get('inc'))}}


def sync(store, group_id, token, max_pages=1):
    """One bounded run. With budget=1, alternate head checks and older pages.

    Incremental continuation retains its own cursor until the previous head
    is encountered; the historical cursor never advances on a head check.
    Checkpoint only after all puts; replay of a partial page is idempotent.
    """
    group = str(group_id)
    if not re.fullmatch('[0-9]{1,32}', group) or not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9._~+/=%-]{1,4096}', token):
        raise ValueError('请提供有效星球 ID 和访问凭据')
    if type(max_pages) is not int or not 1 <= max_pages <= 100:
        raise ValueError('max_pages 必须在 1..100 之间')
    source = 'zsxq:' + group
    store.register(source)
    saved = store.get_cursor(source)
    state = json.loads(saved) if saved else dict(head=None, back=None, done=False, inc=None,
                                               next='head', start=None, end=None)
    counts = dict(new=0, changed=0, unchanged=0, ignored=0)
    status, pages = 'ok', 0
    for _ in range(max_pages):
        stage = state['next']
        cursor = state['back'] if stage == 'back' else state['inc']['cursor'] if stage == 'inc' else None
        try:
            topics = _page(group, token, cursor)
            rows = [_topic(group, t) for t in topics]
            if any(a[2] < b[2] for a, b in zip(rows, rows[1:])):
                raise _Stop('unordered_page')
            for key, published, dt, raw, parts, metadata in rows:
                result = store.put(source, key, raw, parts, require_registered=True, metadata=metadata)
                counts[result['status']] += 1
            last = rows[-1][1] if rows else None
            keys = [r[0] for r in rows]
            if stage == 'head':
                old = state['head']
                if rows:
                    state['head'] = keys[0]
                    if not old:
                        state['done'] = False
                        state['back'] = last
                    elif old not in keys:
                        state['inc'] = {'cursor': last, 'stop': old}
                elif not old:
                    state['done'] = True
            elif stage == 'inc' and (not rows or state['inc']['stop'] in keys):
                state['inc'] = None
            elif rows and _stamp(last) >= _stamp(cursor):
                raise _Stop('cursor_stalled')
            elif stage == 'inc':
                state['inc']['cursor'] = last
            elif rows:
                state['back'] = last
            else:
                state['done'] = True
            if rows:
                for name, value, earlier in [('start', rows[-1], True), ('end', rows[0], False)]:
                    current = state[name]
                    if current is None or (value[2] < _stamp(current) if earlier else value[2] > _stamp(current)):
                        state[name] = value[1]
            state['next'] = ('inc' if state['inc'] else 'back' if stage != 'back' and not state['done'] and state['back'] else 'head')
            store.save_cursor(source, json.dumps(state, separators=(',', ':')))
            pages += 1
            # A completed head/continuation run need not refetch the head this call.
            if state['next'] == 'head' and state['done']:
                break
        except _Stop as exc:
            status = str(exc)
            break
        except (KeyError, TypeError, ValueError, AttributeError):
            status = 'invalid_response_or_source'
            break
    return {'source': source, 'status': status, 'pages': pages, 'counts': counts,
            'coverage': {'start': state['start'], 'end': state['end'],
                         'history_complete': state['done'], 'incremental_pending': bool(state['inc'])}}
