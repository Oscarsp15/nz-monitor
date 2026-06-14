"""Caché en memoria y bus de eventos en proceso."""
import asyncio


def test_inmemory_cache_get_set_delete():
    from cache.memory import InMemoryCache

    c = InMemoryCache()
    assert c.get("k") is None
    c.set("k", {"v": 1}, ttl=100)
    assert c.get("k") == {"v": 1}
    c.delete("k")
    assert c.get("k") is None


def test_inmemory_cache_ttl_expira():
    from cache.memory import InMemoryCache

    c = InMemoryCache()
    c.set("k", "v", ttl=-1)  # ya expirado
    assert c.get("k") is None


def test_eventbus_publish_subscribe():
    from cache.memory import InProcessEventBus

    bus = InProcessEventBus()

    async def scenario():
        agen = bus.subscribe("snapshots")
        task = asyncio.ensure_future(agen.__anext__())
        await asyncio.sleep(0)  # deja que el suscriptor registre su cola
        bus.publish("snapshots", {"metric_type": "health", "status": "ok"})
        msg = await asyncio.wait_for(task, timeout=1)
        await agen.aclose()
        return msg

    msg = asyncio.run(scenario())
    assert msg == {"metric_type": "health", "status": "ok"}
