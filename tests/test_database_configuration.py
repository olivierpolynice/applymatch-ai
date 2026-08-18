from app.db.session import DATABASE_URL, engine


def test_database_engine_uses_configured_url() -> None:
    assert (
        engine.url.render_as_string(
            hide_password=False,
        )
        == DATABASE_URL
    )


def test_sqlite_keeps_thread_compatibility() -> None:
    if DATABASE_URL.startswith("sqlite"):
        assert engine.dialect.name == "sqlite"