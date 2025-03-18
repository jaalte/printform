from flask import Blueprint, jsonify
from ..services.template_service import TemplateService

template_routes = Blueprint('template', __name__)

@template_routes.route('/get_templates', methods=['GET'])
def get_templates():
    """Returns all available templates."""
    templates = TemplateService.load_templates()
    return jsonify(templates)