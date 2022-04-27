from django.db.models import Q, F, Count
from django.http import JsonResponse
from foo.models import Foo
from asgiref.sync import sync_to_async
import asyncio

def bench (request):
    q = (Foo.objects
        .filter (Q (from_wallet_id = 8) | Q (to_wallet_id = 8)))
    record_count = q.aggregate (Count ('id'))['id__count']
    rows = q.order_by ("-created_at")[:10]
    data = list(rows.values())
    return JsonResponse ({'txs': data, 'record_count': record_count})

async def bench_async (request):
    q = (Foo.objects
        .filter (Q (from_wallet_id = 8) | Q (to_wallet_id = 8)))
    rows = q.order_by ("-created_at")[:10]
    data, record_count = await asyncio.gather (
        sync_to_async(list)(rows.values ()),
        sync_to_async(lambda: q.aggregate (Count ('id'))['id__count'])(),
    )
    return JsonResponse ({'txs': data, 'record_count': record_count})