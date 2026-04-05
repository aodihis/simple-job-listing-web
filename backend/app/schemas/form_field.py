from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Field types ──────────────────────────────────────────────────────────────

class FieldType(str, Enum):
    """Exhaustive whitelist of allowed input types. Nothing outside this list is accepted."""

    text = "text"
    textarea = "textarea"
    email = "email"
    url = "url"
    number = "number"
    radio = "radio"        # single-choice from a fixed list
    select = "select"      # single-choice dropdown from a fixed list
    checkbox = "checkbox"  # multi-choice from a fixed list


# Types that require an options list
_OPTION_TYPES: frozenset[FieldType] = frozenset({
    FieldType.radio,
    FieldType.select,
    FieldType.checkbox,
})

MAX_FIELDS = 20
MAX_OPTIONS = 20
MAX_OPTION_LEN = 100


# ── Write schemas ─────────────────────────────────────────────────────────────

class FormFieldCreate(BaseModel):
    label: str = Field(
        min_length=1,
        max_length=200,
        description="The question label shown to the applicant.",
    )
    field_type: FieldType = Field(description="Input type. One of: text, textarea, email, url, number, radio, select, checkbox.")
    is_required: bool = Field(default=False, description="Whether the applicant must answer this field.")
    options: list[str] = Field(
        default_factory=list,
        description="Answer choices. Required for radio / select / checkbox. Ignored for other types.",
    )

    @field_validator("options", mode="before")
    @classmethod
    def strip_options(cls, v: list[str]) -> list[str]:
        return [str(o).strip() for o in v if str(o).strip()]

    @model_validator(mode="after")
    def validate_options_rules(self) -> FormFieldCreate:
        if self.field_type in _OPTION_TYPES:
            if not self.options:
                raise ValueError(
                    f"options must not be empty for field_type '{self.field_type}'"
                )
            if len(self.options) > MAX_OPTIONS:
                raise ValueError(f"Maximum {MAX_OPTIONS} options allowed per field.")
            for opt in self.options:
                if len(opt) > MAX_OPTION_LEN:
                    raise ValueError(
                        f"Each option must be {MAX_OPTION_LEN} characters or fewer. "
                        f"Offending value: {opt!r}"
                    )
        else:
            # Silently strip options that don't apply to this field type.
            self.options = []
        return self


class FormFieldsUpdate(BaseModel):
    """Replaces the entire field list for a job in one atomic operation."""

    fields: list[FormFieldCreate] = Field(
        default_factory=list,
        max_length=MAX_FIELDS,
        description=f"Ordered list of form fields. Maximum {MAX_FIELDS} fields per job.",
    )


# ── Read schemas ──────────────────────────────────────────────────────────────

class FormFieldRead(BaseModel):
    id: int = Field(description="Internal field ID.")
    label: str
    field_type: str
    is_required: bool
    options: list[str]
    order: int = Field(description="Zero-based display order.")

    model_config = {"from_attributes": True}
