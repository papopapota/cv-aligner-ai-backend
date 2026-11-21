import json

from src.infrastructure.adapters.out.job_description_html_parser import (
    extract_description,
    extract_job_posting,
    normalize_text,
)

_MAX_CHARS = 20000


def _jsonld_html(description: str) -> str:
    payload = json.dumps({"@type": "JobPosting", "description": description})
    return f'<script type="application/ld+json">{payload}</script>'

_LINKEDIN_TITLE_CLASSES = (
    "top-card-layout__title font-sans text-lg papabear:text-xl font-bold "
    "leading-open text-color-text mb-0 topcard__title"
)


def test_extracts_the_description_from_a_jobposting_jsonld() -> None:
    html = """
    <html><head>
      <script type="application/ld+json">
        {"@context":"https://schema.org","@type":"JobPosting",
         "title":"Backend Engineer",
         "description":"<p>Buscamos <strong>Python</strong> y FastAPI.</p><p>Remoto.</p>"}
      </script>
    </head><body><main>Otro texto visible</main></body></html>
    """

    description = extract_description(html, _MAX_CHARS)

    assert description == "Buscamos Python y FastAPI.\nRemoto."


def test_finds_jobposting_inside_a_jsonld_graph() -> None:
    html = """
    <script type="application/ld+json">
      {"@graph":[{"@type":"WebPage","name":"Oferta"},
                 {"@type":"JobPosting","description":"Trabaja con LangGraph."}]}
    </script>
    """

    assert extract_description(html, _MAX_CHARS) == "Trabaja con LangGraph."


def test_falls_back_to_the_visible_main_content() -> None:
    html = """
    <html><body>
      <nav>Menú que no interesa</nav>
      <main>
        <h1>Desarrollador Frontend</h1>
        <script>tracking()</script>
        <p>Requisitos: React y TypeScript.</p>
        <p>Experiencia con accesibilidad.</p>
      </main>
      <footer>Copyright</footer>
    </body></html>
    """

    description = extract_description(html, _MAX_CHARS)

    assert "Menú que no interesa" not in description
    assert "tracking()" not in description
    assert "Copyright" not in description
    assert "Desarrollador Frontend" in description
    assert "Requisitos: React y TypeScript." in description
    assert "Experiencia con accesibilidad." in description


def test_normalizes_blank_lines() -> None:
    assert normalize_text("  Primera .\n\n\n  Segunda. \n", _MAX_CHARS) == (
        "Primera .\nSegunda."
    )


def test_truncates_the_description_without_cutting_a_line() -> None:
    assert normalize_text("abc\n\ndef", 4) == "abc"


def test_extracts_linkedin_title_and_company_from_the_top_card() -> None:
    html = f"""
    <html><body>
      <header>
        <h1 class="{_LINKEDIN_TITLE_CLASSES}">
          Senior Frontend Engineer
        </h1>
        <a class="topcard__org-name-link" href="/company/nexa">Nexa Labs</a>
      </header>
      <main><p>Buscamos React y TypeScript.</p></main>
    </body></html>
    """

    content = extract_job_posting(html, _MAX_CHARS)

    assert content.title == "Senior Frontend Engineer"
    assert content.company == "Nexa Labs"
    assert content.description == "Buscamos React y TypeScript."


def test_title_falls_back_to_jsonld_and_then_to_a_generic_h1() -> None:
    jsonld_html = """
    <script type="application/ld+json">
      {"@type":"JobPosting","title":"Backend Engineer",
       "description":"Trabaja con FastAPI."}
    </script>
    <main><h1>Título visible</h1></main>
    """
    h1_html = """
    <script type="application/ld+json">
      {"@type":"JobPosting","description":"Trabaja con FastAPI."}
    </script>
    <main><h1>Desarrollador Python</h1></main>
    """

    assert extract_job_posting(jsonld_html, _MAX_CHARS).title == "Backend Engineer"
    assert extract_job_posting(h1_html, _MAX_CHARS).title == "Desarrollador Python"


def test_company_falls_back_to_jsonld_hiring_organization() -> None:
    html = """
    <script type="application/ld+json">
      {"@type":"JobPosting","description":"Trabaja con FastAPI.",
       "hiringOrganization":{"@type":"Organization","name":"Acme Corp"}}
    </script>
    """

    content = extract_job_posting(html, _MAX_CHARS)

    assert content.company == "Acme Corp"


def test_company_skips_separator_flavors() -> None:
    html = """
    <div>
      <span class="topcard__flavor">·</span>
      <span class="topcard__flavor">Beta Studio</span>
      <span class="topcard__flavor">Remoto</span>
    </div>
    <main><p>Una descripción.</p></main>
    """

    assert extract_job_posting(html, _MAX_CHARS).company == "Beta Studio"


def test_returns_none_when_metadata_is_missing() -> None:
    html = "<main><p>Solo hay descripción.</p></main>"

    content = extract_job_posting(html, _MAX_CHARS)

    assert content.title is None
    assert content.company is None
    assert content.description == "Solo hay descripción."


def test_strips_escaped_html_from_the_jsonld_description() -> None:
    description = (
        "&lt;p&gt;Buscamos &lt;strong&gt;Python&lt;/strong&gt;.&lt;/p&gt;"
        "&lt;ul&gt;&lt;li&gt;Remoto&lt;/li&gt;&lt;/ul&gt;"
    )

    result = extract_description(_jsonld_html(description), _MAX_CHARS)

    assert result == "Buscamos Python.\nRemoto"


def test_strips_double_escaped_html_and_entities() -> None:
    description = (
        "&amp;lt;p&amp;gt;Buscamos Python &amp;amp; FastAPI.&amp;lt;/p&amp;gt;"
    )

    result = extract_description(_jsonld_html(description), _MAX_CHARS)

    assert result == "Buscamos Python & FastAPI."


def test_turns_escaped_br_into_a_line_break() -> None:
    result = extract_description(
        _jsonld_html("Primera&lt;br&gt;Segunda"), _MAX_CHARS
    )

    assert result == "Primera\nSegunda"


def test_does_not_add_a_space_before_punctuation() -> None:
    result = extract_description(
        _jsonld_html("<p>Buscamos <strong>Python</strong>.</p>"), _MAX_CHARS
    )

    assert result == "Buscamos Python."


def test_normalizes_non_breaking_spaces() -> None:
    result = extract_description(
        _jsonld_html("Primera&nbsp;Segunda"), _MAX_CHARS
    )

    assert result == "Primera Segunda"


def test_strips_escaped_tags_from_the_visible_html() -> None:
    html = "<main>&lt;p&gt;Texto visible &lt;strong&gt;destacado&lt;/strong&gt;.&lt;/p&gt;</main>"

    result = extract_description(html, _MAX_CHARS)

    assert result == "Texto visible destacado."
