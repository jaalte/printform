from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

@dataclass
class LabelField:
    name: str
    x: int
    y: int
    data: Dict

@dataclass
class LabelTemplate:
    label: str
    base_image: Optional[str]
    fields: List[LabelField]
    offsets: List[int]
    filename: Optional[str] = None
    template_path: Optional[str] = None

@dataclass
class LabelSession:
    session_id: str
    used_formdata: Dict
    label_template: LabelTemplate
    date_created: datetime
    preview_filename: str

    @classmethod
    def create(cls, session_id: str, formdata: Dict, template: LabelTemplate) -> 'LabelSession':
        return cls(
            session_id=session_id,
            used_formdata=formdata,
            label_template=template,
            date_created=datetime.now(),
            preview_filename=f"preview_{session_id}.png"
        )