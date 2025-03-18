import json
import os
from typing import Dict, Optional
from ..models.label import LabelTemplate, LabelField
from ..config.settings import TEMPLATE_DIR, DEFAULT_TEMPLATE

class TemplateService:
    @staticmethod
    def load_templates() -> Dict[str, LabelTemplate]:
        """Loads all template files from the template directory."""
        templates = {}

        # Get all template files
        template_files = [
            f for f in os.listdir(TEMPLATE_DIR)
            if f.startswith("label_template") and f.endswith(".json")
        ]

        for template_file in template_files:
            template_path = os.path.join(TEMPLATE_DIR, template_file)
            with open(template_path, 'r', encoding='utf-8') as f:
                base_template = json.load(f)

            # Convert fields to LabelField objects
            fields = []
            for field in base_template['fields']:
                # Ensure the field has a label property
                field_data = field['data']
                if 'label' not in field_data:
                    field_data['label'] = field['name'].replace('_', ' ').title()
                
                fields.append(LabelField(
                    name=field['name'],
                    x=field['x'],
                    y=field['y'],
                    data=field_data
                ))

            # Create LabelTemplate object
            template = LabelTemplate(
                label=base_template['label'],
                base_image=base_template.get('base_image'),
                fields=fields,
                offsets=base_template['offsets'],
                filename=template_file,
                template_path=template_path
            )

            templates[template.label] = template

        return templates

    @staticmethod
    def get_template(template_name: Optional[str] = None) -> LabelTemplate:
        """Gets a specific template by name, or the default template."""
        if template_name:
            templates = TemplateService.load_templates()
            if template_name not in templates:
                raise ValueError(f"Unknown template: {template_name}")
            return templates[template_name]

        # Load default template
        with open(DEFAULT_TEMPLATE, 'r', encoding='utf-8') as f:
            base_template = json.load(f)

        fields = []
        for field in base_template['fields']:
            # Ensure the field has a label property
            field_data = field['data']
            if 'label' not in field_data:
                field_data['label'] = field['name'].replace('_', ' ').title()
            
            fields.append(LabelField(
                name=field['name'],
                x=field['x'],
                y=field['y'],
                data=field_data
            ))

        return LabelTemplate(
            label=base_template['label'],
            base_image=base_template.get('base_image'),
            fields=fields,
            offsets=base_template['offsets'],
            filename=os.path.basename(DEFAULT_TEMPLATE),
            template_path=DEFAULT_TEMPLATE
        )