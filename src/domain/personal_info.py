from collections.abc import Mapping
from dataclasses import dataclass, field

ALLOWED_PERSONAL_KEYS = frozenset(
    {"full_name", "headline", "email", "phone", "location", "links"}
)

FORBIDDEN_PERSONAL_KEYS = frozenset(
    {
        "dni",
        "documento_identidad",
        "document",
        "document_number",
        "id_number",
        "passport",
        "passport_number",
        "ssn",
        "ruc",
        "tax_id",
        "address",
        "direccion",
        "exact_address",
        "street",
        "street_address",
        "marital_status",
        "estado_civil",
        "age",
        "edad",
        "date_of_birth",
        "birth_date",
        "fecha_nacimiento",
        "dob",
        "photo",
        "photograph",
        "fotografia",
        "picture",
        "gender",
        "genero",
        "sex",
        "religion",
        "religión",
        "nationality",
        "nacionalidad",
        "salary",
        "salary_expectation",
        "salary_expectations",
        "pretension_salarial",
        "expected_salary",
        "financial_info",
        "bank_account",
    }
)


def _as_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "; ".join(
            str(item).strip() for item in value if str(item).strip()
        )
    if value is None:
        return ""
    return str(value).strip()


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _normalized_key(key: object) -> str:
    return str(key).strip().lower()


def _lookup(data: Mapping[str, object], *keys: str) -> object:
    if not data:
        return None
    normalized = {_normalized_key(key): value for key, value in data.items()}
    for key in keys:
        if key in normalized:
            return normalized[key]
    return None


def _first_text(data: Mapping[str, object], *keys: str) -> str:
    for key in keys:
        value = _as_text(_lookup(data, key))
        if value:
            return value
    return ""


def forbidden_keys_present(data: Mapping[str, object]) -> set[str]:
    return set(
        FORBIDDEN_PERSONAL_KEYS.intersection(
            _normalized_key(key) for key in data
        )
    )


@dataclass(frozen=True, slots=True)
class Location:
    city: str = ""
    country: str = ""

    @classmethod
    def from_mapping(cls, data: object) -> "Location":
        mapping = _as_mapping(data)
        return cls(
            city=_first_text(mapping, "city"),
            country=_first_text(mapping, "country"),
        )

    def to_dict(self) -> dict[str, str]:
        return {"city": self.city, "country": self.country}

    def is_empty(self) -> bool:
        return not (self.city or self.country)


@dataclass(frozen=True, slots=True)
class ProfessionalLinks:
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""

    @classmethod
    def from_mapping(cls, data: object) -> "ProfessionalLinks":
        mapping = _as_mapping(data)
        return cls(
            linkedin=_first_text(mapping, "linkedin"),
            github=_first_text(mapping, "github"),
            portfolio=_first_text(mapping, "portfolio", "website", "web"),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "linkedin": self.linkedin,
            "github": self.github,
            "portfolio": self.portfolio,
        }

    def is_empty(self) -> bool:
        return not (self.linkedin or self.github or self.portfolio)


@dataclass(frozen=True, slots=True)
class PersonalInfo:
    full_name: str = ""
    headline: str = ""
    email: str = ""
    phone: str = ""
    location: Location = field(default_factory=Location)
    links: ProfessionalLinks = field(default_factory=ProfessionalLinks)

    @classmethod
    def from_mapping(cls, data: object) -> "PersonalInfo":
        mapping = _as_mapping(data)
        return cls(
            full_name=_first_text(mapping, "full_name", "name"),
            headline=_first_text(
                mapping,
                "headline",
                "professional_title",
                "role",
                "title",
            ),
            email=_first_text(mapping, "email"),
            phone=_first_text(mapping, "phone", "telephone"),
            location=Location.from_mapping(_lookup(mapping, "location")),
            links=ProfessionalLinks.from_mapping(
                _lookup(mapping, "links", "professional_links")
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "full_name": self.full_name,
            "headline": self.headline,
            "email": self.email,
            "phone": self.phone,
            "location": self.location.to_dict(),
            "links": self.links.to_dict(),
        }

    def is_empty(self) -> bool:
        return not (
            self.full_name
            or self.headline
            or self.email
            or self.phone
            or not self.location.is_empty()
            or not self.links.is_empty()
        )


def render_personal_header(personal_info: PersonalInfo | None) -> str:
    if personal_info is None:
        return ""

    lines: list[str] = []
    if personal_info.full_name:
        lines.append(personal_info.full_name)
    if personal_info.headline:
        lines.append(personal_info.headline)

    location = ", ".join(
        part
        for part in (
            personal_info.location.city,
            personal_info.location.country,
        )
        if part
    )
    contact = " | ".join(
        part
        for part in (personal_info.email, personal_info.phone, location)
        if part
    )
    if contact:
        lines.append(contact)

    links = " | ".join(
        part
        for part in (
            personal_info.links.linkedin,
            personal_info.links.github,
            personal_info.links.portfolio,
        )
        if part
    )
    if links:
        lines.append(links)

    return "\n".join(lines)
