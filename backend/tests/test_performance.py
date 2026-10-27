import pytest

# run these manually, not in CI
pytest.skip("run manually for perf testing", allow_module_level=True)


@pytest.mark.asyncio
async def test_health_latency():
    # should be < 50ms
    pass


@pytest.mark.asyncio
async def test_concurrent_uploads():
    # 10 at once
    pass


@pytest.mark.asyncio
async def test_pool_under_load():
    pass
